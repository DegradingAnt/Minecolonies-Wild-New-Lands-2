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

// Offline test for PackFixes Fix 59: uvfixes_minecolonies_research_cost_resilience.
// Loads the REAL minecolonies ResearchListener under the faithful coremod ClassFilter, applies the
// transformer, asserts parseResearchCosts gained a Throwable try/catch returning a fresh ArrayList,
// and re-serializes with COMPUTE_FRAMES (Object-fallback super resolver) to prove the bytecode verifies.
public class TestResearchGuard {
    static final String MC = "mods/minecolonies-1.1.1341-1.21.1-snapshot.jar";
    static final String CLS = "com/minecolonies/core/datalistener/ResearchListener.class";
    static final String METH = "parseResearchCosts";
    static final String DESC = "(Lnet/minecraft/resources/ResourceLocation;Lcom/google/gson/JsonArray;Lcom/google/gson/JsonArray;)Ljava/util/List;";

    static byte[] fromJar(String jar, String entry) throws Exception {
        try (ZipFile z = new ZipFile(jar)) {
            ZipEntry e = z.getEntry(entry);
            if (e == null) throw new RuntimeException("entry not found: " + entry);
            try (InputStream in = z.getInputStream(e)) { return in.readAllBytes(); }
        }
    }
    static ClassNode read(byte[] b) { ClassNode cn = new ClassNode(); new ClassReader(b).accept(cn, 0); return cn; }
    static MethodNode method(ClassNode cn) {
        for (MethodNode m : cn.methods) if (m.name.equals(METH) && m.desc.equals(DESC)) return m;
        return null;
    }
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

        ClassNode cn = read(fromJar(MC, CLS));
        MethodNode before = method(cn);
        if (before == null) { System.out.println("FAIL: target method not found (mod changed?)"); return; }
        int tcbBefore = before.tryCatchBlocks == null ? 0 : before.tryCatchBlocks.size();

        ScriptObjectMirror entry = (ScriptObjectMirror) T.get("uvfixes_minecolonies_research_cost_resilience");
        if (entry == null) { System.out.println("FAIL: Fix 59 entry missing"); return; }
        ((ScriptObjectMirror) entry.get("transformer")).call(entry, cn);

        MethodNode after = method(cn);
        int tcbAfter = after.tryCatchBlocks == null ? 0 : after.tryCatchBlocks.size();
        boolean hasThrowable = false;
        if (after.tryCatchBlocks != null)
            for (TryCatchBlockNode t : after.tryCatchBlocks) if ("java/lang/Throwable".equals(t.type)) hasThrowable = true;
        boolean hasArrayListNew = false, hasArrayListInit = false, hasAreturn = false;
        for (AbstractInsnNode i : after.instructions.toArray()) {
            if (i instanceof TypeInsnNode && i.getOpcode() == Opcodes.NEW && "java/util/ArrayList".equals(((TypeInsnNode) i).desc)) hasArrayListNew = true;
            if (i instanceof MethodInsnNode && i.getOpcode() == Opcodes.INVOKESPECIAL
                && "java/util/ArrayList".equals(((MethodInsnNode) i).owner) && "<init>".equals(((MethodInsnNode) i).name)) hasArrayListInit = true;
            if (i.getOpcode() == Opcodes.ARETURN) hasAreturn = true;
        }
        boolean verified = verify(cn);

        System.out.println("tryCatchBlocks " + tcbBefore + " -> " + tcbAfter + " (Throwable-handler=" + hasThrowable + ")");
        System.out.println("catch returns new ArrayList: NEW=" + hasArrayListNew + " <init>=" + hasArrayListInit + " ARETURN=" + hasAreturn);
        System.out.println("COMPUTE_FRAMES re-serialize: " + (verified ? "OK" : "FAILED"));
        boolean ok = tcbAfter == tcbBefore + 1 && hasThrowable && hasArrayListNew && hasArrayListInit && hasAreturn && verified;
        System.out.println("\n==== TestResearchGuard: " + (ok ? "PASS ====" : "FAIL ===="));
    }
}
