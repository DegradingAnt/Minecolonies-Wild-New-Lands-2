import org.objectweb.asm.*;
import org.objectweb.asm.tree.*;
import java.io.*;
import java.util.*;
import java.util.zip.*;

// One-shot jar patch for Distant Horizons 3.1.0-b dedicated-server boot crash.
// DH Initializer.preConfigInit() runs client-only library validation; on failure it reports via
// MC_CLIENT.crashMinecraft(msg, throwable). On a dedicated server MC_CLIENT (the client wrapper)
// is null -> NPE during FMLDedicatedServerSetupEvent -> mod loading fails.
// Fix: add a null-guarded static helper dhfix$safeCrash(wrapper, msg, throwable) that no-ops when
// the wrapper is null, and redirect every MC_CLIENT.crashMinecraft(...) call site to it.
// Only Initializer is touched; preConfigInit's stack shape is unchanged (invokeinterface ->
// invokestatic, identical operand consumption), so existing frames stay valid and we avoid a
// whole-class frame recompute (ClassWriter flags=0). The new helper carries its one F_SAME frame.
public class PatchDhJar {
    static final String CLASS = "com/seibel/distanthorizons/core/Initializer";
    static final String CLASS_ENTRY = CLASS + ".class";
    static final String MC_WRAPPER = "com/seibel/distanthorizons/core/wrapperInterfaces/minecraft/IMinecraftClientWrapper";
    static final String CRASH_DESC = "(Ljava/lang/String;Ljava/lang/Throwable;)V";
    static final String SAFE = "dhfix$safeCrash";
    static final String SAFE_DESC = "(L" + MC_WRAPPER + ";Ljava/lang/String;Ljava/lang/Throwable;)V";

    public static void main(String[] args) throws Exception {
        String inJar = args[0], outJar = args[1];
        byte[] orig;
        try (ZipFile zf = new ZipFile(inJar)) {
            ZipEntry e = zf.getEntry(CLASS_ENTRY);
            if (e == null) throw new RuntimeException("class not found in jar: " + CLASS_ENTRY);
            orig = zf.getInputStream(e).readAllBytes();
        }
        ClassReader cr = new ClassReader(orig);
        ClassNode cn = new ClassNode();
        cr.accept(cn, ClassReader.EXPAND_FRAMES);

        // (1) redirect every MC_CLIENT.crashMinecraft(...) call to the null-guarded helper
        int redirected = 0;
        for (MethodNode m : cn.methods) {
            for (AbstractInsnNode insn : m.instructions.toArray()) {
                if (insn instanceof MethodInsnNode) {
                    MethodInsnNode mi = (MethodInsnNode) insn;
                    if (mi.getOpcode() == Opcodes.INVOKEINTERFACE
                            && mi.owner.equals(MC_WRAPPER)
                            && mi.name.equals("crashMinecraft")
                            && mi.desc.equals(CRASH_DESC)) {
                        m.instructions.set(insn, new MethodInsnNode(Opcodes.INVOKESTATIC, CLASS, SAFE, SAFE_DESC, false));
                        redirected++;
                    }
                }
            }
        }

        // (2) add: private static synthetic void dhfix$safeCrash(wrapper, msg, throwable)
        //         { if (wrapper != null) wrapper.crashMinecraft(msg, throwable); }
        MethodNode safe = new MethodNode(Opcodes.ACC_PRIVATE | Opcodes.ACC_STATIC | Opcodes.ACC_SYNTHETIC,
                SAFE, SAFE_DESC, null, null);
        InsnList il = safe.instructions;
        LabelNode ret = new LabelNode();
        il.add(new VarInsnNode(Opcodes.ALOAD, 0));            // wrapper
        il.add(new JumpInsnNode(Opcodes.IFNULL, ret));        // if null -> skip
        il.add(new VarInsnNode(Opcodes.ALOAD, 0));            // wrapper
        il.add(new VarInsnNode(Opcodes.ALOAD, 1));            // msg
        il.add(new VarInsnNode(Opcodes.ALOAD, 2));            // throwable
        il.add(new MethodInsnNode(Opcodes.INVOKEINTERFACE, MC_WRAPPER, "crashMinecraft", CRASH_DESC, true));
        il.add(ret);
        il.add(new FrameNode(Opcodes.F_SAME, 0, null, 0, null)); // locals=[wrapper,msg,throwable], stack=[]
        il.add(new InsnNode(Opcodes.RETURN));
        safe.maxStack = 3;
        safe.maxLocals = 3;
        cn.methods.add(safe);

        // write the patched class without recomputing frames for untouched methods
        ClassWriter cw = new ClassWriter(cr, 0);
        cn.accept(cw);
        byte[] patched = cw.toByteArray();

        // sanity: the patched bytes must re-parse cleanly
        new ClassReader(patched).accept(new ClassNode(), 0);

        // write a new jar: copy all entries, swap the class, add an unofficial-patch marker
        try (ZipFile zf = new ZipFile(inJar);
             ZipOutputStream zos = new ZipOutputStream(new BufferedOutputStream(new FileOutputStream(outJar)))) {
            Enumeration<? extends ZipEntry> en = zf.entries();
            while (en.hasMoreElements()) {
                ZipEntry e = en.nextElement();
                if (e.isDirectory()) { zos.putNextEntry(new ZipEntry(e.getName())); zos.closeEntry(); continue; }
                ZipEntry ne = new ZipEntry(e.getName());
                ne.setMethod(ZipEntry.DEFLATED);
                zos.putNextEntry(ne);
                if (e.getName().equals(CLASS_ENTRY)) zos.write(patched);
                else zf.getInputStream(e).transferTo(zos);
                zos.closeEntry();
            }
            zos.putNextEntry(new ZipEntry("META-INF/ULTIMATEVIBES-DH-PATCH.txt"));
            zos.write(("UNOFFICIAL PATCH - Ultimate Vibes pack (for the owner's own dedicated server).\n"
                    + "Patched com.seibel.distanthorizons.core.Initializer: redirected " + redirected
                    + " MC_CLIENT.crashMinecraft(...) call(s) through a null-guarded helper (dhfix$safeCrash)\n"
                    + "so DH 3.1.0-b no longer throws NullPointerException during FMLDedicatedServerSetupEvent\n"
                    + "(its client-only library validation has no client wrapper on a dedicated server).\n"
                    + "TEMPORARY - replace with the official jar once Distant Horizons ships an upstream fix.\n").getBytes("UTF-8"));
            zos.closeEntry();
        }

        System.out.println("redirected crashMinecraft calls : " + redirected + (redirected == 5 ? " (OK)" : " (WARNING: expected 5)"));
        System.out.println("patched class re-parsed OK; wrote: " + outJar);
    }
}
