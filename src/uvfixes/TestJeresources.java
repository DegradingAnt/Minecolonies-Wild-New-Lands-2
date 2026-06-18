import org.objectweb.asm.*;
import org.objectweb.asm.tree.*;
import org.openjdk.nashorn.api.scripting.ScriptObjectMirror;
import javax.script.Invocable;
import javax.script.ScriptEngine;
import java.nio.file.Files;
import java.nio.file.Path;

// Offline test for the jeresources VillagersHelper.getPoiBlocks(Predicate) crash guard.
public class TestJeresources {
    static final String DESC = "(Ljava/util/function/Predicate;)Ljava/util/Set;";
    public static void main(String[] args) throws Exception {
        ScriptEngine engine = new org.openjdk.nashorn.api.scripting.NashornScriptEngineFactory().getScriptEngine();
        engine.eval(Files.readString(Path.of("uvfixes-src/coremods/uvfixes.js")));
        System.out.println("[0] uvfixes.js evaluated WITHOUT error: PASS");
        ScriptObjectMirror transformers =
            (ScriptObjectMirror) ((Invocable) engine).invokeFunction("initializeCoreMod");
        System.out.println("[0b] initializeCoreMod() entries=" + transformers.size());

        ClassNode in = new ClassNode();
        new ClassReader(Files.readAllBytes(Path.of(
            ".uvrun/jer/jeresources/util/VillagersHelper.class"))).accept(in, 0);
        int before = -1, tcbBefore = 0;
        for (MethodNode m : in.methods) if (m.name.equals("getPoiBlocks") && m.desc.equals(DESC)) {
            before = m.instructions.size();
            tcbBefore = m.tryCatchBlocks == null ? 0 : m.tryCatchBlocks.size();
        }

        ScriptObjectMirror entry = (ScriptObjectMirror) transformers.get("uvfixes_jeresources_villager_poi_guard");
        if (entry == null) { System.out.println("FAIL: missing entry"); return; }
        ScriptObjectMirror fn = (ScriptObjectMirror) entry.get("transformer");
        ClassNode out = (ClassNode) fn.call(entry, in);

        int after = -1, tcbAfter = 0; boolean hasEmptySet = false;
        for (MethodNode m : out.methods) if (m.name.equals("getPoiBlocks") && m.desc.equals(DESC)) {
            after = m.instructions.size();
            tcbAfter = m.tryCatchBlocks.size();
            for (AbstractInsnNode n : m.instructions.toArray())
                if (n instanceof MethodInsnNode && ((MethodInsnNode) n).name.equals("emptySet")
                        && ((MethodInsnNode) n).owner.equals("java/util/Collections")) hasEmptySet = true;
        }
        boolean writes = false;
        try {
            ClassWriter cw = new ClassWriter(ClassWriter.COMPUTE_FRAMES) {
                protected String getCommonSuperClass(String a, String b) {
                    try { return super.getCommonSuperClass(a, b); } catch (Throwable t) { return "java/lang/Object"; }
                }
            };
            out.accept(cw); writes = true;
        } catch (Throwable t) { System.out.println("  write error: " + t); }

        System.out.println("getPoiBlocks insns " + before + "->" + after + " | tryCatch " + tcbBefore + "->" + tcbAfter
            + " | emptySet=" + hasEmptySet + " | classWrites=" + writes);
        boolean pass = after > before && tcbAfter == tcbBefore + 1 && hasEmptySet && writes && before > 0;
        System.out.println(pass ? "\n==== jeresources PASS ====" : "\n==== jeresources FAIL ====");
    }
}
