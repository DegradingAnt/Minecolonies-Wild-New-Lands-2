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

// Offline test for PackFixes Fix 61: uvfixes_stringrepresentable_dedupe_namelookup.
// Loads the real net.minecraft.util.StringRepresentable, applies the transform, asserts the wnl$dedupeByName
// helper was added + createNameLookup got the head INVOKESTATIC to it, and the class re-serializes under
// COMPUTE_FRAMES (proves the hand-built helper bytecode + head insertion are valid).
public class TestStringRepDedup {
    static final String JAR = "C:/Users/linde/curseforge/minecraft/Install/libraries/net/minecraft/client/1.21.1-20240808.144430/client-1.21.1-20240808.144430-srg.jar";
    static final String CLS = "net/minecraft/util/StringRepresentable.class";
    static final String HELPER = "wnl$dedupeByName";
    static final String CNL = "createNameLookup";
    static final String CNL_DESC = "([Lnet/minecraft/util/StringRepresentable;Ljava/util/function/Function;)Ljava/util/function/Function;";

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
    static boolean hasMethod(ClassNode cn, String name) {
        for (MethodNode m : cn.methods) if (m.name.equals(name)) return true;
        return false;
    }
    static boolean headCallsHelper(ClassNode cn) {
        for (MethodNode m : cn.methods) {
            if (!m.name.equals(CNL) || !m.desc.equals(CNL_DESC)) continue;
            for (AbstractInsnNode i : m.instructions.toArray()) {
                if (i instanceof MethodInsnNode mi && mi.getOpcode() == Opcodes.INVOKESTATIC && mi.name.equals(HELPER)) return true;
            }
        }
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
        boolean helperBefore = hasMethod(cn, HELPER);

        ScriptObjectMirror entry = (ScriptObjectMirror) T.get("uvfixes_stringrepresentable_dedupe_namelookup");
        if (entry == null) { System.out.println("FAIL: Fix 61 entry missing"); return; }
        ((ScriptObjectMirror) entry.get("transformer")).call(entry, cn);

        boolean helperAfter = hasMethod(cn, HELPER);
        boolean headCall = headCallsHelper(cn);
        boolean verified = verify(cn);

        System.out.println("helper wnl$dedupeByName present: " + helperBefore + " -> " + helperAfter);
        System.out.println("createNameLookup head calls helper: " + headCall);
        System.out.println("COMPUTE_FRAMES re-serialize: " + (verified ? "OK" : "FAILED"));
        boolean ok = !helperBefore && helperAfter && headCall && verified;
        System.out.println("\n==== TestStringRepDedup: " + (ok ? "PASS ====" : "FAIL ===="));
    }
}
