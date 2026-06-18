import org.objectweb.asm.ClassReader;
import org.objectweb.asm.ClassWriter;
import org.objectweb.asm.tree.*;
import org.objectweb.asm.util.CheckClassAdapter;
import org.openjdk.nashorn.api.scripting.ScriptObjectMirror;

import javax.script.Invocable;
import javax.script.ScriptEngine;
import javax.script.ScriptEngineManager;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Map;

public class TestTransform {
    static ScriptObjectMirror transformers;

    public static void main(String[] args) throws Exception {
        ScriptEngine engine = new ScriptEngineManager().getEngineByName("nashorn");
        engine.eval(Files.readString(Path.of("jar/coremods/uvfixes.js")));
        transformers = (ScriptObjectMirror) ((Invocable) engine).invokeFunction("initializeCoreMod");

        // --- Fix 5: BufferKt regex swap ---
        ClassNode buf = apply("uvfixes_supplemental_rendertargets_regex",
                "C:/Windows/Temp/sp_inspect/io/github/jedlimlx/supplemental_patches/shaders/BufferKt.class");
        int oldRe = 0, newRe = 0;
        for (MethodNode m : buf.methods)
            for (AbstractInsnNode insn : m.instructions)
                if (insn instanceof LdcInsnNode ldc && ldc.cst instanceof String s) {
                    if (s.equals("RENDERTARGETS: ((\\d+,)*\\d+)")) oldRe++;
                    if (s.equals("RENDERTARGETS:\\s*((\\d+,)*\\d+)")) newRe++;
                }
        System.out.println("Fix5: old-regex remaining=" + oldRe + " new-regex present=" + newRe
                + (oldRe == 0 && newRe == 1 ? "  PASS" : "  FAIL"));
        // prove the new regex actually matches both comment styles
        var p = java.util.regex.Pattern.compile("RENDERTARGETS:\\s*((\\d+,)*\\d+)");
        System.out.println("Fix5 regex: nospace=" + p.matcher("/* RENDERTARGETS:0,6,4,10,11,20 */").find()
                + " spaced=" + p.matcher("/* RENDERTARGETS: 0,5,4,19 */").find());
        verify(buf);

        // --- Fix 6: VeilMixinPlugin shouldApplyMixin head-guard ---
        ClassNode veil = apply("uvfixes_veil_blit_mixin_disable",
                "C:/Windows/Temp/veil_inspect/f413/foundry/veil/impl/VeilMixinPlugin.class");
        MethodNode sam = veil.methods.stream()
                .filter(m -> m.name.equals("shouldApplyMixin") && m.desc.equals("(Ljava/lang/String;Ljava/lang/String;)Z"))
                .findFirst().orElseThrow();
        StringBuilder head = new StringBuilder();
        AbstractInsnNode insn = sam.instructions.getFirst();
        for (int n = 0; n < 6 && insn != null; insn = insn.getNext()) {
            if (insn.getOpcode() < 0) continue; // labels/frames/lines
            n++;
            head.append(insn.getOpcode()).append(insn instanceof LdcInsnNode l ? "(" + l.cst + ")" : "").append(" ");
        }
        System.out.println("Fix6 head: " + head);
        boolean ok = head.toString().startsWith(
                "25 18(foundry.veil.mixin.performance.client.PerformanceRenderTargetMixin) 182 153 3 172");
        System.out.println("Fix6: " + (ok ? "PASS (ALOAD2 LDC INVOKEVIRTUAL IFEQ ICONST_0 IRETURN)" : "FAIL"));
        verify(veil);

        // --- Fix 7: UniformKt dedupe injection ---
        ClassNode uni = apply("uvfixes_supplemental_uniform_dedupe",
                "C:/Windows/Temp/sp_inspect/io/github/jedlimlx/supplemental_patches/shaders/UniformKt.class");
        MethodNode gu = uni.methods.stream()
                .filter(m -> m.name.equals("generateUniforms")).findFirst().orElseThrow();
        boolean hasReadString = false, hasContains = false, hasGetName = false;
        for (AbstractInsnNode gin : gu.instructions)
            if (gin instanceof MethodInsnNode mi) {
                if (mi.name.equals("readString") && mi.owner.equals("java/nio/file/Files")) hasReadString = true;
                if (mi.name.equals("contains") && mi.owner.equals("java/lang/String")) hasContains = true;
                if (mi.name.equals("getName") && mi.owner.endsWith("Uniform")) hasGetName = true;
            }
        System.out.println("Fix7: readString=" + hasReadString + " contains=" + hasContains + " getName=" + hasGetName
                + " tcbs=" + gu.tryCatchBlocks.size()
                + ((hasReadString && hasContains && hasGetName) ? "  PASS" : "  FAIL"));
        verify(uni);

        // --- Fix 8: ErrorHandlingKt catch-all ---
        ClassNode eh = apply("uvfixes_supplemental_errorhandling_catchall",
                "C:/Windows/Temp/sp_inspect/io/github/jedlimlx/supplemental_patches/shaders/ErrorHandlingKt.class");
        MethodNode weh = eh.methods.stream()
                .filter(m -> m.name.equals("withErrorHandling")).findFirst().orElseThrow();
        boolean fix8ok = weh.tryCatchBlocks.size() == 2
                && "java/lang/Throwable".equals(weh.tryCatchBlocks.get(1).type)
                && weh.tryCatchBlocks.get(0).type.endsWith("MinecraftError");
        System.out.println("Fix8: tcbs=" + weh.tryCatchBlocks.size() + " second="
                + weh.tryCatchBlocks.get(weh.tryCatchBlocks.size() - 1).type + (fix8ok ? "  PASS" : "  FAIL"));
        verify(eh);

        // --- Fix 9: ClientEvents stitch event guard ---
        ClassNode ce = apply("uvfixes_supplemental_stitch_event_guard",
                "C:/Windows/Temp/sp_inspect/io/github/jedlimlx/supplemental_patches/events/ClientEvents.class");
        MethodNode tse = ce.methods.stream()
                .filter(m -> m.name.equals("textureStitchedEvent")).findFirst().orElseThrow();
        boolean fix9ok = tse.tryCatchBlocks.size() == 1 && "java/lang/Throwable".equals(tse.tryCatchBlocks.get(0).type);
        System.out.println("Fix9: tcbs=" + tse.tryCatchBlocks.size() + (fix9ok ? "  PASS" : "  FAIL"));
        verify(ce);

        // --- Fix 10: moonlight SimpleMixinPlugin guard ---
        ClassNode ml = apply("uvfixes_supplementaries_sodium_fluid_mixin_disable",
                "C:/Windows/Temp/supp_inspect/net/mehvahdjukaar/moonlight/api/misc/SimpleMixinPlugin.class");
        MethodNode sam10 = ml.methods.stream()
                .filter(m -> m.name.equals("shouldApplyMixin") && m.desc.equals("(Ljava/lang/String;Ljava/lang/String;)Z"))
                .findFirst().orElseThrow();
        StringBuilder head10 = new StringBuilder();
        AbstractInsnNode in10 = sam10.instructions.getFirst();
        for (int n = 0; n < 6 && in10 != null; in10 = in10.getNext()) {
            if (in10.getOpcode() < 0) continue;
            n++;
            head10.append(in10.getOpcode()).append(in10 instanceof LdcInsnNode l ? "(" + l.cst + ")" : "").append(" ");
        }
        boolean fix10ok = head10.toString().startsWith(
                "25 18(net.mehvahdjukaar.supplementaries.mixins.neoforge.compat.CompatSodiumFluidRendererMixin) 182 153 3 172");
        System.out.println("Fix10 head: " + head10);
        System.out.println("Fix10: " + (fix10ok ? "PASS" : "FAIL"));
        verify(ml);

        // --- Fix 11: expanded_combat tab guard ---
        ClassNode ec = apply("uvfixes_expandedcombat_tab_guard",
                "C:/Windows/Temp/ec_inspect/com/userofbricks/expanded_combat/init/ECCreativeTabs.class");
        MethodNode mv = ec.methods.stream()
                .filter(m -> m.name.equals("ModifyVanillaCreativeTabs")).findFirst().orElseThrow();
        boolean fix11ok = mv.tryCatchBlocks.size() == 1 && "java/lang/Throwable".equals(mv.tryCatchBlocks.get(0).type);
        System.out.println("Fix11: tcbs=" + mv.tryCatchBlocks.size() + (fix11ok ? "  PASS" : "  FAIL"));
        verify(ec);

        // --- Fix 12: tombstone getAmplifier guard ---
        ClassNode ts = apply("uvfixes_tombstone_scroll_config_guard",
                "C:/Windows/Temp/uvfixes/ts_inspect/ovh/corail/tombstone/item/ItemMagicScroll.class");
        MethodNode ga = ts.methods.stream()
                .filter(m -> m.name.equals("getAmplifier") && m.desc.equals("(Lnet/minecraft/world/item/ItemStack;)I"))
                .findFirst().orElseThrow();
        boolean fix12ok = ga.tryCatchBlocks.size() == 1 && "java/lang/Throwable".equals(ga.tryCatchBlocks.get(0).type)
                && tailOps(ga, 3).equals("87 3 172"); // POP ICONST_0 IRETURN
        System.out.println("Fix12: tcbs=" + ga.tryCatchBlocks.size() + " tail=" + tailOps(ga, 3) + (fix12ok ? "  PASS" : "  FAIL"));
        verify(ts);

        // --- Fix 13: ItemStack.getHoverName guard ---
        ClassNode is = apply("uvfixes_itemstack_hovername_guard",
                "C:/Windows/Temp/uvfixes/mc_inspect/net/minecraft/world/item/ItemStack.class");
        MethodNode ghn = is.methods.stream()
                .filter(m -> m.name.equals("getHoverName") && m.desc.equals("()Lnet/minecraft/network/chat/Component;"))
                .findFirst().orElseThrow();
        MethodInsnNode emptyCall = null;
        for (AbstractInsnNode in2 = ghn.instructions.getLast(); in2 != null; in2 = in2.getPrevious())
            if (in2 instanceof MethodInsnNode mi && mi.name.equals("empty")) { emptyCall = mi; break; }
        boolean fix13ok = ghn.tryCatchBlocks.size() == 1 && "java/lang/Throwable".equals(ghn.tryCatchBlocks.get(0).type)
                && tailOps(ghn, 3).equals("87 184 176") // POP INVOKESTATIC ARETURN
                && emptyCall != null && emptyCall.itf && emptyCall.owner.equals("net/minecraft/network/chat/Component");
        System.out.println("Fix13: tcbs=" + ghn.tryCatchBlocks.size() + " tail=" + tailOps(ghn, 3)
                + " emptyItf=" + (emptyCall != null && emptyCall.itf) + (fix13ok ? "  PASS" : "  FAIL"));
        verify(is);

        // --- Fix 14: biolith registry re-seed ---
        ClassNode bc = apply("uvfixes_biolith_registry_reseed",
                "C:/Windows/Temp/uvfixes/bio_inspect/com/terraformersmc/biolith/impl/biome/BiomeCoordinator.class");
        MethodNode hws = bc.methods.stream()
                .filter(m -> m.name.equals("handleWorldStarting")).findFirst().orElseThrow();
        StringBuilder h14 = new StringBuilder();
        int n14 = 0;
        for (AbstractInsnNode in3 = hws.instructions.getFirst(); in3 != null && n14 < 8; in3 = in3.getNext())
            if (in3.getOpcode() >= 0) { h14.append(h14.isEmpty() ? "" : " ").append(in3.getOpcode()); n14++; }
        boolean fix14ok = h14.toString().equals("178 199 25 182 192 179 4 179");
        System.out.println("Fix14 head: " + h14 + (fix14ok ? "  PASS" : "  FAIL"));
        verify(bc);

        // --- Fix 15: journeymap join guard ---
        ClassNode jm = apply("uvfixes_journeymap_join_guard",
                "C:/Windows/Temp/uvfixes/jm_inspect/journeymap/common/event/NeoForgeServerEvents.class");
        MethodNode jw = jm.methods.stream()
                .filter(m -> m.name.equals("onEntityJoinWorldEvent")).findFirst().orElseThrow();
        boolean fix15ok = jw.tryCatchBlocks.size() == 1 && "java/lang/Throwable".equals(jw.tryCatchBlocks.get(0).type)
                && tailOps(jw, 2).equals("182 177"); // printStackTrace RETURN
        System.out.println("Fix15: tcbs=" + jw.tryCatchBlocks.size() + " tail=" + tailOps(jw, 2) + (fix15ok ? "  PASS" : "  FAIL"));
        verify(jm);

        // --- Fix 16: supplemental MaterialGeneratorKt constant dedup ---
        ClassNode mg = apply("uvfixes_supplemental_material_dedup",
                "C:/Windows/Temp/uvfixes/sp2/io/github/jedlimlx/supplemental_patches/shaders/MaterialGeneratorKt.class");
        int oldC = 0, newC = 0;
        for (MethodNode m : mg.methods)
            for (AbstractInsnNode in16 : m.instructions)
                if (in16 instanceof LdcInsnNode ldc16 && ldc16.cst instanceof String s16) {
                    if (s16.contains("bool noGeneratedNormals;")) oldC++;
                    if (s16.contains("vec3 maRecolor;\n    bool noVanillaAO;")) newC++;
                }
        boolean fix16ok = oldC == 0 && newC == 1;
        System.out.println("Fix16: old-decl remaining=" + oldC + " new-constant=" + newC + (fix16ok ? "  PASS" : "  FAIL"));
        verify(mg);

        // --- Fix 17: caverns_and_chasms JEI filter guards ---
        ClassNode cc = apply("uvfixes_cavernschasms_jei_guard",
                "C:/Windows/Temp/uvfixes/cc_inspect/com/teamabnormals/caverns_and_chasms/integration/jei/CCPlugin.class");
        int guarded17 = 0;
        for (MethodNode m : cc.methods)
            if ((m.name.equals("lambda$getRepairData$0") || m.name.equals("lambda$getRepairData$3"))
                    && m.tryCatchBlocks.size() == 1 && "java/lang/Throwable".equals(m.tryCatchBlocks.get(0).type)
                    && tailOps(m, 3).equals("87 3 172")) guarded17++;
        System.out.println("Fix17: guarded lambdas=" + guarded17 + (guarded17 == 2 ? "  PASS" : "  FAIL"));
        verify(cc);

        // --- Fix 18: uncrafteverything JEI recipe scan parallelized ---
        ClassNode ue = apply("uvfixes_uncrafteverything_jei_parallel",
                "C:/Windows/Temp/uvfixes/ue_inspect/com/coolerpromc/uncrafteverything/util/RecipeViewerHelpers.class");
        boolean syncList18 = false, parStream18 = false;
        int collForEach18 = 0, streamForEach18 = 0;
        for (MethodNode m : ue.methods) {
            if (!m.name.equals("getRecipes")) continue;
            for (AbstractInsnNode in18 : m.instructions) {
                if (in18 instanceof MethodInsnNode mi) {
                    if (mi.owner.equals("java/util/Collections") && mi.name.equals("synchronizedList")
                            && mi.getNext() instanceof VarInsnNode st && st.getOpcode() == 58 /*ASTORE*/ && st.var == 2)
                        syncList18 = true;
                    if (mi.owner.equals("java/util/Collection") && mi.name.equals("parallelStream")
                            && mi.getPrevious() instanceof MethodInsnNode prev && prev.name.equals("getRecipes"))
                        parStream18 = true;
                    if (mi.owner.equals("java/util/Collection") && mi.name.equals("forEach")) collForEach18++;
                    if (mi.owner.equals("java/util/stream/Stream") && mi.name.equals("forEach")) streamForEach18++;
                }
            }
        }
        boolean fix18ok = syncList18 && parStream18 && collForEach18 == 0 && streamForEach18 == 4;
        System.out.println("Fix18: syncList=" + syncList18 + " parallelStream=" + parStream18
                + " collForEach=" + collForEach18 + " streamForEach=" + streamForEach18
                + (fix18ok ? "  PASS" : "  FAIL"));
        verify(ue);

        // --- Fix 19: townstead CEM probe memoization ---
        ClassNode ts19 = apply("uvfixes_townstead_cem_probe_cache",
                "C:/Windows/Temp/uvfixes/ts_inspect/com/aetherianartificer/townstead/client/animation/EmfAnimationSourceAdapter.class");
        boolean field19 = ts19.fields.stream().anyMatch(f -> f.name.equals("uvfixes$cemCache"));
        int puts19 = 0, dupPuts19 = 0;
        boolean head19 = false, inv19 = false;
        for (MethodNode m : ts19.methods) {
            for (AbstractInsnNode in19 : m.instructions) {
                if (in19 instanceof FieldInsnNode fi && fi.name.equals("uvfixes$cemCache") && fi.getOpcode() == 179 /*PUTSTATIC*/) {
                    puts19++;
                    if (m.name.equals("resolvePlayerCem") && fi.getPrevious() != null && fi.getPrevious().getOpcode() == 89 /*DUP*/) dupPuts19++;
                    if (m.name.equals("invalidate")) inv19 = true;
                }
            }
            if (m.name.equals("resolvePlayerCem")) {
                AbstractInsnNode first = m.instructions.getFirst();
                while (first != null && first.getOpcode() < 0) first = first.getNext();
                head19 = first instanceof FieldInsnNode hf && hf.getOpcode() == 178 /*GETSTATIC*/ && hf.name.equals("uvfixes$cemCache");
            }
        }
        boolean fix19ok = field19 && head19 && puts19 == 3 && dupPuts19 == 2 && inv19;
        System.out.println("Fix19: field=" + field19 + " head=" + head19 + " puts=" + puts19
                + " dupPuts=" + dupPuts19 + " invalidateHook=" + inv19 + (fix19ok ? "  PASS" : "  FAIL"));
        verify(ts19);

        // --- Fix 20: smithingtemplateviewer armor-stand guard ---
        ClassNode stv = apply("uvfixes_smithingtemplateviewer_empty_ingredient_guard",
                "C:/Windows/Temp/uvfixes/stv_inspect/com/buuz135/smithingtemplateviewer/SmithingTrimWrapper.class");
        boolean fix20ok = false;
        for (MethodNode m : stv.methods)
            if (m.name.equals("updateArmorStand") && m.tryCatchBlocks.size() == 1
                    && "java/lang/Throwable".equals(m.tryCatchBlocks.get(0).type)
                    && tailOps(m, 2).equals("87 177")) fix20ok = true;
        System.out.println("Fix20: guard=" + fix20ok + (fix20ok ? "  PASS" : "  FAIL"));
        verify(stv);

        // --- Fix 21: spawn variant managers Level.random -> RandomSource.create() ---
        String spawnCls = "C:/Users/linde/curseforge/minecraft/Instances/Ultimate vibes distant horizons version/.uvrun/analysis/spawnfix/cls/com/ninni/spawn/server/data/";
        ClassNode avm = apply("uvfixes_spawn_animal_variant_random", spawnCls + "AnimalVariantManager.class");
        ClassNode bvm = apply("uvfixes_spawn_block_variant_random", spawnCls + "BlockVariantManager.class");
        for (ClassNode cn : new ClassNode[]{avm, bvm}) {
            String want = cn == avm ? "chooseWeightedVariant" : "choose";
            int levelRandomLeft = 0, createCalls = 0; boolean popBefore = false;
            for (MethodNode m : cn.methods) {
                if (!m.name.equals(want)) continue;
                for (AbstractInsnNode in = m.instructions.getFirst(); in != null; in = in.getNext()) {
                    if (in instanceof FieldInsnNode f && f.owner.equals("net/minecraft/world/level/Level")
                            && f.name.equals("random")) levelRandomLeft++;
                    if (in instanceof MethodInsnNode mi && mi.getOpcode() == 184 /*INVOKESTATIC*/
                            && mi.owner.equals("net/minecraft/util/RandomSource") && mi.name.equals("create")) {
                        createCalls++;
                        AbstractInsnNode prev = in.getPrevious();
                        while (prev != null && prev.getOpcode() < 0) prev = prev.getPrevious();
                        if (prev != null && prev.getOpcode() == 87 /*POP*/) popBefore = true;
                    }
                }
            }
            boolean ok21 = levelRandomLeft == 0 && createCalls == 1 && popBefore;
            System.out.println("Fix21 " + cn.name + ": Level.random left=" + levelRandomLeft
                    + " create=" + createCalls + " popBefore=" + popBefore + (ok21 ? "  PASS" : "  FAIL"));
            verify(cn);
        }

        // --- Fix 22: neoforge tab-anchor assert no-op ---
        ClassNode tabev = apply("uvfixes_neoforge_tab_anchor_fallback",
                "C:/Users/linde/curseforge/minecraft/Instances/Ultimate vibes distant horizons version/.uvrun/analysis/nf-event/net/neoforged/neoforge/event/BuildCreativeModeTabContentsEvent.class");
        boolean fix22ok = false;
        for (MethodNode m : tabev.methods)
            if (m.name.equals("assertTargetExists")) {
                int real = 0;
                for (AbstractInsnNode in = m.instructions.getFirst(); in != null; in = in.getNext())
                    if (in.getOpcode() >= 0) real++;
                fix22ok = real == 1 && tailOps(m, 1).equals("177");
            }
        System.out.println("Fix22: assertTargetExists is bare RETURN=" + fix22ok + (fix22ok ? "  PASS" : "  FAIL"));
        verify(tabev);

        // --- Fix 23: fieldguide SearchManager entry cache ---
        String anal = "C:/Users/linde/curseforge/minecraft/Instances/Ultimate vibes distant horizons version/.uvrun/analysis/";
        ClassNode sm = apply("uvfixes_fieldguide_entry_cache",
                anal + "fieldguide/extracted/com/evandev/fieldguide/client/search/SearchManager.class");
        boolean fieldOk = sm.fields.stream().anyMatch(f -> f.name.equals("uv$entryCache"));
        int containsK = 0, getK = 0, putK = 0, heads = 0;
        for (MethodNode m : sm.methods) {
            if (m.name.equals("matchByBiome"))
                for (AbstractInsnNode in = m.instructions.getFirst(); in != null; in = in.getNext())
                    if (in instanceof MethodInsnNode mi && mi.owner.equals("java/util/HashMap")) {
                        if (mi.name.equals("containsKey")) containsK++;
                        if (mi.name.equals("get")) getK++;
                        if (mi.name.equals("put")) putK++;
                    }
            if (m.name.equals("groupByQueries") || (m.name.equals("searchEntries") && m.desc.startsWith("(Ljava/lang/String;"))) {
                AbstractInsnNode first = m.instructions.getFirst();
                while (first != null && first.getOpcode() < 0) first = first.getNext();
                if (first instanceof FieldInsnNode fi && fi.name.equals("uv$entryCache")) heads++;
            }
        }
        boolean fix23ok = fieldOk && containsK == 1 && getK == 1 && putK == 1 && heads == 2;
        System.out.println("Fix23: field=" + fieldOk + " containsKey=" + containsK + " get=" + getK
                + " put=" + putK + " resetHeads=" + heads + (fix23ok ? "  PASS" : "  FAIL"));
        verify(sm);

        // --- Fix 24: softimprints capture gate ---
        ClassNode fpc = apply("uvfixes_softimprints_skip_wasted_capture_render",
                anal + "softimprints/extracted/com/nine/softimprints/core/contact/model/render/FirstPersonContactCapturer.class");
        boolean fix24ok = false;
        for (MethodNode m : fpc.methods)
            if (m.name.equals("captureIfApplicable")) {
                int gates = 0;
                boolean ifeqBeforeBegin = false;
                for (AbstractInsnNode in = m.instructions.getFirst(); in != null; in = in.getNext()) {
                    if (in instanceof MethodInsnNode mi && mi.name.equals("tryBeginLivingCapture")) {
                        gates++;
                        AbstractInsnNode nx = in.getNext();
                        while (nx != null && nx.getOpcode() < 0) nx = nx.getNext();
                        ifeqBeforeBegin = nx != null && nx.getOpcode() == 153 /*IFEQ*/;
                    }
                }
                fix24ok = gates == 1 && ifeqBeforeBegin && tailOps(m, 2).equals("177 177");
            }
        System.out.println("Fix24: gate=" + fix24ok + (fix24ok ? "  PASS" : "  FAIL"));
        verify(fpc);
    }

    // last n real opcodes of a method, space-joined
    static String tailOps(MethodNode m, int n) {
        java.util.ArrayDeque<Integer> ops = new java.util.ArrayDeque<>();
        for (AbstractInsnNode in = m.instructions.getLast(); in != null && ops.size() < n; in = in.getPrevious())
            if (in.getOpcode() >= 0) ops.addFirst(in.getOpcode());
        StringBuilder sb = new StringBuilder();
        for (int op : ops) sb.append(sb.isEmpty() ? "" : " ").append(op);
        return sb.toString();
    }

    static ClassNode apply(String key, String classFile) throws Exception {
        ClassNode node = new ClassNode();
        new ClassReader(Files.readAllBytes(Path.of(classFile))).accept(node, 0);
        ScriptObjectMirror entry = (ScriptObjectMirror) transformers.get(key);
        ScriptObjectMirror fn = (ScriptObjectMirror) entry.get("transformer");
        return (ClassNode) fn.call(entry, node);
    }

    // structural bytecode verification (frames recomputed like ModLauncher does)
    static void verify(ClassNode node) {
        ClassWriter cw = new ClassWriter(ClassWriter.COMPUTE_FRAMES) {
            protected String getCommonSuperClass(String a, String b) {
                try { return super.getCommonSuperClass(a, b); }
                catch (Throwable t) { return "java/lang/Object"; }
            }
        };
        node.accept(cw);
        var sw = new java.io.StringWriter();
        CheckClassAdapter.verify(new ClassReader(cw.toByteArray()), false, new java.io.PrintWriter(sw));
        System.out.println("verify " + node.name + ": " + (sw.toString().isEmpty() ? "CLEAN" : "PROBLEMS:\n" + sw));
    }
}
