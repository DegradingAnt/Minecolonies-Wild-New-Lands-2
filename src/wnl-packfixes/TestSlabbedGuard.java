import org.objectweb.asm.*;
import org.objectweb.asm.tree.*;
import org.openjdk.nashorn.api.scripting.ScriptObjectMirror;
import javax.script.Invocable;
import javax.script.ScriptEngine;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.zip.ZipEntry;
import java.util.zip.ZipFile;

// Offline test for PackFixes Fix 60: uvfixes_slabbed_anchor_reentrant_getchunk.
// Loads slabbed's SlabAnchorAttachment, applies the transform, asserts the non-blocking helper was added,
// the blocking Level.getChunk(II) in isAnchored is redirected to INVOKESTATIC <helper>, and the class
// re-serializes under COMPUTE_FRAMES (proves the added method + redirect are valid bytecode).
public class TestSlabbedGuard {
    static final String JAR = "mods/slabbed-0.4.2-beta.1+26.2.jar";
    static final String CLS = "com/slabbed/anchor/SlabAnchorAttachment.class";
    static final String HELPER = "wnl$nbGetChunk";

    static byte[] fromJar(String jar, String entry) throws Exception {
        try (ZipFile z = new ZipFile(jar)) {
            ZipEntry e = z.getEntry(entry);
            if (e == null) throw new RuntimeException("entry not found: " + entry);
            try (InputStream in = z.getInputStream(e)) { return in.readAllBytes(); }
        }
    }
    static ClassNode read(byte[] b) { ClassNode cn = new ClassNode(); new ClassReader(b).accept(cn, 0); return cn; }
    static final class SafeCW extends ClassWriter {
        SafeCW(int f) { super(f); }
        @Override protected String getCommonSuperClass(String a, String b) {
            try { return super.getCommonSuperClass(a, b); } catch (Throwable t) { return "java/lang/Object"; }
        }
    }
    static boolean verify(ClassNode cn) {
        try { ClassWriter cw = new SafeCW(ClassWriter.COMPUTE_FRAMES | ClassWriter.COMPUTE_MAXS); cn.accept(cw); return true; }
        catch (Throwable t) { System.out.println("    VERIFY/WRITE ERROR: " + t); return false; }
    }
    // count blocking-getChunk INVOKEVIRTUAL + helper INVOKESTATIC across all methods (excluding the helper itself)
    static int[] count(ClassNode cn) {
        int virt = 0, stat = 0;
        for (MethodNode m : cn.methods) {
            if (m.name.equals(HELPER)) continue;
            for (AbstractInsnNode i : m.instructions.toArray()) {
                if (i instanceof MethodInsnNode mi && mi.name.equals("getChunk")
                    && mi.owner.equals("net/minecraft/world/level/Level") && mi.getOpcode() == Opcodes.INVOKEVIRTUAL
                    && mi.desc.equals("(II)Lnet/minecraft/world/level/chunk/LevelChunk;")) virt++;
                if (i instanceof MethodInsnNode mi2 && mi2.name.equals(HELPER) && mi2.getOpcode() == Opcodes.INVOKESTATIC) stat++;
            }
        }
        return new int[]{virt, stat};
    }
    static boolean hasHelper(ClassNode cn) {
        for (MethodNode m : cn.methods) if (m.name.equals(HELPER)) return true;
        return false;
    }

    public static void main(String[] args) throws Exception {
        java.util.Set<String> WL_CLASSES = java.util.Set.of(
            "net.neoforged.coremod.api.ASMAPI",
            "org.objectweb.asm.Attribute","org.objectweb.asm.Handle","org.objectweb.asm.Label",
            "org.objectweb.asm.Opcodes","org.objectweb.asm.Type","org.objectweb.asm.TypePath",
            "org.objectweb.asm.TypeReference","org.objectweb.asm.tree.AbstractInsnNode",
            "org.objectweb.asm.tree.FieldInsnNode","org.objectweb.asm.tree.FieldNode","org.objectweb.asm.tree.FrameNode",
            "org.objectweb.asm.tree.IincInsnNode","org.objectweb.asm.tree.InsnList","org.objectweb.asm.tree.InsnNode",
            "org.objectweb.asm.tree.IntInsnNode","org.objectweb.asm.tree.InvokeDynamicInsnNode","org.objectweb.asm.tree.JumpInsnNode",
            "org.objectweb.asm.tree.LabelNode","org.objectweb.asm.tree.LdcInsnNode","org.objectweb.asm.tree.LineNumberNode",
            "org.objectweb.asm.tree.LocalVariableAnnotationNode","org.objectweb.asm.tree.LocalVariableNode",
            "org.objectweb.asm.tree.LookupSwitchInsnNode","org.objectweb.asm.tree.MethodInsnNode","org.objectweb.asm.tree.MethodNode",
            "org.objectweb.asm.tree.MultiANewArrayInsnNode","org.objectweb.asm.tree.ParameterNode",
            "org.objectweb.asm.tree.TableSwitchInsnNode","org.objectweb.asm.tree.TryCatchBlockNode",
            "org.objectweb.asm.tree.TypeAnnotationNode","org.objectweb.asm.tree.TypeInsnNode","org.objectweb.asm.tree.VarInsnNode");
        java.util.Set<String> WL_PKGS = java.util.Set.of("java.util","java.util.function","org.objectweb.asm.util");
        org.openjdk.nashorn.api.scripting.ClassFilter filter = name -> {
            if (WL_CLASSES.contains(name)) return true;
            int dot = name.lastIndexOf('.');
            return dot != -1 && WL_PKGS.contains(name.substring(0, dot));
        };
        ScriptEngine engine = new org.openjdk.nashorn.api.scripting.NashornScriptEngineFactory()
            .getScriptEngine(new String[]{"--language=es6"}, ClassLoader.getSystemClassLoader(), filter);
        engine.eval(Files.readString(Path.of("_dev/wnl-packfixes-src/coremods/uvfixes.js")));
        engine.eval("log = function(s){ print('    [coremod] ' + s); };");
        ScriptObjectMirror T = (ScriptObjectMirror) ((Invocable) engine).invokeFunction("initializeCoreMod");

        ClassNode cn = read(fromJar(JAR, CLS));
        int[] before = count(cn);
        boolean helperBefore = hasHelper(cn);

        ScriptObjectMirror entry = (ScriptObjectMirror) T.get("uvfixes_slabbed_anchor_reentrant_getchunk");
        if (entry == null) { System.out.println("FAIL: Fix 60 entry missing"); return; }
        ((ScriptObjectMirror) entry.get("transformer")).call(entry, cn);

        int[] after = count(cn);
        boolean helperAfter = hasHelper(cn);
        boolean verified = verify(cn);

        System.out.println("helper method present: " + helperBefore + " -> " + helperAfter);
        System.out.println("blocking Level.getChunk(II) INVOKEVIRTUAL: " + before[0] + " -> " + after[0]);
        System.out.println("helper INVOKESTATIC redirects: " + before[1] + " -> " + after[1]);
        System.out.println("COMPUTE_FRAMES re-serialize: " + (verified ? "OK" : "FAILED"));
        boolean ok = !helperBefore && helperAfter && before[0] >= 1 && after[0] == 0 && after[1] == before[0] && verified;
        System.out.println("\n==== TestSlabbedGuard: " + (ok ? "PASS ====" : "FAIL ===="));
    }
}
