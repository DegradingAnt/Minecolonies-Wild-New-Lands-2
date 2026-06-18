import org.objectweb.asm.*;
import org.objectweb.asm.tree.*;
import org.openjdk.nashorn.api.scripting.ScriptObjectMirror;

import javax.script.Invocable;
import javax.script.ScriptEngine;
import java.nio.file.Files;
import java.nio.file.Path;

// Offline test for PackFixes Fix 30: add MateriallyTexturedBakedModel.emitItemQuads so DO
// renders its per-item getRenderPasses sub-models on FFAPI's Indigo path (fixes blank icons
// when DO's model is wrapped by Continuity emissive/CTM, SnowRealMagic, etc.).
public class TestDomum {
    static final String DESC =
        "(Lnet/minecraft/world/item/ItemStack;Ljava/util/function/Supplier;Lnet/fabricmc/fabric/api/renderer/v1/render/RenderContext;)V";

    public static void main(String[] args) throws Exception {
        ScriptEngine engine = new org.openjdk.nashorn.api.scripting.NashornScriptEngineFactory().getScriptEngine();
        engine.eval(Files.readString(Path.of("uvfixes-src/coremods/uvfixes.js")));
        System.out.println("[0] uvfixes.js evaluated WITHOUT error: PASS");
        ScriptObjectMirror transformers =
            (ScriptObjectMirror) ((Invocable) engine).invokeFunction("initializeCoreMod");
        System.out.println("[0b] initializeCoreMod() entries=" + transformers.size());

        ClassNode in = new ClassNode();
        new ClassReader(Files.readAllBytes(Path.of(
            ".uvrun/fr/com/ldtteam/domumornamentum/client/model/baked/MateriallyTexturedBakedModel.class")))
            .accept(in, 0);
        int before = in.methods.size();
        boolean hadBefore = false;
        for (MethodNode m : in.methods) if (m.name.equals("emitItemQuads") && m.desc.equals(DESC)) hadBefore = true;

        ScriptObjectMirror entry = (ScriptObjectMirror) transformers.get("uvfixes_domum_emititemquads");
        if (entry == null) { System.out.println("FAIL: missing entry uvfixes_domum_emititemquads"); return; }
        ScriptObjectMirror fn = (ScriptObjectMirror) entry.get("transformer");
        ClassNode out = (ClassNode) fn.call(entry, in);

        MethodNode added = null;
        for (MethodNode m : out.methods) if (m.name.equals("emitItemQuads") && m.desc.equals(DESC)) added = m;
        boolean methodAdded = added != null;
        boolean isPublic = methodAdded && (added.access & Opcodes.ACC_PUBLIC) != 0;
        int insnCount = methodAdded ? added.instructions.size() : -1;

        // idempotency: applying twice must not add a 2nd emitItemQuads
        ClassNode out2 = (ClassNode) fn.call(entry, out);
        int stubs = 0; for (MethodNode m : out2.methods) if (m.name.equals("emitItemQuads") && m.desc.equals(DESC)) stubs++;
        boolean idempotent = stubs == 1;

        // bytecode validity: write with COMPUTE_FRAMES (tolerant common-superclass like ModLauncher)
        boolean writes = false;
        try {
            ClassWriter cw = new ClassWriter(ClassWriter.COMPUTE_FRAMES) {
                protected String getCommonSuperClass(String a, String b) {
                    try { return super.getCommonSuperClass(a, b); } catch (Throwable t) { return "java/lang/Object"; }
                }
            };
            out.accept(cw); writes = true;
        } catch (Throwable t) { System.out.println("  write error: " + t); }

        System.out.println("methods " + before + "->" + out.methods.size()
            + " | hadBefore=" + hadBefore + " added=" + methodAdded + " public=" + isPublic
            + " insns=" + insnCount + " idempotent=" + idempotent + " classWrites=" + writes);
        boolean pass = methodAdded && isPublic && idempotent && writes && !hadBefore;
        System.out.println(pass ? "\n==== Fix30 PASS ====" : "\n==== Fix30 FAIL ====");
    }
}
