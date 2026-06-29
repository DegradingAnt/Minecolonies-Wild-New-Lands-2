import org.objectweb.asm.*;
import org.objectweb.asm.tree.*;
import java.util.zip.*;
import java.io.*;

// Transform-applies test for Fix 63 v2 (sable VoxelNeighborhoodState$1/$2 solidity cache ->
// per-thread ThreadLocal, replacing the v1 global ACC_SYNCHRONIZED that serialized OCL gen 18->4 c/s).
// Loads the REAL inner classes from the sable jar, applies the SAME three retargets the JS coremod does
// (field + <init> + typed apply), asserts the result, and re-serializes with COMPUTE_FRAMES (Object-fallback
// SafeCW) to prove the spliced control flow + stack are verifier-valid.
public class TestSableThreadLocal {
    static final String MAP  = "it/unimi/dsi/fastutil/ints/Int2BooleanOpenHashMap";
    static final String MAPD = "L" + MAP + ";";
    static final String TL   = "java/lang/ThreadLocal";
    static final String TLD  = "L" + TL + ";";

    static class SafeCW extends ClassWriter {
        SafeCW(int f) { super(f); }
        protected String getCommonSuperClass(String a, String b) { return "java/lang/Object"; }
    }

    // Mirror of sableVoxelCacheThreadLocal in uvfixes.js
    static boolean[] transform(ClassNode cn) {
        boolean fieldFixed = false, initFixed = false, applyFixed = false;

        for (Object of : cn.fields) {
            FieldNode fld = (FieldNode) of;
            if (fld.name.equals("cache") && fld.desc.equals(MAPD)) { fld.desc = TLD; fieldFixed = true; }
        }

        for (Object om : cn.methods) {
            MethodNode m = (MethodNode) om;
            if (m.name.equals("<init>")) {
                boolean nNew = false, nInit = false, nPut = false;
                for (AbstractInsnNode insn : m.instructions.toArray()) {
                    if (insn instanceof TypeInsnNode && insn.getOpcode() == Opcodes.NEW && ((TypeInsnNode) insn).desc.equals(MAP)) {
                        ((TypeInsnNode) insn).desc = TL; nNew = true;
                    } else if (insn instanceof MethodInsnNode && insn.getOpcode() == Opcodes.INVOKESPECIAL
                            && ((MethodInsnNode) insn).owner.equals(MAP) && ((MethodInsnNode) insn).name.equals("<init>")) {
                        ((MethodInsnNode) insn).owner = TL; nInit = true;
                    } else if (insn instanceof FieldInsnNode && insn.getOpcode() == Opcodes.PUTFIELD
                            && ((FieldInsnNode) insn).name.equals("cache") && ((FieldInsnNode) insn).desc.equals(MAPD)) {
                        ((FieldInsnNode) insn).desc = TLD; nPut = true;
                    }
                }
                if (nNew && nInit && nPut) initFixed = true;
            } else if (m.name.equals("apply") && m.desc.endsWith(")Ljava/lang/Boolean;")) {
                for (AbstractInsnNode gi : m.instructions.toArray()) {
                    if (gi instanceof FieldInsnNode && gi.getOpcode() == Opcodes.GETFIELD
                            && ((FieldInsnNode) gi).name.equals("cache") && ((FieldInsnNode) gi).desc.equals(MAPD)) {
                        ((FieldInsnNode) gi).desc = TLD;
                        LabelNode have = new LabelNode();
                        InsnList list = new InsnList();
                        list.add(new MethodInsnNode(Opcodes.INVOKEVIRTUAL, TL, "get", "()Ljava/lang/Object;", false));
                        list.add(new InsnNode(Opcodes.DUP));
                        list.add(new JumpInsnNode(Opcodes.IFNONNULL, have));
                        list.add(new InsnNode(Opcodes.POP));
                        list.add(new VarInsnNode(Opcodes.ALOAD, 0));
                        list.add(new FieldInsnNode(Opcodes.GETFIELD, cn.name, "cache", TLD));
                        list.add(new TypeInsnNode(Opcodes.NEW, MAP));
                        list.add(new InsnNode(Opcodes.DUP));
                        list.add(new MethodInsnNode(Opcodes.INVOKESPECIAL, MAP, "<init>", "()V", false));
                        list.add(new InsnNode(Opcodes.DUP_X1));
                        list.add(new MethodInsnNode(Opcodes.INVOKEVIRTUAL, TL, "set", "(Ljava/lang/Object;)V", false));
                        list.add(have);
                        list.add(new TypeInsnNode(Opcodes.CHECKCAST, MAP));
                        m.instructions.insert(gi, list);
                        applyFixed = true;
                        break;
                    }
                }
            }
        }
        return new boolean[]{ fieldFixed, initFixed, applyFixed };
    }

    static boolean check(String jar, String cls) throws Exception {
        byte[] in;
        try (ZipFile zf = new ZipFile(jar)) {
            ZipEntry e = zf.getEntry(cls);
            if (e == null) { System.out.println("FAIL: " + cls + " not in " + jar); return false; }
            in = zf.getInputStream(e).readAllBytes();
        }
        ClassNode cn = new ClassNode();
        new ClassReader(in).accept(cn, 0);
        boolean[] r = transform(cn);
        boolean fieldFixed = r[0], initFixed = r[1], applyFixed = r[2];

        // assert: field cache now ThreadLocal
        boolean fieldOk = false;
        for (Object of : cn.fields) {
            FieldNode fld = (FieldNode) of;
            if (fld.name.equals("cache")) fieldOk = fld.desc.equals(TLD);
        }
        // assert: <init> allocates a ThreadLocal, putfield desc is TL, no leftover map alloc
        boolean initTL = false, initMapLeft = false, putTL = false;
        // assert: apply has the lazy-fetch shape + still computeIfAbsent on the map
        boolean getfieldTL = false, tlGet = false, tlSet = false, ckcast = false, computeStill = false;
        for (Object om : cn.methods) {
            MethodNode m = (MethodNode) om;
            if (m.name.equals("<init>")) {
                for (AbstractInsnNode insn : m.instructions.toArray()) {
                    if (insn instanceof TypeInsnNode && insn.getOpcode() == Opcodes.NEW) {
                        if (((TypeInsnNode) insn).desc.equals(TL)) initTL = true;
                        if (((TypeInsnNode) insn).desc.equals(MAP)) initMapLeft = true;
                    }
                    if (insn instanceof FieldInsnNode && insn.getOpcode() == Opcodes.PUTFIELD
                            && ((FieldInsnNode) insn).name.equals("cache"))
                        putTL = ((FieldInsnNode) insn).desc.equals(TLD);
                }
            } else if (m.name.equals("apply") && m.desc.endsWith(")Ljava/lang/Boolean;")) {
                for (AbstractInsnNode insn : m.instructions.toArray()) {
                    if (insn instanceof FieldInsnNode && insn.getOpcode() == Opcodes.GETFIELD
                            && ((FieldInsnNode) insn).name.equals("cache"))
                        getfieldTL = ((FieldInsnNode) insn).desc.equals(TLD);
                    if (insn instanceof MethodInsnNode) {
                        MethodInsnNode mi = (MethodInsnNode) insn;
                        if (mi.owner.equals(TL) && mi.name.equals("get")) tlGet = true;
                        if (mi.owner.equals(TL) && mi.name.equals("set")) tlSet = true;
                        if (mi.owner.equals(MAP) && mi.name.equals("computeIfAbsent")) computeStill = true;
                    }
                    if (insn instanceof TypeInsnNode && insn.getOpcode() == Opcodes.CHECKCAST
                            && ((TypeInsnNode) insn).desc.equals(MAP)) ckcast = true;
                }
            }
        }

        boolean serOk; int len = 0;
        try {
            SafeCW cw = new SafeCW(ClassWriter.COMPUTE_FRAMES | ClassWriter.COMPUTE_MAXS);
            cn.accept(cw);
            len = cw.toByteArray().length;
            serOk = true;
        } catch (Throwable t) { serOk = false; System.out.println("  re-serialize threw: " + t); }

        System.out.println("  " + cls);
        System.out.println("    transform flags: field=" + fieldFixed + " init=" + initFixed + " apply=" + applyFixed);
        System.out.println("    field cache=ThreadLocal: " + fieldOk);
        System.out.println("    <init> new ThreadLocal: " + initTL + " | no leftover map alloc: " + (!initMapLeft) + " | putfield desc TL: " + putTL);
        System.out.println("    apply getfield TL: " + getfieldTL + " | ThreadLocal.get: " + tlGet + " | ThreadLocal.set: " + tlSet
                + " | checkcast map: " + ckcast + " | computeIfAbsent retained: " + computeStill);
        System.out.println("    COMPUTE_FRAMES re-serialize OK: " + serOk + " (" + len + " bytes)");

        boolean pass = fieldFixed && initFixed && applyFixed && fieldOk && initTL && !initMapLeft && putTL
                && getfieldTL && tlGet && tlSet && ckcast && computeStill && serOk;
        System.out.println("    -> " + (pass ? "PASS" : "FAIL"));
        return pass;
    }

    public static void main(String[] a) throws Exception {
        String jar = a.length > 0 ? a[0] : "mods/sable-neoforge-1.21.1-2.0.3.jar";
        System.out.println("jar=" + jar);
        boolean p1 = check(jar, "dev/ryanhcode/sable/physics/chunk/VoxelNeighborhoodState$1.class");
        boolean p2 = check(jar, "dev/ryanhcode/sable/physics/chunk/VoxelNeighborhoodState$2.class");
        boolean pass = p1 && p2;
        System.out.println(pass ? "RESULT: PASS" : "RESULT: FAIL");
        if (!pass) System.exit(1);
    }
}
