import org.objectweb.asm.*;
import org.objectweb.asm.tree.*;
import org.openjdk.nashorn.api.scripting.ScriptObjectMirror;

import javax.script.Invocable;
import javax.script.ScriptEngine;
import java.nio.file.Files;
import java.nio.file.Path;

// Offline test for PackFixes Fix 39 (uvfixes_domum_slab_material_face_on_drop):
// patches DO's RetexturedBakedModelBuilder.getRetexturingQuad so its POST-GUARD
// Optional.empty() tail (fired when the material model emits no quad for the slab's
// exposed face -> DO drops the face -> invisible slab top) instead returns
//   Optional.of(new ModelSpriteQuadTransformerData(
//       new BakedQuad(src.getVertices(), src.getTintIndex(), src.getDirection(),
//                     modelData.model().getParticleIcon(ModelData.EMPTY), true, true),
//       modelData.state()))
// so retexture()'s existing .map(ModelSpriteQuadTransformer) runs and the dropped face
// reappears textured with the MATERIAL particle sprite. The two earlier Optional.empty()
// returns (needsRetexturing guard, needsErasure guard) are left untouched, so erased faces
// stay invisible and non-placeholder faces are unchanged.
//
// Verifies:
//   (a) getRetexturingQuad lost exactly ONE Optional.empty() (3 -> 2: the post-guard tail
//       was replaced; the two guard returns survive),
//   (b) getRetexturingQuad gained: NEW BakedQuad, NEW ModelSpriteQuadTransformerData,
//       INVOKEINTERFACE BakedModel.getParticleIcon, INVOKESTATIC Optional.of,
//       INVOKEVIRTUAL ReplacementModelData.model + ReplacementModelData.state,
//   (c) retexture() is byte-identical (the erasure path is NOT touched) -- both its
//       Optional.empty() guard returns survive (count unchanged),
//   (d) lambda$build$0 and lambda$build$2 are UNTOUCHED (still call Optional.ifPresent;
//       the working-face/present path stays byte-identical),
//   (e) the patched class re-serializes under COMPUTE_FRAMES (valid, verifiable bytecode),
//   (f) the transform reports patched (checked via the explicit structural asserts above).
public class TestDomumSlab {
    static final String ENTRY = "uvfixes_domum_slab_material_face_on_drop";
    static final String CLASS_PATH = ".uvrun/doslab/RetexturedBakedModelBuilder.class";
    static final String GETRETEX_DESC =
        "(Lnet/minecraft/client/renderer/block/model/BakedQuad;Lnet/minecraft/core/Direction;)Ljava/util/Optional;";
    static final String REPL_DATA =
        "com/ldtteam/domumornamentum/client/model/baked/RetexturedBakedModelBuilder$ReplacementModelData";
    static final String XFORM_DATA =
        "com/ldtteam/domumornamentum/client/model/utils/ModelSpriteQuadTransformerData";
    static final String BAKED_QUAD = "net/minecraft/client/renderer/block/model/BakedQuad";

    static MethodNode find(ClassNode cn, String name, String desc) {
        for (MethodNode m : cn.methods) if (m.name.equals(name) && (desc == null || m.desc.equals(desc))) return m;
        return null;
    }
    static int countInvoke(MethodNode m, int op, String owner, String name, String desc) {
        int c = 0;
        for (AbstractInsnNode n : m.instructions.toArray())
            if (n instanceof MethodInsnNode) {
                MethodInsnNode mi = (MethodInsnNode) n;
                if (n.getOpcode() == op && mi.owner.equals(owner) && mi.name.equals(name)
                        && (desc == null || mi.desc.equals(desc))) c++;
            }
        return c;
    }
    static int countNew(MethodNode m, String type) {
        int c = 0;
        for (AbstractInsnNode n : m.instructions.toArray())
            if (n instanceof TypeInsnNode && n.getOpcode() == Opcodes.NEW && ((TypeInsnNode) n).desc.equals(type)) c++;
        return c;
    }
    static byte[] serialize(MethodNode m, ClassNode owner) {
        // serialize the whole class but return a stable hash basis for just the method by
        // comparing instruction sequences textually
        StringBuilder sb = new StringBuilder();
        for (AbstractInsnNode n : m.instructions.toArray()) {
            sb.append(n.getOpcode());
            if (n instanceof MethodInsnNode) { MethodInsnNode x=(MethodInsnNode)n; sb.append(' ').append(x.owner).append('.').append(x.name).append(x.desc); }
            else if (n instanceof FieldInsnNode) { FieldInsnNode x=(FieldInsnNode)n; sb.append(' ').append(x.owner).append('.').append(x.name); }
            else if (n instanceof TypeInsnNode) { sb.append(' ').append(((TypeInsnNode)n).desc); }
            else if (n instanceof VarInsnNode) { sb.append(' ').append(((VarInsnNode)n).var); }
            sb.append('\n');
        }
        return sb.toString().getBytes();
    }

    public static void main(String[] args) throws Exception {
        ScriptEngine engine = new org.openjdk.nashorn.api.scripting.NashornScriptEngineFactory().getScriptEngine();
        engine.eval(Files.readString(Path.of("uvfixes-src/coremods/uvfixes.js")));
        System.out.println("[0] uvfixes.js evaluated WITHOUT error: PASS");
        ScriptObjectMirror transformers =
            (ScriptObjectMirror) ((Invocable) engine).invokeFunction("initializeCoreMod");
        System.out.println("[0b] initializeCoreMod() entries=" + transformers.size());

        ClassNode in = new ClassNode();
        new ClassReader(Files.readAllBytes(Path.of(CLASS_PATH))).accept(in, 0);

        MethodNode gBefore  = find(in, "getRetexturingQuad", GETRETEX_DESC);
        MethodNode rBefore  = find(in, "retexture", GETRETEX_DESC);
        MethodNode l0Before = find(in, "lambda$build$0", null);
        MethodNode l2Before = find(in, "lambda$build$2", null);
        if (gBefore == null || rBefore == null || l0Before == null || l2Before == null) {
            System.out.println("FAIL: required methods not found in class"); return;
        }

        int gEmptyBefore   = countInvoke(gBefore, Opcodes.INVOKESTATIC, "java/util/Optional", "empty", "()Ljava/util/Optional;");
        int gOfBefore      = countInvoke(gBefore, Opcodes.INVOKESTATIC, "java/util/Optional", "of", null);
        int gNewQuadBefore = countNew(gBefore, BAKED_QUAD);
        int gNewDataBefore = countNew(gBefore, XFORM_DATA);
        int gParticleBefore= countInvoke(gBefore, Opcodes.INVOKEINTERFACE, "net/minecraft/client/resources/model/BakedModel", "getParticleIcon", null);
        // getRetexturingQuad's NORMAL path already builds a ModelSpriteQuadTransformerData and calls
        // ReplacementModelData.state()/.model() -- so baseline these and assert the DELTA, not absolutes.
        int gNewDataBeforeC= countNew(gBefore, XFORM_DATA);
        int gDataCtorBefore= countInvoke(gBefore, Opcodes.INVOKESPECIAL, XFORM_DATA, "<init>", null);
        int gStateBefore   = countInvoke(gBefore, Opcodes.INVOKEVIRTUAL, REPL_DATA, "state", null);
        int gModelBefore   = countInvoke(gBefore, Opcodes.INVOKEVIRTUAL, REPL_DATA, "model", null);
        int rEmptyBefore   = countInvoke(rBefore, Opcodes.INVOKESTATIC, "java/util/Optional", "empty", "()Ljava/util/Optional;");
        byte[] rSigBefore  = serialize(rBefore, in);
        byte[] l0SigBefore = serialize(l0Before, in);
        byte[] l2SigBefore = serialize(l2Before, in);

        ScriptObjectMirror entry = (ScriptObjectMirror) transformers.get(ENTRY);
        if (entry == null) { System.out.println("FAIL: missing entry " + ENTRY); return; }
        ScriptObjectMirror fn = (ScriptObjectMirror) entry.get("transformer");
        ClassNode out = (ClassNode) fn.call(entry, in);

        MethodNode g  = find(out, "getRetexturingQuad", GETRETEX_DESC);
        MethodNode r  = find(out, "retexture", GETRETEX_DESC);
        MethodNode l0 = find(out, "lambda$build$0", null);
        MethodNode l2 = find(out, "lambda$build$2", null);

        int gEmptyAfter   = countInvoke(g, Opcodes.INVOKESTATIC, "java/util/Optional", "empty", "()Ljava/util/Optional;");
        int gOfAfter      = countInvoke(g, Opcodes.INVOKESTATIC, "java/util/Optional", "of", null);
        int gNewQuadAfter = countNew(g, BAKED_QUAD);
        int gNewDataAfter = countNew(g, XFORM_DATA);
        int gParticleAfter= countInvoke(g, Opcodes.INVOKEINTERFACE, "net/minecraft/client/resources/model/BakedModel", "getParticleIcon", null);
        int gModelAfter   = countInvoke(g, Opcodes.INVOKEVIRTUAL, REPL_DATA, "model", null);
        int gStateAfter   = countInvoke(g, Opcodes.INVOKEVIRTUAL, REPL_DATA, "state", null);
        int gQuadCtor     = countInvoke(g, Opcodes.INVOKESPECIAL, BAKED_QUAD, "<init>", null);
        int gDataCtor     = countInvoke(g, Opcodes.INVOKESPECIAL, XFORM_DATA, "<init>", null);
        int rEmptyAfter   = countInvoke(r, Opcodes.INVOKESTATIC, "java/util/Optional", "empty", "()Ljava/util/Optional;");

        // (a) exactly one Optional.empty removed from getRetexturingQuad (post-guard tail)
        boolean emptyDropped = (gEmptyBefore - gEmptyAfter) == 1 && gEmptyBefore == 3;
        // (b) the material-quad machinery was added
        boolean addedOf      = (gOfAfter - gOfBefore) == 1;
        boolean addedQuad    = (gNewQuadAfter - gNewQuadBefore) == 1 && gQuadCtor == 1;
        // one NEW+<init> of ModelSpriteQuadTransformerData added on top of the pre-existing normal-path one
        boolean addedData    = (gNewDataAfter - gNewDataBeforeC) == 1 && (gDataCtor - gDataCtorBefore) == 1;
        boolean addedParticle= (gParticleAfter - gParticleBefore) == 1;
        // one extra ReplacementModelData.model() and one extra .state() over the normal-path baseline
        boolean addedModelState = (gModelAfter - gModelBefore) == 1 && (gStateAfter - gStateBefore) == 1;
        // (c) retexture() untouched (erasure path preserved): both guards survive, body byte-identical
        boolean retexUntouched = rEmptyAfter == rEmptyBefore && rEmptyBefore == 2
                              && java.util.Arrays.equals(rSigBefore, serialize(r, out));
        // (d) consumer lambdas untouched
        boolean lambdasUntouched = java.util.Arrays.equals(l0SigBefore, serialize(l0, out))
                                && java.util.Arrays.equals(l2SigBefore, serialize(l2, out))
                                && countInvoke(l0, Opcodes.INVOKEVIRTUAL, "java/util/Optional", "ifPresent", null) == 1
                                && countInvoke(l2, Opcodes.INVOKEVIRTUAL, "java/util/Optional", "ifPresent", null) == 1;

        // (e) re-serialize with COMPUTE_FRAMES
        boolean writes = false;
        try {
            ClassWriter cw = new ClassWriter(ClassWriter.COMPUTE_FRAMES) {
                protected String getCommonSuperClass(String a, String b) {
                    try { return super.getCommonSuperClass(a, b); } catch (Throwable t) { return "java/lang/Object"; }
                }
            };
            out.accept(cw); writes = true;
        } catch (Throwable t) { System.out.println("  write error: " + t); t.printStackTrace(); }

        System.out.println("getRetexturingQuad: Optional.empty " + gEmptyBefore + "->" + gEmptyAfter
            + " | Optional.of " + gOfBefore + "->" + gOfAfter
            + " | NEW BakedQuad " + gNewQuadBefore + "->" + gNewQuadAfter + " (ctor=" + gQuadCtor + ")"
            + " | NEW XformData " + gNewDataBefore + "->" + gNewDataAfter + " (ctor=" + gDataCtor + ")"
            + " | getParticleIcon " + gParticleBefore + "->" + gParticleAfter
            + " | ReplData.model=" + gModelAfter + " state=" + gStateAfter);
        System.out.println("retexture(): Optional.empty " + rEmptyBefore + "->" + rEmptyAfter
            + " | body-identical=" + java.util.Arrays.equals(rSigBefore, serialize(r, out)));
        System.out.println("lambdas: $0-identical=" + java.util.Arrays.equals(l0SigBefore, serialize(l0, out))
            + " $2-identical=" + java.util.Arrays.equals(l2SigBefore, serialize(l2, out)));
        System.out.println("checks: emptyDropped=" + emptyDropped + " addedOf=" + addedOf
            + " addedQuad=" + addedQuad + " addedData=" + addedData + " addedParticle=" + addedParticle
            + " addedModelState=" + addedModelState + " retexUntouched=" + retexUntouched
            + " lambdasUntouched=" + lambdasUntouched + " classWrites=" + writes);

        boolean pass = emptyDropped && addedOf && addedQuad && addedData && addedParticle
                    && addedModelState && retexUntouched && lambdasUntouched && writes;
        System.out.println(pass ? "\n==== DomumSlab PASS ====" : "\n==== DomumSlab FAIL ====");
    }
}
