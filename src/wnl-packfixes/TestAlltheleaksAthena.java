import org.objectweb.asm.*;
import org.objectweb.asm.tree.*;
import java.util.zip.*;
import java.io.*;

// Transform-applies test for Fix 64 (alltheleaks AthenaResourceLoaderMixin setGetter static-ify).
// Loads the REAL mixin class from the jar, applies the same transform the JS coremod does, asserts the
// result, and re-serializes with COMPUTE_FRAMES (Object-fallback SafeCW) to prove the bytecode is valid.
public class TestAlltheleaksAthena {
    static final String DESC = "(Ljava/util/function/Function;)V";
    static final String CLS  = "dev/uncandango/alltheleaks/mixin/core/main/AthenaResourceLoaderMixin.class";

    static class SafeCW extends ClassWriter {
        SafeCW(int f) { super(f); }
        protected String getCommonSuperClass(String a, String b) { return "java/lang/Object"; }
    }

    public static void main(String[] a) throws Exception {
        String jar = a.length > 0 ? a[0]
            : "mods/alltheleaks-1.1.9+1.21.1-neoforge.jar";
        byte[] in = null;
        try (ZipFile zf = new ZipFile(jar)) {
            ZipEntry e = zf.getEntry(CLS);
            if (e == null) { System.out.println("FAIL: " + CLS + " not in " + jar); System.exit(2); }
            in = zf.getInputStream(e).readAllBytes();
        }
        ClassNode cn = new ClassNode();
        new ClassReader(in).accept(cn, 0);

        boolean shadowed = false, callfixed = false;
        for (Object om : cn.methods) {
            MethodNode m = (MethodNode) om;
            if (m.name.equals("setGetter") && m.desc.equals(DESC)) {
                m.access = (m.access & ~Opcodes.ACC_ABSTRACT) | Opcodes.ACC_STATIC;
                InsnList body = new InsnList();
                body.add(new InsnNode(Opcodes.RETURN));
                m.instructions = body;
                shadowed = true;
            } else if (m.name.equals("clearGetter")) {
                for (AbstractInsnNode insn : m.instructions.toArray()) {
                    if (insn instanceof MethodInsnNode && insn.getOpcode() == Opcodes.INVOKEVIRTUAL) {
                        MethodInsnNode mi = (MethodInsnNode) insn;
                        if (mi.name.equals("setGetter") && mi.desc.equals(DESC)) {
                            AbstractInsnNode rcv = insn.getPrevious().getPrevious();
                            if (rcv instanceof VarInsnNode && rcv.getOpcode() == Opcodes.ALOAD && ((VarInsnNode) rcv).var == 0) {
                                m.instructions.remove(rcv);
                                m.instructions.set(insn, new MethodInsnNode(Opcodes.INVOKESTATIC, mi.owner, mi.name, mi.desc, false));
                                callfixed = true;
                            }
                            break;
                        }
                    }
                }
            }
        }

        boolean sgStatic = false, sgBody = false, callStatic = false, noRcvLeft = true;
        for (Object om : cn.methods) {
            MethodNode m = (MethodNode) om;
            if (m.name.equals("setGetter") && m.desc.equals(DESC)) {
                sgStatic = (m.access & Opcodes.ACC_STATIC) != 0 && (m.access & Opcodes.ACC_ABSTRACT) == 0;
                sgBody = m.instructions != null && m.instructions.size() >= 1;
            }
            if (m.name.equals("clearGetter")) {
                int aload0 = 0;
                for (AbstractInsnNode insn : m.instructions.toArray()) {
                    if (insn instanceof VarInsnNode && insn.getOpcode() == Opcodes.ALOAD && ((VarInsnNode) insn).var == 0) aload0++;
                    if (insn instanceof MethodInsnNode && ((MethodInsnNode) insn).name.equals("setGetter"))
                        callStatic = insn.getOpcode() == Opcodes.INVOKESTATIC;
                }
                noRcvLeft = (aload0 == 0); // the only this-load was the removed receiver
            }
        }

        boolean serOk;
        int len = 0;
        try {
            SafeCW cw = new SafeCW(ClassWriter.COMPUTE_FRAMES | ClassWriter.COMPUTE_MAXS);
            cn.accept(cw);
            len = cw.toByteArray().length;
            serOk = true;
        } catch (Throwable t) { serOk = false; System.out.println("re-serialize threw: " + t); }

        System.out.println("shadowed=" + shadowed + " callfixed=" + callfixed);
        System.out.println("setGetter static+!abstract=" + sgStatic + " hasBody=" + sgBody);
        System.out.println("clearGetter call invokestatic=" + callStatic + " noReceiverAload0Left=" + noRcvLeft);
        System.out.println("COMPUTE_FRAMES re-serialize OK=" + serOk + " (" + len + " bytes)");
        boolean pass = shadowed && callfixed && sgStatic && sgBody && callStatic && noRcvLeft && serOk;
        System.out.println(pass ? "RESULT: PASS" : "RESULT: FAIL");
        if (!pass) System.exit(1);
    }
}
