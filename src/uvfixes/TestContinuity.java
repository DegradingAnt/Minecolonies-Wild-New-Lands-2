import org.objectweb.asm.*;
import org.objectweb.asm.tree.*;
import org.openjdk.nashorn.api.scripting.ScriptObjectMirror;

import javax.script.Invocable;
import javax.script.ScriptEngine;
import java.nio.file.Files;
import java.nio.file.Path;

// Offline test for PackFixes Fix 31: ModelWrappingHandler.wrap() skip-DO guard.
public class TestContinuity {
    static final String WRAP_DESC =
        "(Lnet/minecraft/client/resources/model/BakedModel;Lnet/minecraft/resources/ResourceLocation;Lnet/minecraft/client/resources/model/ModelResourceLocation;)Lnet/minecraft/client/resources/model/BakedModel;";

    public static void main(String[] args) throws Exception {
        ScriptEngine engine = new org.openjdk.nashorn.api.scripting.NashornScriptEngineFactory().getScriptEngine();
        engine.eval(Files.readString(Path.of("uvfixes-src/coremods/uvfixes.js")));
        System.out.println("[0] uvfixes.js evaluated WITHOUT error: PASS");
        ScriptObjectMirror transformers =
            (ScriptObjectMirror) ((Invocable) engine).invokeFunction("initializeCoreMod");
        System.out.println("[0b] initializeCoreMod() entries=" + transformers.size());

        ClassNode in = new ClassNode();
        new ClassReader(Files.readAllBytes(Path.of(
            ".uvrun/cont2/me/pepperbell/continuity/client/resource/ModelWrappingHandler.class")))
            .accept(in, 0);
        int wrapBefore = -1;
        for (MethodNode m : in.methods) if (m.name.equals("wrap") && m.desc.equals(WRAP_DESC)) wrapBefore = m.instructions.size();

        ScriptObjectMirror entry = (ScriptObjectMirror) transformers.get("uvfixes_continuity_skip_domum");
        if (entry == null) { System.out.println("FAIL: missing entry uvfixes_continuity_skip_domum"); return; }
        ScriptObjectMirror fn = (ScriptObjectMirror) entry.get("transformer");
        ClassNode out = (ClassNode) fn.call(entry, in);

        int wrapAfter = -1; boolean hasInstanceof = false;
        for (MethodNode m : out.methods) if (m.name.equals("wrap") && m.desc.equals(WRAP_DESC)) {
            wrapAfter = m.instructions.size();
            for (AbstractInsnNode n : m.instructions.toArray())
                if (n instanceof TypeInsnNode && n.getOpcode() == Opcodes.INSTANCEOF
                    && ((TypeInsnNode) n).desc.equals("com/ldtteam/domumornamentum/client/model/baked/MateriallyTexturedBakedModel"))
                    hasInstanceof = true;
        }
        boolean guardAdded = wrapAfter > wrapBefore && hasInstanceof;

        boolean writes = false;
        try {
            ClassWriter cw = new ClassWriter(ClassWriter.COMPUTE_FRAMES) {
                protected String getCommonSuperClass(String a, String b) {
                    try { return super.getCommonSuperClass(a, b); } catch (Throwable t) { return "java/lang/Object"; }
                }
            };
            out.accept(cw); writes = true;
        } catch (Throwable t) { System.out.println("  write error: " + t); }

        System.out.println("wrap() insns " + wrapBefore + "->" + wrapAfter
            + " | instanceof-DO guard=" + hasInstanceof + " | classWrites=" + writes);
        boolean pass = guardAdded && writes && wrapBefore > 0;
        System.out.println(pass ? "\n==== Fix31 PASS ====" : "\n==== Fix31 FAIL ====");
    }
}
