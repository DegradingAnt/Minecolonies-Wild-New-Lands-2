// Ultimate Vibes Pack Fixes - JS coremod
// Applied at class-load time; original mod jars stay untouched.
// Each fix logs "[uvfixes] ..." and no-ops with a log line if a mod update
// changed the target (then check whether upstream fixed the bug).

var ASMAPI = Java.type('net.neoforged.coremod.api.ASMAPI');
var Opcodes = Java.type('org.objectweb.asm.Opcodes');
var InsnNode = Java.type('org.objectweb.asm.tree.InsnNode');
var VarInsnNode = Java.type('org.objectweb.asm.tree.VarInsnNode');
var JumpInsnNode = Java.type('org.objectweb.asm.tree.JumpInsnNode');
var LabelNode = Java.type('org.objectweb.asm.tree.LabelNode');
var InsnList = Java.type('org.objectweb.asm.tree.InsnList');
var TryCatchBlockNode = Java.type('org.objectweb.asm.tree.TryCatchBlockNode');
var MethodInsnNode = Java.type('org.objectweb.asm.tree.MethodInsnNode');
var FieldInsnNode = Java.type('org.objectweb.asm.tree.FieldInsnNode');
var TypeInsnNode = Java.type('org.objectweb.asm.tree.TypeInsnNode');
var LdcInsnNode = Java.type('org.objectweb.asm.tree.LdcInsnNode');
var AsmType = Java.type('org.objectweb.asm.Type');

function log(msg) {
    ASMAPI.log('INFO', '[uvfixes] ' + msg);
}

var OLD_SOUNDS = 'net/skill_tree_rpgs/skills/SkillTreeSounds';
var NEW_SOUNDS = 'net/skill_tree_rpgs/skills/SkillSounds';
var OLD_SPELLS = 'net/skill_tree_rpgs/skills/Spells';
var NEW_SPELLS = 'net/skill_tree_rpgs/skills/SkillsCommon';

function remapName(name) {
    if (name.equals(OLD_SOUNDS)) return NEW_SOUNDS;
    if (name.equals(OLD_SPELLS)) return NEW_SPELLS;
    return name;
}

function remapDesc(desc) {
    return desc.replace('L' + OLD_SOUNDS + ';', 'L' + NEW_SOUNDS + ';')
               .replace('L' + OLD_SPELLS + ';', 'L' + NEW_SPELLS + ';');
}

// Fix 3: MRPGC Skill Tree 1.1.2 was compiled against a Skill Tree (RPG Series)
// version where SkillSounds was named SkillTreeSounds and SkillsCommon was
// named Spells. All referenced members verified identical on 1.4.4.
function remapMrpgcClass(classNode) {
    var changed = 0;
    for (var i = 0; i < classNode.methods.size(); i++) {
        var m = classNode.methods.get(i);
        var insns = m.instructions.toArray();
        for (var j = 0; j < insns.length; j++) {
            var insn = insns[j];
            if (insn instanceof FieldInsnNode) {
                var no = remapName(insn.owner); var nd = remapDesc(insn.desc);
                if (!no.equals(insn.owner) || !nd.equals(insn.desc)) { insn.owner = no; insn.desc = nd; changed++; }
            } else if (insn instanceof MethodInsnNode) {
                var no2 = remapName(insn.owner); var nd2 = remapDesc(insn.desc);
                if (!no2.equals(insn.owner) || !nd2.equals(insn.desc)) { insn.owner = no2; insn.desc = nd2; changed++; }
            } else if (insn instanceof TypeInsnNode) {
                var nt = remapName(insn.desc);
                if (!nt.equals(insn.desc)) { insn.desc = nt; changed++; }
            } else if (insn instanceof LdcInsnNode && insn.cst instanceof AsmType) {
                var d = insn.cst.getDescriptor(); var d2 = remapDesc(d);
                if (!d2.equals(d)) { insn.cst = AsmType.getType(d2); changed++; }
            }
        }
    }
    log(changed > 0 ? 'mrpgc remap applied to ' + classNode.name + ' (' + changed + ' refs)' : 'mrpgc remap: 0 refs in ' + classNode.name + ' (Skill Tree RPG updated? mod updated?)');
    return classNode;
}

// Fix 27: createaeronauticscurios 2.0 (aeronautics_curios_compat) ships its three
// LinkedTypewriter mixins rewritten for a NEWER Create Aeronautics / `simulated`
// than the bundled one (aeronautics 1.3.0). Their MixinExtras @Local(name="player")
// sugars + @At injection points don't resolve against simulated 1.3.0's
// LinkedTypewriterBlockEntity.checkAndStartUsing -> "Critical injection failure,
// Scanned 0 target(s)" -> Mod Construction aborts -> wakes WakeHandler.<clinit>
// "Cannot get config value before config is loaded" cascade -> tick-1 crash.
// (Same cascade shape the old libjf NPE used to trigger.)
// Patch: strip every INJECTOR handler method (@Inject/@ModifyArg/@Redirect/
// MixinExtras @ModifyExpressionValue/@WrapWithCondition/etc.) from the 3 mixin
// classes, leaving @Shadow/@Unique fields and the interface-impl methods intact.
// The mixins still add their interface + fields (no @Shadow / ClassCast breakage,
// goggles-curio core untouched); only the already-broken remote-typewriter
// behaviour is disabled. No jar edit. No-ops harmlessly once the mod is updated
// to match the installed Create Aeronautics (methods will simply be absent).
var INJECTOR_DESC = [
    'Lorg/spongepowered/asm/mixin/injection/Inject;',
    'Lorg/spongepowered/asm/mixin/injection/ModifyArg;',
    'Lorg/spongepowered/asm/mixin/injection/ModifyArgs;',
    'Lorg/spongepowered/asm/mixin/injection/ModifyConstant;',
    'Lorg/spongepowered/asm/mixin/injection/ModifyVariable;',
    'Lorg/spongepowered/asm/mixin/injection/Redirect;'
];
function uvIsInjectorMethod(m) {
    var anns = m.visibleAnnotations;
    if (anns == null) return false;
    for (var k = 0; k < anns.size(); k++) {
        var d = anns.get(k).desc;
        if (d.startsWith('Lcom/llamalad7/mixinextras/injector/')) return true;
        for (var x = 0; x < INJECTOR_DESC.length; x++) {
            if (d.equals(INJECTOR_DESC[x])) return true;
        }
    }
    return false;
}
function uvStripInjectors(classNode, label) {
    var removed = 0;
    var methods = classNode.methods;
    for (var i = methods.size() - 1; i >= 0; i--) {
        if (uvIsInjectorMethod(methods.get(i))) { methods.remove(i); removed++; }
    }
    log(label + ': stripped ' + removed + ' broken injector(s) (createaeronauticscurios 2.0 vs simulated 1.3.0)');
    return classNode;
}

function initializeCoreMod() {
    return {
        // Fix 30: Domum Ornamentum architect's-cutter item ICONS render blank/wrong when DO's
        // MateriallyTexturedBakedModel is wrapped by a Fabric ForwardingBakedModel that reports
        // isVanillaAdapter()=false (Continuity emissive/CTM EmissiveBakedModel/CtmBakedModel,
        // SnowRealMagic, etc.). That flips the item onto FFAPI's Indigo emitItemQuads render path,
        // which renders via getQuads(null) and NEVER calls DO's getRenderPasses(stack) where the
        // per-item material lives -> blank. DO is a pure NeoForge BakedModel and never implemented
        // the Fabric emitItemQuads (it inherits the FabricBakedModel default, which is the broken
        // one). FIX: add emitItemQuads that emits DO's per-item getRenderPasses sub-models through
        // the RenderContext consumer (BakedModelConsumer extends Consumer<BakedModel>, so a simple
        // List.forEach(consumer) does it -> linear bytecode, no frames). DO then renders correctly
        // on the Indigo/Fabric path too, so it works EVEN WHEN WRAPPED -> Continuity emissive/CTM,
        // SnowRealMagic, MoreCulling all stay fully ON, nothing disabled, Indigo speed kept.
        'uvfixes_domum_emititemquads': {
            'target': { 'type': 'CLASS', 'name': 'com.ldtteam.domumornamentum.client.model.baked.MateriallyTexturedBakedModel' },
            'transformer': function (classNode) {
                var MethodNode = Java.type('org.objectweb.asm.tree.MethodNode');
                var OWNER = 'com/ldtteam/domumornamentum/client/model/baked/MateriallyTexturedBakedModel';
                var DESC = '(Lnet/minecraft/world/item/ItemStack;Ljava/util/function/Supplier;Lnet/fabricmc/fabric/api/renderer/v1/render/RenderContext;)V';
                for (var i = 0; i < classNode.methods.size(); i++) {
                    var mm = classNode.methods.get(i);
                    if (mm.name.equals('emitItemQuads') && mm.desc.equals(DESC)) {
                        log('domum emitItemQuads already present -> skip (DO updated, upstream may have fixed it)');
                        return classNode;
                    }
                }
                // Guard: only emit the INVOKEVIRTUAL to getRenderPasses(ItemStack,Z) if DO still declares it.
                // Without this, a DO API change would defer to a NoSuchMethodError at item-render time with a
                // success-looking boot log. With it, a DO update surfaces as a clear skip line in the boot log.
                var hasGRP = false;
                for (var k = 0; k < classNode.methods.size(); k++) {
                    var gm = classNode.methods.get(k);
                    if (gm.name.equals('getRenderPasses') && gm.desc.equals('(Lnet/minecraft/world/item/ItemStack;Z)Ljava/util/List;')) { hasGRP = true; break; }
                }
                if (!hasGRP) {
                    log('domum emitItemQuads: getRenderPasses(ItemStack,Z) NOT found -> skip (would crash at item-render; DO updated? mod updated?)');
                    return classNode;
                }
                var mn = new MethodNode(Opcodes.ACC_PUBLIC, 'emitItemQuads', DESC, null, null);
                var l = mn.instructions;
                var loop = new LabelNode();
                var end = new LabelNode();
                // Iterator it = this.getRenderPasses(stack, false).iterator();   [local 4]
                l.add(new VarInsnNode(Opcodes.ALOAD, 0));
                l.add(new VarInsnNode(Opcodes.ALOAD, 1));
                l.add(new InsnNode(Opcodes.ICONST_0));
                l.add(new MethodInsnNode(Opcodes.INVOKEVIRTUAL, OWNER, 'getRenderPasses', '(Lnet/minecraft/world/item/ItemStack;Z)Ljava/util/List;', false));
                l.add(new MethodInsnNode(Opcodes.INVOKEINTERFACE, 'java/util/List', 'iterator', '()Ljava/util/Iterator;', true));
                l.add(new VarInsnNode(Opcodes.ASTORE, 4));
                // while (it.hasNext())  VanillaModelEncoder.emitItemQuads((BakedModel)it.next(), null, rand, context);
                l.add(loop);
                l.add(new VarInsnNode(Opcodes.ALOAD, 4));
                l.add(new MethodInsnNode(Opcodes.INVOKEINTERFACE, 'java/util/Iterator', 'hasNext', '()Z', true));
                l.add(new JumpInsnNode(Opcodes.IFEQ, end));
                l.add(new VarInsnNode(Opcodes.ALOAD, 4));
                l.add(new MethodInsnNode(Opcodes.INVOKEINTERFACE, 'java/util/Iterator', 'next', '()Ljava/lang/Object;', true));
                l.add(new TypeInsnNode(Opcodes.CHECKCAST, 'net/minecraft/client/resources/model/BakedModel'));
                l.add(new InsnNode(Opcodes.ACONST_NULL));
                l.add(new VarInsnNode(Opcodes.ALOAD, 2));
                l.add(new VarInsnNode(Opcodes.ALOAD, 3));
                l.add(new MethodInsnNode(Opcodes.INVOKESTATIC, 'net/fabricmc/fabric/impl/renderer/VanillaModelEncoder', 'emitItemQuads', '(Lnet/minecraft/client/resources/model/BakedModel;Lnet/minecraft/world/level/block/state/BlockState;Ljava/util/function/Supplier;Lnet/fabricmc/fabric/api/renderer/v1/render/RenderContext;)V', false));
                l.add(new JumpInsnNode(Opcodes.GOTO, loop));
                l.add(end);
                l.add(new InsnNode(Opcodes.RETURN));
                mn.maxStack = 4;
                mn.maxLocals = 5;
                classNode.methods.add(mn);
                log('domum MateriallyTexturedBakedModel.emitItemQuads ADDED (Indigo-path fallback; no-op under Sodium where items use getQuads)');
                return classNode;
            }
        },
        // Fix 32: DO x Farsight x Flywheel chunk-swap RENDER-THREAD LIVELOCK (confirmed via live
        // thread dump). On a Farsight chunk swap, LevelChunk.clearAllBlockEntities iterates the
        // chunk's block-entity ConcurrentHashMap calling BlockEntity.setRemoved on each. NeoForge's
        // setRemoved sets remove=true THEN calls requestModelDataUpdate(). DO's
        // MateriallyTexturedBlockEntity.requestModelDataUpdate calls level.setBlocksDirty(...),
        // which fires Flywheel's checkUpdate mixin -> Level.getBlockEntity in CREATE mode ->
        // re-creates the DO block-entity (PanelBlock.newBlockEntity) and re-ADDS it to the very map
        // being iterated -> infinite loop -> render thread frozen. FIX: guard
        // requestModelDataUpdate with an early-return when this.isRemoved()==true. setRemoved sets
        // remove=true BEFORE invoking requestModelDataUpdate (verified in NeoForge 21.1.233
        // setRemoved disasm: putfield remove=true at offset 2, invokevirtual requestModelDataUpdate
        // at offset 10), so isRemoved() is reliably true on the teardown path -> setBlocksDirty (and
        // the super call) are skipped -> the Flywheel re-add can't happen -> loop broken. On a normal
        // model refresh (live BE) isRemoved() is false -> behaviour 100% unchanged. isRemoved()Z is
        // inherited from the NeoForge-patched MC BlockEntity (DO -> AbstractMateriallyTexturedBlockEntity
        // -> net.minecraft.world.level.block.entity.BlockEntity); INVOKEVIRTUAL on the DO class
        // virtual-dispatches to it. Insert-guard-at-HEAD idiom, same shape as Fix 31. No-ops with a
        // log line if DO drops/renames the override (mod updated -> check if upstream fixed it).
        'uvfixes_domum_skip_modeldata_when_removed': {
            'target': { 'type': 'CLASS', 'name': 'com.ldtteam.domumornamentum.entity.block.MateriallyTexturedBlockEntity' },
            'transformer': function (classNode) {
                var OWNER = 'com/ldtteam/domumornamentum/entity/block/MateriallyTexturedBlockEntity';
                var done = false;
                for (var i = 0; i < classNode.methods.size(); i++) {
                    var m = classNode.methods.get(i);
                    if (m.name.equals('requestModelDataUpdate') && m.desc.equals('()V')) {
                        var list = new InsnList();
                        var cont = new LabelNode();
                        // if (this.isRemoved()) return;
                        list.add(new VarInsnNode(Opcodes.ALOAD, 0));
                        list.add(new MethodInsnNode(Opcodes.INVOKEVIRTUAL, OWNER, 'isRemoved', '()Z', false));
                        list.add(new JumpInsnNode(Opcodes.IFEQ, cont));
                        list.add(new InsnNode(Opcodes.RETURN));
                        list.add(cont);
                        m.instructions.insert(list);
                        done = true;
                        break;
                    }
                }
                log(done ? 'domum MateriallyTexturedBlockEntity.requestModelDataUpdate isRemoved-guard added (breaks DOxFarsightxFlywheel clearAllBlockEntities livelock; live-BE refresh unchanged)' : 'domum: requestModelDataUpdate()V not found, patch skipped (mod updated?)');
                return classNode;
            }
        },
        // Fix 31: THE core DO icon fix. Continuity's ModelWrappingHandler.wrap() wraps DO's
        // MateriallyTexturedBakedModel in an EmissiveBakedModel/CtmBakedModel (Fabric
        // ForwardingBakedModel, isVanillaAdapter=false). Under Sodium that flips DO's item onto a
        // stack-blind render path (getQuads(null)) where DO's per-item material -- which only lives
        // in getRenderPasses(ItemStack)/emitItemQuads(ItemStack) -- is unreachable -> blank icon.
        // (Fix 30's emitItemQuads can't help: Sodium never calls it for items.) Real fix: never let
        // Continuity wrap a DO model. Guard wrap(): if the incoming model is a MateriallyTexturedBakedModel,
        // return it unwrapped. DO then stays on its normal stack-aware path and renders correctly,
        // while Continuity CTM/emissive stay fully ON for every other block (DO blocks are
        // material-textured and never needed CTM/emissive). Same insert-guard-at-HEAD pattern as Fix 25.
        'uvfixes_continuity_skip_domum': {
            'target': { 'type': 'CLASS', 'name': 'me.pepperbell.continuity.client.resource.ModelWrappingHandler' },
            'transformer': function (classNode) {
                var WRAP_DESC = '(Lnet/minecraft/client/resources/model/BakedModel;Lnet/minecraft/resources/ResourceLocation;Lnet/minecraft/client/resources/model/ModelResourceLocation;)Lnet/minecraft/client/resources/model/BakedModel;';
                var done = false;
                for (var i = 0; i < classNode.methods.size(); i++) {
                    var m = classNode.methods.get(i);
                    if (m.name.equals('wrap') && m.desc.equals(WRAP_DESC)) {
                        var list = new InsnList();
                        var cont = new LabelNode();
                        // if (model instanceof MateriallyTexturedBakedModel) return model;
                        list.add(new VarInsnNode(Opcodes.ALOAD, 1));
                        list.add(new TypeInsnNode(Opcodes.INSTANCEOF, 'com/ldtteam/domumornamentum/client/model/baked/MateriallyTexturedBakedModel'));
                        list.add(new JumpInsnNode(Opcodes.IFEQ, cont));
                        list.add(new VarInsnNode(Opcodes.ALOAD, 1));
                        list.add(new InsnNode(Opcodes.ARETURN));
                        list.add(cont);
                        m.instructions.insert(list);
                        done = true;
                        break;
                    }
                }
                log(done ? 'continuity ModelWrappingHandler.wrap skip-DO guard added (DO never CTM/emissive-wrapped -> renders; CTM/emissive kept for all other blocks)' : 'continuity: wrap(...) not found, patch skipped (mod updated?)');
                return classNode;
            }
        },
        // Fix 27 (see comment above uvStripInjectors): neuter the 3 broken
        // createaeronauticscurios 2.0 LinkedTypewriter mixins so the pack boots.
        'uvfixes_aerocurios_typewriter_be': {
            'target': { 'type': 'CLASS', 'name': 'com.titammods.aeronautics_curios_compat.mixin.MixinLinkedTypewriterBlockEntity' },
            'transformer': function (classNode) {
                return uvStripInjectors(classNode, 'aerocurios MixinLinkedTypewriterBlockEntity');
            }
        },
        'uvfixes_aerocurios_typewriter_entries': {
            'target': { 'type': 'CLASS', 'name': 'com.titammods.aeronautics_curios_compat.mixin.MixinLinkedTypewriterEntries' },
            'transformer': function (classNode) {
                return uvStripInjectors(classNode, 'aerocurios MixinLinkedTypewriterEntries');
            }
        },
        'uvfixes_aerocurios_typewriter_interaction': {
            'target': { 'type': 'CLASS', 'name': 'com.titammods.aeronautics_curios_compat.mixin.MixinLinkedTypewriterInteractionHandler' },
            'transformer': function (classNode) {
                return uvStripInjectors(classNode, 'aerocurios MixinLinkedTypewriterInteractionHandler');
            }
        },
        // Fix 28: fuelgoeshere 1.2.0 is an addon for the ORIGINAL Iron Furnaces; the user
        // swapped in the "Iron Furnace Reburn" fork, whose BlockIronFurnaceContainerBase
        // differs -> fuelgoeshere's @WrapOperation forceFuel finds 0 targets -> Critical
        // injection failure -> ironfurnaces mod-construction abort -> same wakes "Cannot get
        // config value before config is loaded" tick-1 cascade. Strip the injector from
        // MixinBlockIronFurnaceContainerBase (the iron-furnace hook); MixinAbstractFurnaceMenu
        // (vanilla furnaces) is left intact and keeps working.
        'uvfixes_fuelgoeshere_ironfurnace': {
            'target': { 'type': 'CLASS', 'name': 'cy.jdkdigital.fuelgoeshere.mixin.MixinBlockIronFurnaceContainerBase' },
            'transformer': function (classNode) {
                return uvStripInjectors(classNode, 'fuelgoeshere MixinBlockIronFurnaceContainerBase');
            }
        },
        // Fix 25: respackopts 4.11.3 + libjf 3.17.4 -- libjf ResourcePath.getName()
        // builds String.format("%s/%s/%s", this.type.getDirectory(), id.ns, id.path).
        // When a pack is scanned with a null PackType (Paxi datapacks seen via
        // dynamictrees' tree-pack scan), type.getDirectory() NPEs inside respackopts'
        // global PathPackResources.listPath wrapper -> corrupts dynamictrees' parallel
        // RegisterEvent -> cascade of unbound-value failures across ~10 mods -> wakes
        // "Cannot get config value before config is loaded" crash on tick 1.
        // Guard: if type is null, return id.toString() (non-null; won't match a
        // respackopts config so the pack passes through unfiltered). Lets Paxi
        // datapacks load cleanly without editing respackopts/libjf jars.
        'uvfixes_libjf_respackopts_nulltype': {
            'target': { 'type': 'CLASS', 'name': 'io.gitlab.jfronny.libjf.ResourcePath' },
            'transformer': function (classNode) {
                var done = false;
                for (var i = 0; i < classNode.methods.size(); i++) {
                    var m = classNode.methods.get(i);
                    if (m.name.equals('getName') && m.desc.equals('()Ljava/lang/String;')) {
                        var list = new InsnList();
                        var cont = new LabelNode();
                        list.add(new VarInsnNode(Opcodes.ALOAD, 0));
                        list.add(new FieldInsnNode(Opcodes.GETFIELD, 'io/gitlab/jfronny/libjf/ResourcePath', 'type', 'Lnet/minecraft/server/packs/PackType;'));
                        list.add(new JumpInsnNode(Opcodes.IFNONNULL, cont));
                        list.add(new VarInsnNode(Opcodes.ALOAD, 0));
                        list.add(new FieldInsnNode(Opcodes.GETFIELD, 'io/gitlab/jfronny/libjf/ResourcePath', 'id', 'Lnet/minecraft/resources/ResourceLocation;'));
                        list.add(new MethodInsnNode(Opcodes.INVOKEVIRTUAL, 'net/minecraft/resources/ResourceLocation', 'toString', '()Ljava/lang/String;', false));
                        list.add(new InsnNode(Opcodes.ARETURN));
                        list.add(cont);
                        m.instructions.insert(list);
                        done = true;
                        break;
                    }
                }
                log(done ? 'libjf ResourcePath.getName null-PackType guard applied (respackopts no longer NPEs on typeless packs)' : 'libjf: ResourcePath.getName not found, patch skipped (mod updated?)');
                return classNode;
            }
        },
        // Fix 26: libjf_unsafe 3.17.4 -- InterfaceImplTargetPatch class-load deadlock.
        // scanInterfaces(ClassNode) calls ClassLoader.loadClass(super), and getUpper(String)
        // calls Class.forName(name), DURING mixin transformation while modlauncher holds the
        // mixin-plugin delegates lock. Under parallel class loading (creative-tab tooltip build
        // via SessionSearchTrees.updateCreativeTooltips, or world-load chunk gen) two worker
        // threads form an AB-BA inversion between the mixin-plugin ArrayList monitor and a
        // per-class ModuleClassLoader monitor -> hard 3-way deadlock (Render thread + 2 workers),
        // 100% reproducible on opening the creative inventory. Fix: add uvScanByName(String) that
        // walks the super/interface hierarchy by READING .class bytes (ClassReader) instead of
        // loading classes -- identical INTERFACES data, ZERO classloading -> no lock inversion.
        // Redirect both loadClass (scanInterfaces) and Class.forName (getUpper) to it.
        'uvfixes_libjf_interfaceimpl_deadlock': {
            'target': { 'type': 'CLASS', 'name': 'io.gitlab.jfronny.libjf.unsafe.asm.patch.targeting.InterfaceImplTargetPatch' },
            'transformer': function (classNode) {
                var MethodNode = Java.type('org.objectweb.asm.tree.MethodNode');
                var IincInsnNode = Java.type('org.objectweb.asm.tree.IincInsnNode');
                var OWNER = 'io/gitlab/jfronny/libjf/unsafe/asm/patch/targeting/InterfaceImplTargetPatch';

                function prevReal(n) { n = n.getPrevious(); while (n !== null && n.getOpcode() < 0) n = n.getPrevious(); return n; }
                function nextReal(n) { n = n.getNext(); while (n !== null && n.getOpcode() < 0) n = n.getNext(); return n; }

                // ---- 1) add uvScanByName(String): bytes-based, recursive, no classloading ----
                var hasHelper = false;
                for (var q = 0; q < classNode.methods.size(); q++) {
                    if (classNode.methods.get(q).name.equals('uvScanByName')) { hasHelper = true; break; }
                }
                if (!hasHelper) {
                    var mn = new MethodNode(Opcodes.ACC_PRIVATE | Opcodes.ACC_STATIC | Opcodes.ACC_SYNTHETIC,
                        'uvScanByName', '(Ljava/lang/String;)V', null, null);
                    var il = mn.instructions;
                    var L_proceed = new LabelNode(), L_skipSup = new LabelNode(),
                        L_arrCond = new LabelNode(), L_arrEnd = new LabelNode(),
                        L_putMap = new LabelNode(), L_tryStart = new LabelNode(),
                        L_tryEnd = new LabelNode(), L_catch = new LabelNode(),
                        L_iterCond = new LabelNode(), L_iterEnd = new LabelNode();
                    // if (INTERFACES.containsKey(n)) return;
                    il.add(new FieldInsnNode(Opcodes.GETSTATIC, OWNER, 'INTERFACES', 'Ljava/util/Map;'));
                    il.add(new VarInsnNode(Opcodes.ALOAD, 0));
                    il.add(new MethodInsnNode(Opcodes.INVOKEINTERFACE, 'java/util/Map', 'containsKey', '(Ljava/lang/Object;)Z', true));
                    il.add(new JumpInsnNode(Opcodes.IFEQ, L_proceed));
                    il.add(new InsnNode(Opcodes.RETURN));
                    il.add(L_proceed);
                    // HashSet supers = new HashSet();
                    il.add(new TypeInsnNode(Opcodes.NEW, 'java/util/HashSet'));
                    il.add(new InsnNode(Opcodes.DUP));
                    il.add(new MethodInsnNode(Opcodes.INVOKESPECIAL, 'java/util/HashSet', '<init>', '()V', false));
                    il.add(new VarInsnNode(Opcodes.ASTORE, 1));
                    // InputStream is = OWNER.class.getClassLoader().getResourceAsStream(n.concat(".class"));
                    il.add(new LdcInsnNode(AsmType.getObjectType(OWNER)));
                    il.add(new MethodInsnNode(Opcodes.INVOKEVIRTUAL, 'java/lang/Class', 'getClassLoader', '()Ljava/lang/ClassLoader;', false));
                    il.add(new VarInsnNode(Opcodes.ALOAD, 0));
                    il.add(new LdcInsnNode('.class'));
                    il.add(new MethodInsnNode(Opcodes.INVOKEVIRTUAL, 'java/lang/String', 'concat', '(Ljava/lang/String;)Ljava/lang/String;', false));
                    il.add(new MethodInsnNode(Opcodes.INVOKEVIRTUAL, 'java/lang/ClassLoader', 'getResourceAsStream', '(Ljava/lang/String;)Ljava/io/InputStream;', false));
                    il.add(new VarInsnNode(Opcodes.ASTORE, 2));
                    // if (is == null) goto putMap;
                    il.add(new VarInsnNode(Opcodes.ALOAD, 2));
                    il.add(new JumpInsnNode(Opcodes.IFNULL, L_putMap));
                    // try {
                    il.add(L_tryStart);
                    il.add(new TypeInsnNode(Opcodes.NEW, 'org/objectweb/asm/ClassReader'));
                    il.add(new InsnNode(Opcodes.DUP));
                    il.add(new VarInsnNode(Opcodes.ALOAD, 2));
                    il.add(new MethodInsnNode(Opcodes.INVOKESPECIAL, 'org/objectweb/asm/ClassReader', '<init>', '(Ljava/io/InputStream;)V', false));
                    il.add(new VarInsnNode(Opcodes.ASTORE, 3));
                    // String sup = cr.getSuperName(); if (sup != null) supers.add(sup);
                    il.add(new VarInsnNode(Opcodes.ALOAD, 3));
                    il.add(new MethodInsnNode(Opcodes.INVOKEVIRTUAL, 'org/objectweb/asm/ClassReader', 'getSuperName', '()Ljava/lang/String;', false));
                    il.add(new VarInsnNode(Opcodes.ASTORE, 4));
                    il.add(new VarInsnNode(Opcodes.ALOAD, 4));
                    il.add(new JumpInsnNode(Opcodes.IFNULL, L_skipSup));
                    il.add(new VarInsnNode(Opcodes.ALOAD, 1));
                    il.add(new VarInsnNode(Opcodes.ALOAD, 4));
                    il.add(new MethodInsnNode(Opcodes.INVOKEVIRTUAL, 'java/util/HashSet', 'add', '(Ljava/lang/Object;)Z', false));
                    il.add(new InsnNode(Opcodes.POP));
                    il.add(L_skipSup);
                    // String[] itfs = cr.getInterfaces(); for (i=0;i<itfs.length;i++) supers.add(itfs[i]);
                    il.add(new VarInsnNode(Opcodes.ALOAD, 3));
                    il.add(new MethodInsnNode(Opcodes.INVOKEVIRTUAL, 'org/objectweb/asm/ClassReader', 'getInterfaces', '()[Ljava/lang/String;', false));
                    il.add(new VarInsnNode(Opcodes.ASTORE, 5));
                    il.add(new InsnNode(Opcodes.ICONST_0));
                    il.add(new VarInsnNode(Opcodes.ISTORE, 6));
                    il.add(L_arrCond);
                    il.add(new VarInsnNode(Opcodes.ILOAD, 6));
                    il.add(new VarInsnNode(Opcodes.ALOAD, 5));
                    il.add(new InsnNode(Opcodes.ARRAYLENGTH));
                    il.add(new JumpInsnNode(Opcodes.IF_ICMPGE, L_arrEnd));
                    il.add(new VarInsnNode(Opcodes.ALOAD, 1));
                    il.add(new VarInsnNode(Opcodes.ALOAD, 5));
                    il.add(new VarInsnNode(Opcodes.ILOAD, 6));
                    il.add(new InsnNode(Opcodes.AALOAD));
                    il.add(new MethodInsnNode(Opcodes.INVOKEVIRTUAL, 'java/util/HashSet', 'add', '(Ljava/lang/Object;)Z', false));
                    il.add(new InsnNode(Opcodes.POP));
                    il.add(new IincInsnNode(6, 1));
                    il.add(new JumpInsnNode(Opcodes.GOTO, L_arrCond));
                    il.add(L_arrEnd);
                    // is.close();
                    il.add(new VarInsnNode(Opcodes.ALOAD, 2));
                    il.add(new MethodInsnNode(Opcodes.INVOKEVIRTUAL, 'java/io/InputStream', 'close', '()V', false));
                    il.add(L_tryEnd);
                    il.add(new JumpInsnNode(Opcodes.GOTO, L_putMap));
                    // } catch (Throwable t) { /* ignore */ }
                    il.add(L_catch);
                    il.add(new VarInsnNode(Opcodes.ASTORE, 8));
                    // INTERFACES.put(n, supers);
                    il.add(L_putMap);
                    il.add(new FieldInsnNode(Opcodes.GETSTATIC, OWNER, 'INTERFACES', 'Ljava/util/Map;'));
                    il.add(new VarInsnNode(Opcodes.ALOAD, 0));
                    il.add(new VarInsnNode(Opcodes.ALOAD, 1));
                    il.add(new MethodInsnNode(Opcodes.INVOKEINTERFACE, 'java/util/Map', 'put', '(Ljava/lang/Object;Ljava/lang/Object;)Ljava/lang/Object;', true));
                    il.add(new InsnNode(Opcodes.POP));
                    // for (Iterator it = supers.iterator(); it.hasNext();) uvScanByName((String) it.next());
                    il.add(new VarInsnNode(Opcodes.ALOAD, 1));
                    il.add(new MethodInsnNode(Opcodes.INVOKEVIRTUAL, 'java/util/HashSet', 'iterator', '()Ljava/util/Iterator;', false));
                    il.add(new VarInsnNode(Opcodes.ASTORE, 7));
                    il.add(L_iterCond);
                    il.add(new VarInsnNode(Opcodes.ALOAD, 7));
                    il.add(new MethodInsnNode(Opcodes.INVOKEINTERFACE, 'java/util/Iterator', 'hasNext', '()Z', true));
                    il.add(new JumpInsnNode(Opcodes.IFEQ, L_iterEnd));
                    il.add(new VarInsnNode(Opcodes.ALOAD, 7));
                    il.add(new MethodInsnNode(Opcodes.INVOKEINTERFACE, 'java/util/Iterator', 'next', '()Ljava/lang/Object;', true));
                    il.add(new TypeInsnNode(Opcodes.CHECKCAST, 'java/lang/String'));
                    il.add(new MethodInsnNode(Opcodes.INVOKESTATIC, OWNER, 'uvScanByName', '(Ljava/lang/String;)V', false));
                    il.add(new JumpInsnNode(Opcodes.GOTO, L_iterCond));
                    il.add(L_iterEnd);
                    il.add(new InsnNode(Opcodes.RETURN));
                    mn.tryCatchBlocks.add(new TryCatchBlockNode(L_tryStart, L_tryEnd, L_catch, 'java/lang/Throwable'));
                    mn.maxStack = 4; mn.maxLocals = 9;
                    classNode.methods.add(mn);
                }

                // ---- 2) redirect the two classloading call sites to uvScanByName ----
                var redirectedLoad = false, redirectedForName = false;
                for (var i = 0; i < classNode.methods.size(); i++) {
                    var m = classNode.methods.get(i);
                    if (m.name.equals('scanInterfaces') && m.desc.equals('(Lorg/objectweb/asm/tree/ClassNode;)V')) {
                        var insns = m.instructions.toArray();
                        for (var k = 0; k < insns.length; k++) {
                            var insn = insns[k];
                            if (insn instanceof MethodInsnNode && insn.getOpcode() === Opcodes.INVOKEVIRTUAL
                                && insn.owner.equals('java/lang/ClassLoader') && insn.name.equals('loadClass')) {
                                // run: LDC(class), INVOKEVIRTUAL getClassLoader, ALOAD <super-internal>, loadClass, POP
                                var al = prevReal(insn);          // ALOAD (slashed super name, slot 3)
                                var cl = prevReal(al);            // INVOKEVIRTUAL Class.getClassLoader
                                var ldc = prevReal(cl);           // LDC class constant
                                var pop = nextReal(insn);         // POP (discards loaded Class)
                                var repl = new InsnList();
                                repl.add(new VarInsnNode(Opcodes.ALOAD, 3)); // slot 3 = slashed internal super name
                                repl.add(new MethodInsnNode(Opcodes.INVOKESTATIC, OWNER, 'uvScanByName', '(Ljava/lang/String;)V', false));
                                m.instructions.insertBefore(ldc, repl);
                                m.instructions.remove(ldc); m.instructions.remove(cl); m.instructions.remove(al);
                                m.instructions.remove(insn); m.instructions.remove(pop);
                                redirectedLoad = true;
                                break;
                            }
                        }
                    }
                    if (m.name.equals('getUpper') && m.desc.equals('(Ljava/lang/String;)Ljava/util/Set;')) {
                        var insns2 = m.instructions.toArray();
                        for (var k2 = 0; k2 < insns2.length; k2++) {
                            var in2 = insns2[k2];
                            if (in2 instanceof MethodInsnNode && in2.getOpcode() === Opcodes.INVOKESTATIC
                                && in2.owner.equals(OWNER) && in2.name.equals('scanInterfaces') && in2.desc.equals('(Ljava/lang/Class;)V')) {
                                // run: ALOAD0, BIPUSH 47, BIPUSH 46, replace, Class.forName, scanInterfaces(Class)
                                var fornm = prevReal(in2);        // INVOKESTATIC Class.forName
                                var rep = prevReal(fornm);        // INVOKEVIRTUAL String.replace
                                var b46 = prevReal(rep);          // BIPUSH 46
                                var b47 = prevReal(b46);          // BIPUSH 47
                                var aload0 = prevReal(b47);       // ALOAD 0
                                var newrun = new InsnList();
                                newrun.add(new VarInsnNode(Opcodes.ALOAD, 0));
                                newrun.add(new MethodInsnNode(Opcodes.INVOKESTATIC, OWNER, 'uvScanByName', '(Ljava/lang/String;)V', false));
                                m.instructions.insertBefore(aload0, newrun);
                                m.instructions.remove(aload0); m.instructions.remove(b47); m.instructions.remove(b46);
                                m.instructions.remove(rep); m.instructions.remove(fornm); m.instructions.remove(in2);
                                redirectedForName = true;
                                break;
                            }
                        }
                    }
                }
                log('libjf InterfaceImplTargetPatch deadlock fix: helper=' + (!hasHelper) + ' loadClass->scan=' + redirectedLoad
                    + ' forName->scan=' + redirectedForName + ' (bytes-based hierarchy, no classload during transform)'
                    + ((redirectedLoad && redirectedForName) ? '' : ' -- WARNING: a redirect did NOT apply -> creative-inventory deadlock fix INCOMPLETE (libjf updated? mod updated?)'));
                return classNode;
            }
        },
        // Fix 1: Quark 4.1-480 wraps the tiny potato model with Map.compute,
        // receiving null when a resource pack broke the model, and wraps it
        // blindly -> later NPE in Continuity model wrapping. Null in -> null out.
        'uvfixes_quark_potato': {
            'target': { 'type': 'CLASS', 'name': 'org.violetmoon.quark.addons.oddities.module.TinyPotatoModule$Client' },
            'transformer': function (classNode) {
                var done = false;
                for (var i = 0; i < classNode.methods.size(); i++) {
                    var m = classNode.methods.get(i);
                    if (m.name.startsWith('lambda$modelBake') && m.desc.endsWith(')Lnet/minecraft/client/resources/model/BakedModel;')) {
                        var isStatic = (m.access & Opcodes.ACC_STATIC) !== 0;
                        var slot = isStatic ? 1 : 2;
                        var list = new InsnList();
                        var cont = new LabelNode();
                        list.add(new VarInsnNode(Opcodes.ALOAD, slot));
                        list.add(new JumpInsnNode(Opcodes.IFNONNULL, cont));
                        list.add(new InsnNode(Opcodes.ACONST_NULL));
                        list.add(new InsnNode(Opcodes.ARETURN));
                        list.add(cont);
                        m.instructions.insert(list);
                        done = true;
                        break;
                    }
                }
                log(done ? 'quark tiny-potato null-guard applied' : 'quark: target method missing, patch skipped (mod updated?)');
                return classNode;
            }
        },
        // Fix 2: Spawn 4.0.4 FieldGuidePlugin.getEntityClass explodes with
        // MalformedParameterizedTypeException reading DeferredHolder generics.
        // Any throw -> return null; the caller already skips null entries.
        'uvfixes_spawn_fieldguide': {
            'target': { 'type': 'CLASS', 'name': 'com.ninni.spawn.compat.fieldguide.FieldGuidePlugin' },
            'transformer': function (classNode) {
                var done = false;
                for (var i = 0; i < classNode.methods.size(); i++) {
                    var m = classNode.methods.get(i);
                    if (m.name.equals('getEntityClass') && m.desc.equals('(Ljava/lang/reflect/Field;)Ljava/lang/Class;')) {
                        var start = new LabelNode();
                        var end = new LabelNode();
                        var handler = new LabelNode();
                        m.instructions.insert(start);
                        var tail = new InsnList();
                        tail.add(end);
                        tail.add(handler);
                        tail.add(new InsnNode(Opcodes.POP));
                        tail.add(new InsnNode(Opcodes.ACONST_NULL));
                        tail.add(new InsnNode(Opcodes.ARETURN));
                        m.instructions.add(tail);
                        m.tryCatchBlocks.add(new TryCatchBlockNode(start, end, handler, 'java/lang/Throwable'));
                        done = true;
                        break;
                    }
                }
                log(done ? 'spawn field-guide reflection guard applied' : 'spawn: target method missing, patch skipped (mod updated?)');
                return classNode;
            }
        },
        'uvfixes_mrpgc_spells': {
            'target': { 'type': 'CLASS', 'name': 'com.mrpgc_skill_tree.skills.MrpgSkillSpells' },
            'transformer': remapMrpgcClass
        },
        'uvfixes_mrpgc_client': {
            'target': { 'type': 'CLASS', 'name': 'com.mrpgc_skill_tree.client.MRPGCSkillTreeClient' },
            'transformer': remapMrpgcClass
        },
        // Fix 4: Ponder (JiJ in Create 6.0.10) StitchedSprite keeps a static
        // HashMap mutated from parallel mod-construction threads by every
        // Create addon -> intermittent ConcurrentModificationException.
        // HashMap -> ConcurrentHashMap, per-atlas lists -> synchronizedList.
        'uvfixes_ponder_stitchedsprite_race': {
            'target': { 'type': 'CLASS', 'name': 'net.createmod.catnip.render.StitchedSprite' },
            'transformer': function (classNode) {
                var swapped = 0, wrapped = 0;
                for (var i = 0; i < classNode.methods.size(); i++) {
                    var m = classNode.methods.get(i);
                    if (m.name.equals('<clinit>')) {
                        var insns = m.instructions.toArray();
                        for (var j = 0; j < insns.length; j++) {
                            var insn = insns[j];
                            if (insn instanceof TypeInsnNode && insn.getOpcode() == Opcodes.NEW && insn.desc.equals('java/util/HashMap')) {
                                insn.desc = 'java/util/concurrent/ConcurrentHashMap';
                                swapped++;
                            } else if (insn instanceof MethodInsnNode && insn.getOpcode() == Opcodes.INVOKESPECIAL && insn.owner.equals('java/util/HashMap') && insn.name.equals('<init>')) {
                                insn.owner = 'java/util/concurrent/ConcurrentHashMap';
                                swapped++;
                            }
                        }
                    } else if (m.name.startsWith('lambda$new$') && m.desc.endsWith(')Ljava/util/List;')) {
                        var insns2 = m.instructions.toArray();
                        for (var k = 0; k < insns2.length; k++) {
                            if (insns2[k].getOpcode() == Opcodes.ARETURN) {
                                m.instructions.insertBefore(insns2[k], new MethodInsnNode(Opcodes.INVOKESTATIC, 'java/util/Collections', 'synchronizedList', '(Ljava/util/List;)Ljava/util/List;', false));
                                wrapped++;
                            }
                        }
                    }
                }
                log('ponder StitchedSprite thread-safety: ' + swapped + ' map insns swapped, ' + wrapped + ' list returns wrapped' + (swapped == 0 ? ' - NOTHING MATCHED (mod updated?)' : ''));
                return classNode;
            }
        },
        // Fix 5: Supplemental Patches 0.8.0-beta shaderpack generator NPEs at
        // Buffer.kt:58 because its regex demands a space after "RENDERTARGETS:"
        // and this Complementary build writes "/* RENDERTARGETS:0,6,... */".
        // The generator aborts half-patched (colortex15 used but never declared
        // -> Iris ShaderCompileException) and the NPE during the texture-stitch
        // event makes vanilla drop ALL selected resource packs + redo the whole
        // resource reload (~44s wasted per boot). Regex space -> \s* (0+ spaces).
        'uvfixes_supplemental_rendertargets_regex': {
            'target': { 'type': 'CLASS', 'name': 'io.github.jedlimlx.supplemental_patches.shaders.BufferKt' },
            'transformer': function (classNode) {
                var OLD_RE = 'RENDERTARGETS: ((\\d+,)*\\d+)';
                var NEW_RE = 'RENDERTARGETS:\\s*((\\d+,)*\\d+)';
                var hits = 0;
                for (var i = 0; i < classNode.methods.size(); i++) {
                    var m = classNode.methods.get(i);
                    var insns = m.instructions.toArray();
                    for (var j = 0; j < insns.length; j++) {
                        var insn = insns[j];
                        if (insn instanceof LdcInsnNode && OLD_RE == insn.cst) {
                            insn.cst = NEW_RE;
                            hits++;
                        }
                    }
                }
                log(hits > 0 ? 'supplemental_patches RENDERTARGETS regex relaxed (' + hits + ' constant)' : 'supplemental_patches: regex constant missing, patch skipped (mod updated?)');
                return classNode;
            }
        },
        // Fix 6: Veil 4.1.3 changed PerformanceRenderTargetMixin._blitToScreen:
        // 4.0.0 blitted the finished frame to framebuffer 0 (the window,
        // hardcoded); 4.1.3 blits to whatever GL_DRAW_FRAMEBUFFER_BINDING is
        // currently bound -> if any mod leaves an FBO bound at present time the
        // frame goes offscreen forever (game alive, window frozen on last image,
        // resize -> black). Veil's own mixin plugin already force-disables this
        // exact mixin for known-conflicting mods (affinity/hdr_mod/soulshade)
        // but exposes no config. Use the same escape hatch: make
        // shouldApplyMixin return false for it -> vanilla blit (binds FBO 0).
        'uvfixes_veil_blit_mixin_disable': {
            'target': { 'type': 'CLASS', 'name': 'foundry.veil.impl.VeilMixinPlugin' },
            'transformer': function (classNode) {
                var done = false;
                for (var i = 0; i < classNode.methods.size(); i++) {
                    var m = classNode.methods.get(i);
                    if (m.name.equals('shouldApplyMixin') && m.desc.equals('(Ljava/lang/String;Ljava/lang/String;)Z')) {
                        var list = new InsnList();
                        var cont = new LabelNode();
                        list.add(new VarInsnNode(Opcodes.ALOAD, 2));
                        list.add(new LdcInsnNode('foundry.veil.mixin.performance.client.PerformanceRenderTargetMixin'));
                        list.add(new MethodInsnNode(Opcodes.INVOKEVIRTUAL, 'java/lang/String', 'equals', '(Ljava/lang/Object;)Z', false));
                        list.add(new JumpInsnNode(Opcodes.IFEQ, cont));
                        list.add(new InsnNode(Opcodes.ICONST_0));
                        list.add(new InsnNode(Opcodes.IRETURN));
                        list.add(cont);
                        m.instructions.insert(list);
                        done = true;
                        break;
                    }
                }
                log(done ? 'veil PerformanceRenderTargetMixin disabled (vanilla blit restored)' : 'veil: shouldApplyMixin missing, patch skipped (mod updated?)');
                return classNode;
            }
        },
        // Fix 7: Supplemental Patches generateUniforms appends declarations for
        // every registered uniform without checking whether the shaderpack
        // already declares them. This custom Complementary build declares
        // colortex14 itself -> duplicate declaration -> GLSL error C1038 ->
        // Iris disables shaders. Inject: read uniforms.glsl once at method
        // start, and skip any uniform whose " <name>;" already appears in it.
        'uvfixes_supplemental_uniform_dedupe': {
            'target': { 'type': 'CLASS', 'name': 'io.github.jedlimlx.supplemental_patches.shaders.UniformKt' },
            'transformer': function (classNode) {
                var done = false;
                for (var i = 0; i < classNode.methods.size(); i++) {
                    var m = classNode.methods.get(i);
                    if (!(m.name.equals('generateUniforms') && m.desc.equals('(Ljava/nio/file/Path;)V'))) continue;

                    // Prelude: slot 20 = content of <dir>/shaders/lib/uniforms.glsl ("" on any error)
                    var preStart = new LabelNode(), preEnd = new LabelNode(), preHandler = new LabelNode(), preDone = new LabelNode();
                    var pre = new InsnList();
                    pre.add(preStart);
                    pre.add(new VarInsnNode(Opcodes.ALOAD, 0));
                    pre.add(new MethodInsnNode(Opcodes.INVOKEINTERFACE, 'java/nio/file/Path', 'toAbsolutePath', '()Ljava/nio/file/Path;', true));
                    pre.add(new MethodInsnNode(Opcodes.INVOKEVIRTUAL, 'java/lang/Object', 'toString', '()Ljava/lang/String;', false));
                    pre.add(new LdcInsnNode('/shaders/lib/uniforms.glsl'));
                    pre.add(new MethodInsnNode(Opcodes.INVOKEVIRTUAL, 'java/lang/String', 'concat', '(Ljava/lang/String;)Ljava/lang/String;', false));
                    pre.add(new InsnNode(Opcodes.ICONST_0));
                    pre.add(new TypeInsnNode(Opcodes.ANEWARRAY, 'java/lang/String'));
                    pre.add(new MethodInsnNode(Opcodes.INVOKESTATIC, 'java/nio/file/Paths', 'get', '(Ljava/lang/String;[Ljava/lang/String;)Ljava/nio/file/Path;', false));
                    pre.add(new MethodInsnNode(Opcodes.INVOKESTATIC, 'java/nio/file/Files', 'readString', '(Ljava/nio/file/Path;)Ljava/lang/String;', false));
                    pre.add(new VarInsnNode(Opcodes.ASTORE, 20));
                    pre.add(preEnd);
                    pre.add(new JumpInsnNode(Opcodes.GOTO, preDone));
                    pre.add(preHandler);
                    pre.add(new InsnNode(Opcodes.POP));
                    pre.add(new LdcInsnNode(''));
                    pre.add(new VarInsnNode(Opcodes.ASTORE, 20));
                    pre.add(preDone);
                    m.instructions.insert(pre);
                    m.tryCatchBlocks.add(new TryCatchBlockNode(preStart, preEnd, preHandler, 'java/lang/Throwable'));

                    // First UNIFORMS loop: after "checkcast Uniform; astore U" insert
                    // "if (content.contains(' '+u.getName()+';')) continue;"
                    var insns = m.instructions.toArray();
                    for (var j = 0; j < insns.length; j++) {
                        var insn = insns[j];
                        if (insn instanceof TypeInsnNode && insn.getOpcode() == Opcodes.CHECKCAST
                                && insn.desc.equals('io/github/jedlimlx/supplemental_patches/shaders/Uniform')
                                && insns[j + 1] instanceof VarInsnNode && insns[j + 1].getOpcode() == Opcodes.ASTORE) {
                            var uSlot = insns[j + 1]['var'];
                            // loop-continue label = first backward GOTO after this point
                            var contLabel = null;
                            for (var k = j + 2; k < insns.length; k++) {
                                if (insns[k] instanceof JumpInsnNode && insns[k].getOpcode() == Opcodes.GOTO
                                        && m.instructions.indexOf(insns[k].label) < m.instructions.indexOf(insn)) {
                                    contLabel = insns[k].label;
                                    break;
                                }
                            }
                            if (contLabel === null) break;
                            var keep = new LabelNode();
                            var chk = new InsnList();
                            chk.add(new VarInsnNode(Opcodes.ALOAD, 20));
                            chk.add(new LdcInsnNode(' '));
                            chk.add(new VarInsnNode(Opcodes.ALOAD, uSlot));
                            chk.add(new MethodInsnNode(Opcodes.INVOKEVIRTUAL, 'io/github/jedlimlx/supplemental_patches/shaders/Uniform', 'getName', '()Ljava/lang/String;', false));
                            chk.add(new MethodInsnNode(Opcodes.INVOKEVIRTUAL, 'java/lang/String', 'concat', '(Ljava/lang/String;)Ljava/lang/String;', false));
                            chk.add(new LdcInsnNode(';'));
                            chk.add(new MethodInsnNode(Opcodes.INVOKEVIRTUAL, 'java/lang/String', 'concat', '(Ljava/lang/String;)Ljava/lang/String;', false));
                            chk.add(new MethodInsnNode(Opcodes.INVOKEVIRTUAL, 'java/lang/String', 'contains', '(Ljava/lang/CharSequence;)Z', false));
                            chk.add(new JumpInsnNode(Opcodes.IFEQ, keep));
                            chk.add(new JumpInsnNode(Opcodes.GOTO, contLabel));
                            chk.add(keep);
                            m.instructions.insert(insns[j + 1], chk);
                            done = true;
                            break; // first loop only (the GLSL builder)
                        }
                    }
                    if (done) {
                        m.maxLocals = Math.max(m.maxLocals, 22);
                        m.maxStack = Math.max(m.maxStack, 4);
                    }
                    break;
                }
                log(done ? 'supplemental uniform dedupe injected (no duplicate colortex declarations)' : 'supplemental UniformKt: pattern missing, patch skipped (mod updated?)');
                return classNode;
            }
        },
        // Fix 8: Supplemental Patches withErrorHandling only catches its own
        // MinecraftError type - a raw IOException/NPE from one bad item kills
        // the whole shaderpack install. Add a second catch-all entry: print
        // the stack trace and skip the item, the remaining items proceed.
        'uvfixes_supplemental_errorhandling_catchall': {
            'target': { 'type': 'CLASS', 'name': 'io.github.jedlimlx.supplemental_patches.shaders.ErrorHandlingKt' },
            'transformer': function (classNode) {
                var done = false;
                for (var i = 0; i < classNode.methods.size(); i++) {
                    var m = classNode.methods.get(i);
                    if (!(m.name.equals('withErrorHandling') && m.desc.equals('(Lkotlin/jvm/functions/Function0;)V'))) continue;
                    if (m.tryCatchBlocks.size() !== 1) break;
                    var existing = m.tryCatchBlocks.get(0);
                    var h2 = new LabelNode();
                    var tail = new InsnList();
                    tail.add(h2);
                    tail.add(new MethodInsnNode(Opcodes.INVOKEVIRTUAL, 'java/lang/Throwable', 'printStackTrace', '()V', false));
                    tail.add(new InsnNode(Opcodes.RETURN));
                    m.instructions.add(tail);
                    m.tryCatchBlocks.add(new TryCatchBlockNode(existing.start, existing.end, h2, 'java/lang/Throwable'));
                    done = true;
                    break;
                }
                log(done ? 'supplemental withErrorHandling catch-all added (bad items skipped, not fatal)' : 'supplemental ErrorHandlingKt: pattern missing, patch skipped (mod updated?)');
                return classNode;
            }
        },
        // Fix 9: Supplemental Patches runs its shaderpack generator inside the
        // TextureAtlasStitchedEvent handler; any escaping exception makes
        // vanilla remove ALL selected resource packs and redo the entire
        // resource reload (~44s + wiped pack selection, every boot). Wrap the
        // handler in try/catch Throwable -> print + return.
        'uvfixes_supplemental_stitch_event_guard': {
            'target': { 'type': 'CLASS', 'name': 'io.github.jedlimlx.supplemental_patches.events.ClientEvents' },
            'transformer': function (classNode) {
                var done = false;
                for (var i = 0; i < classNode.methods.size(); i++) {
                    var m = classNode.methods.get(i);
                    if (m.name.equals('textureStitchedEvent') && m.desc.equals('(Lnet/neoforged/neoforge/client/event/TextureAtlasStitchedEvent;)V')) {
                        var start = new LabelNode();
                        var end = new LabelNode();
                        var handler = new LabelNode();
                        m.instructions.insert(start);
                        var tail = new InsnList();
                        tail.add(end);
                        tail.add(handler);
                        tail.add(new MethodInsnNode(Opcodes.INVOKEVIRTUAL, 'java/lang/Throwable', 'printStackTrace', '()V', false));
                        tail.add(new InsnNode(Opcodes.RETURN));
                        m.instructions.add(tail);
                        m.tryCatchBlocks.add(new TryCatchBlockNode(start, end, handler, 'java/lang/Throwable'));
                        done = true;
                        break;
                    }
                }
                log(done ? 'supplemental textureStitchedEvent guard applied (resource reload protected)' : 'supplemental ClientEvents: target method missing, patch skipped (mod updated?)');
                return classNode;
            }
        },
        // Fix 10: Supplementaries' CompatSodiumFluidRendererMixin targets fluid
        // renderer internals that no longer exist in this pack's custom Sodium
        // 0.8.12-alpha.4 -> "Scanned 0 targets" critical injection failure ->
        // hard crash the moment a world is joined. Its plugin inherits
        // shouldApplyMixin from Moonlight's SimpleMixinPlugin; same escape
        // hatch as the Veil fix: return false for that exact mixin only.
        'uvfixes_supplementaries_sodium_fluid_mixin_disable': {
            'target': { 'type': 'CLASS', 'name': 'net.mehvahdjukaar.moonlight.api.misc.SimpleMixinPlugin' },
            'transformer': function (classNode) {
                var done = false;
                for (var i = 0; i < classNode.methods.size(); i++) {
                    var m = classNode.methods.get(i);
                    if (m.name.equals('shouldApplyMixin') && m.desc.equals('(Ljava/lang/String;Ljava/lang/String;)Z')) {
                        var list = new InsnList();
                        var cont = new LabelNode();
                        list.add(new VarInsnNode(Opcodes.ALOAD, 2));
                        list.add(new LdcInsnNode('net.mehvahdjukaar.supplementaries.mixins.neoforge.compat.CompatSodiumFluidRendererMixin'));
                        list.add(new MethodInsnNode(Opcodes.INVOKEVIRTUAL, 'java/lang/String', 'equals', '(Ljava/lang/Object;)Z', false));
                        list.add(new JumpInsnNode(Opcodes.IFEQ, cont));
                        list.add(new InsnNode(Opcodes.ICONST_0));
                        list.add(new InsnNode(Opcodes.IRETURN));
                        list.add(cont);
                        m.instructions.insert(list);
                        done = true;
                        break;
                    }
                }
                log(done ? 'supplementaries sodium fluid mixin disabled (incompatible with custom sodium)' : 'moonlight: shouldApplyMixin missing, patch skipped (mod updated?)');
                return classNode;
            }
        },
        // Fix 11: Expanded Combat's ModifyVanillaCreativeTabs anchors items
        // after minecraft:tipped_arrow in the vanilla Combat tab; that anchor
        // is missing in this pack -> NeoForge assertTargetExists throws ->
        // the exception rides up through sawmill's join-time creative-tab
        // rebuild into PlayerList.placeNewPlayer -> every world join is kicked
        // with "Invalid player data". Guard the whole listener: a missing
        // anchor logs and skips the vanilla-tab cross-listing (EC's own tabs
        // are registered elsewhere and unaffected).
        'uvfixes_expandedcombat_tab_guard': {
            'target': { 'type': 'CLASS', 'name': 'com.userofbricks.expanded_combat.init.ECCreativeTabs' },
            'transformer': function (classNode) {
                var done = false;
                for (var i = 0; i < classNode.methods.size(); i++) {
                    var m = classNode.methods.get(i);
                    if (m.name.equals('ModifyVanillaCreativeTabs') && m.desc.equals('(Lnet/neoforged/neoforge/event/BuildCreativeModeTabContentsEvent;)V')) {
                        var start = new LabelNode();
                        var end = new LabelNode();
                        var handler = new LabelNode();
                        m.instructions.insert(start);
                        var tail = new InsnList();
                        tail.add(end);
                        tail.add(handler);
                        tail.add(new MethodInsnNode(Opcodes.INVOKEVIRTUAL, 'java/lang/Throwable', 'printStackTrace', '()V', false));
                        tail.add(new InsnNode(Opcodes.RETURN));
                        m.instructions.add(tail);
                        m.tryCatchBlocks.add(new TryCatchBlockNode(start, end, handler, 'java/lang/Throwable'));
                        done = true;
                        break;
                    }
                }
                log(done ? 'expanded_combat vanilla-tab guard applied (missing tipped_arrow anchor no longer kicks)' : 'expanded_combat: target method missing, patch skipped (mod updated?)');
                return classNode;
            }
        },
        // Fix 12: Tombstone's ItemMagicScroll.getName builds the scroll name via
        // getAmplifier, which reads SERVER config (levelMaxMagicScrolls).
        // Server configs only exist in-world, so any name lookup at the main
        // menu throws IllegalStateException("Cannot get config value before
        // config is loaded"). Simply Tooltips' findRealStack iterates the WHOLE
        // item registry calling getHoverName for any component tooltip (e.g.
        // hovering in the Distant Horizons config screen) -> instant crash.
        // Catch-all on getAmplifier returning 0; in-world the config is loaded
        // so behavior is unchanged. Silent catch: the registry scan can hit
        // this every frame, printStackTrace would flood the log.
        'uvfixes_tombstone_scroll_config_guard': {
            'target': { 'type': 'CLASS', 'name': 'ovh.corail.tombstone.item.ItemMagicScroll' },
            'transformer': function (classNode) {
                var done = false;
                for (var i = 0; i < classNode.methods.size(); i++) {
                    var m = classNode.methods.get(i);
                    if (m.name.equals('getAmplifier') && m.desc.equals('(Lnet/minecraft/world/item/ItemStack;)I')) {
                        var start = new LabelNode();
                        var end = new LabelNode();
                        var handler = new LabelNode();
                        m.instructions.insert(start);
                        var tail = new InsnList();
                        tail.add(end);
                        tail.add(handler);
                        tail.add(new InsnNode(Opcodes.POP));
                        tail.add(new InsnNode(Opcodes.ICONST_0));
                        tail.add(new InsnNode(Opcodes.IRETURN));
                        m.instructions.add(tail);
                        m.tryCatchBlocks.add(new TryCatchBlockNode(start, end, handler, 'java/lang/Throwable'));
                        done = true;
                        break;
                    }
                }
                log(done ? 'tombstone magic-scroll config guard applied (menu-safe item names)' : 'tombstone: getAmplifier missing, patch skipped (mod updated?)');
                return classNode;
            }
        },
        // Fix 13: systemic companion to Fix 12. Simply Tooltips' registry-wide
        // name scan means ANY of the pack's 751 mod ids with a menu-unsafe
        // Item.getName override crashes the game from a single tooltip. Guard
        // the vanilla chokepoint instead of chasing each mod: getHoverName
        // falls back to Component.empty() rather than propagating. The try
        // block costs nothing unless something actually throws, and a blank
        // name in a tooltip cache beats a crash to desktop.
        'uvfixes_itemstack_hovername_guard': {
            'target': { 'type': 'CLASS', 'name': 'net.minecraft.world.item.ItemStack' },
            'transformer': function (classNode) {
                var done = false;
                for (var i = 0; i < classNode.methods.size(); i++) {
                    var m = classNode.methods.get(i);
                    if (m.name.equals('getHoverName') && m.desc.equals('()Lnet/minecraft/network/chat/Component;')) {
                        var start = new LabelNode();
                        var end = new LabelNode();
                        var handler = new LabelNode();
                        m.instructions.insert(start);
                        var tail = new InsnList();
                        tail.add(end);
                        tail.add(handler);
                        tail.add(new InsnNode(Opcodes.POP));
                        // Component is an interface: itf flag MUST be true
                        tail.add(new MethodInsnNode(Opcodes.INVOKESTATIC, 'net/minecraft/network/chat/Component', 'empty', '()Lnet/minecraft/network/chat/MutableComponent;', true));
                        tail.add(new InsnNode(Opcodes.ARETURN));
                        m.instructions.add(tail);
                        m.tryCatchBlocks.add(new TryCatchBlockNode(start, end, handler, 'java/lang/Throwable'));
                        done = true;
                        break;
                    }
                }
                log(done ? 'itemstack getHoverName guard applied (broken item names no longer crash menus)' : 'itemstack: getHoverName missing?! patch skipped');
                return classNode;
            }
        },
        // Fix 14: Biolith (JiJ'd in Quark) keeps GLOBAL static state shared by
        // all server instances. handleServerStopped nulls registryManager on
        // the OLD server's thread — which with this pack's slow worker-drain
        // shutdown can fire minutes late, right into the NEXT world's startup.
        // handleWorldStarting then hits getBiomeLookupOrThrow ->
        // Optional.empty().orElseThrow() -> NoSuchElementException -> server
        // crash on every second world start of a session. Head-inject: if
        // registryManager is null, re-seed it from the starting level's own
        // registryAccess() and restore serverStarted (self-heals per world).
        'uvfixes_biolith_registry_reseed': {
            'target': { 'type': 'CLASS', 'name': 'com.terraformersmc.biolith.impl.biome.BiomeCoordinator' },
            'transformer': function (classNode) {
                var done = false;
                var BC = 'com/terraformersmc/biolith/impl/biome/BiomeCoordinator';
                var FROZEN = 'net/minecraft/core/RegistryAccess$Frozen';
                for (var i = 0; i < classNode.methods.size(); i++) {
                    var m = classNode.methods.get(i);
                    if (m.name.equals('handleWorldStarting') && m.desc.equals('(Lnet/minecraft/server/level/ServerLevel;)V')) {
                        var skip = new LabelNode();
                        var head = new InsnList();
                        head.add(new FieldInsnNode(Opcodes.GETSTATIC, BC, 'registryManager', 'L' + FROZEN + ';'));
                        head.add(new JumpInsnNode(Opcodes.IFNONNULL, skip));
                        head.add(new VarInsnNode(Opcodes.ALOAD, 0));
                        head.add(new MethodInsnNode(Opcodes.INVOKEVIRTUAL, 'net/minecraft/server/level/ServerLevel', 'registryAccess', '()Lnet/minecraft/core/RegistryAccess;', false));
                        head.add(new TypeInsnNode(Opcodes.CHECKCAST, FROZEN));
                        head.add(new FieldInsnNode(Opcodes.PUTSTATIC, BC, 'registryManager', 'L' + FROZEN + ';'));
                        head.add(new InsnNode(Opcodes.ICONST_1));
                        head.add(new FieldInsnNode(Opcodes.PUTSTATIC, BC, 'serverStarted', 'Z'));
                        head.add(skip);
                        m.instructions.insert(head);
                        done = true;
                        break;
                    }
                }
                log(done ? 'biolith registry re-seed applied (second world start no longer crashes)' : 'biolith: handleWorldStarting missing, patch skipped (mod updated?)');
                return classNode;
            }
        },
        // Fix 15: JourneyMap 6.0.0-beta.83's join listener sends
        // ClientPermissionsPacket via common-networking, which throws
        // RegistrationException ("packet not registered on the server") on
        // second world join of a session. The exception rides up
        // EntityJoinLevelEvent -> ServerLevel.addPlayer ->
        // PlayerList.placeNewPlayer -> "Couldn't place player in world" kick.
        // Whole-body guard: a failed permissions sync degrades to client-side
        // defaults instead of kicking the join.
        'uvfixes_journeymap_join_guard': {
            'target': { 'type': 'CLASS', 'name': 'journeymap.common.event.NeoForgeServerEvents' },
            'transformer': function (classNode) {
                var done = false;
                for (var i = 0; i < classNode.methods.size(); i++) {
                    var m = classNode.methods.get(i);
                    if (m.name.equals('onEntityJoinWorldEvent') && m.desc.equals('(Lnet/neoforged/neoforge/event/entity/EntityJoinLevelEvent;)V')) {
                        var start = new LabelNode();
                        var end = new LabelNode();
                        var handler = new LabelNode();
                        m.instructions.insert(start);
                        var tail = new InsnList();
                        tail.add(end);
                        tail.add(handler);
                        tail.add(new MethodInsnNode(Opcodes.INVOKEVIRTUAL, 'java/lang/Throwable', 'printStackTrace', '()V', false));
                        tail.add(new InsnNode(Opcodes.RETURN));
                        m.instructions.add(tail);
                        m.tryCatchBlocks.add(new TryCatchBlockNode(start, end, handler, 'java/lang/Throwable'));
                        done = true;
                        break;
                    }
                }
                log(done ? 'journeymap join guard applied (packet errors no longer kick the player)' : 'journeymap: onEntityJoinWorldEvent missing, patch skipped (mod updated?)');
                return classNode;
            }
        },
        // Fix 16: supplemental_patches' MaterialGeneratorKt string-injects a
        // GBUFFERS_BLOCK declaration block into irisIPBR.glsl that declares
        // "bool noGeneratedNormals;" — but the custom Complementary build
        // already declares it in gbuffers_block.glsl -> C1038 duplicate
        // declaration in moving_block.fsh -> whole world pipeline fails.
        // Drop just that one line from the injected constant; the other four
        // declarations don't collide.
        'uvfixes_supplemental_material_dedup': {
            'target': { 'type': 'CLASS', 'name': 'io.github.jedlimlx.supplemental_patches.shaders.MaterialGeneratorKt' },
            'transformer': function (classNode) {
                var OLD = '#if defined GBUFFERS_ENTITIES || defined GBUFFERS_HAND\n    int subsurfaceMode;\n#endif\n\n#if defined GBUFFERS_BLOCK\n    float skyLightCheck = 0.0;\n    float overlayNoiseEmission;\n    vec3 maRecolor;\n    bool noGeneratedNormals;\n    bool noVanillaAO;\n#endif\n';
                var NEW = '#if defined GBUFFERS_ENTITIES || defined GBUFFERS_HAND\n    int subsurfaceMode;\n#endif\n\n#if defined GBUFFERS_BLOCK\n    float skyLightCheck = 0.0;\n    float overlayNoiseEmission;\n    vec3 maRecolor;\n    bool noVanillaAO;\n#endif\n';
                var count = 0;
                for (var i = 0; i < classNode.methods.size(); i++) {
                    var insns = classNode.methods.get(i).instructions.toArray();
                    for (var j = 0; j < insns.length; j++) {
                        var insn = insns[j];
                        if (insn instanceof LdcInsnNode && OLD == insn.cst) { insn.cst = NEW; count++; }
                    }
                }
                log(count > 0 ? 'supplemental material-gen dedup applied (' + count + ' constant, noGeneratedNormals no longer re-declared)' : 'supplemental MaterialGeneratorKt: constant missing, patch skipped (mod updated?)');
                return classNode;
            }
        },
        // Fix 17: Caverns & Chasms' JEI plugin streams ALL JEI item stacks and
        // its filter predicates call ArmorItem.getMaterial().getKey().location()
        // — NPE when any mod ships an item whose material/tier Holder is
        // unregistered (getKey()==null). JEI catches the error but aborts CC's
        // plugin registration mid-way -> CC recipes missing in JEI every join.
        // Guard both boolean filter lambdas: a broken item is skipped (false)
        // instead of killing the whole plugin. Silent (runs per item stack).
        'uvfixes_cavernschasms_jei_guard': {
            'target': { 'type': 'CLASS', 'name': 'com.teamabnormals.caverns_and_chasms.integration.jei.CCPlugin' },
            'transformer': function (classNode) {
                var fixed = 0;
                for (var i = 0; i < classNode.methods.size(); i++) {
                    var m = classNode.methods.get(i);
                    if ((m.name.equals('lambda$getRepairData$0') || m.name.equals('lambda$getRepairData$3'))
                            && m.desc.equals('(Lnet/minecraft/world/item/ItemStack;)Z')) {
                        var start = new LabelNode();
                        var end = new LabelNode();
                        var handler = new LabelNode();
                        m.instructions.insert(start);
                        var tail = new InsnList();
                        tail.add(end);
                        tail.add(handler);
                        tail.add(new InsnNode(Opcodes.POP));
                        tail.add(new InsnNode(Opcodes.ICONST_0));
                        tail.add(new InsnNode(Opcodes.IRETURN));
                        m.instructions.add(tail);
                        m.tryCatchBlocks.add(new TryCatchBlockNode(start, end, handler, 'java/lang/Throwable'));
                        fixed++;
                    }
                }
                log(fixed === 2 ? 'caverns_and_chasms JEI repair-filter guards applied (2 lambdas, broken items skipped)' : 'caverns_and_chasms: expected 2 filter lambdas, found ' + fixed + ' (mod updated?)');
                return classNode;
            }
        },
        // Fix 18: Uncraft Everything's JEI plugin costs ~5.1s per world join:
        // RecipeViewerHelpers.getRecipes scans EVERY RecipeManager recipe
        // sequentially on the render thread. The loop body is self-contained
        // (immutable recipe reads, adds to one local list, no JEI API calls),
        // so it parallelizes safely: wrap the result list in
        // Collections.synchronizedList and swap Collection.forEach for
        // Collection.parallelStream().forEach. Entry order becomes
        // nondeterministic, which JEI does not care about (per-item lookups).
        'uvfixes_uncrafteverything_jei_parallel': {
            'target': { 'type': 'CLASS', 'name': 'com.coolerpromc.uncrafteverything.util.RecipeViewerHelpers' },
            'transformer': function (classNode) {
                var done = 0;
                for (var i = 0; i < classNode.methods.size(); i++) {
                    var m = classNode.methods.get(i);
                    if (!m.name.equals('getRecipes')) continue;
                    var insns = m.instructions.toArray();
                    // (a) result ArrayList -> Collections.synchronizedList(...)
                    for (var j = 0; j < insns.length; j++) {
                        var a = insns[j];
                        if (a instanceof VarInsnNode && a.getOpcode() == Opcodes.ASTORE && a.var == 2) {
                            m.instructions.insertBefore(a, new MethodInsnNode(Opcodes.INVOKESTATIC, 'java/util/Collections', 'synchronizedList', '(Ljava/util/List;)Ljava/util/List;', false));
                            done++;
                            break;
                        }
                    }
                    // (b) RecipeManager.getRecipes() ... Collection.forEach ->
                    //     .parallelStream() ... Stream.forEach
                    for (var j = 0; j < insns.length; j++) {
                        var b = insns[j];
                        if (b instanceof MethodInsnNode && b.name.equals('getRecipes') && b.owner.equals('net/minecraft/world/item/crafting/RecipeManager')) {
                            m.instructions.insert(b, new MethodInsnNode(Opcodes.INVOKEINTERFACE, 'java/util/Collection', 'parallelStream', '()Ljava/util/stream/Stream;', true));
                            done++;
                        }
                        if (b instanceof MethodInsnNode && b.getOpcode() == Opcodes.INVOKEINTERFACE && b.owner.equals('java/util/Collection') && b.name.equals('forEach')) {
                            b.owner = 'java/util/stream/Stream';
                            done++;
                        }
                    }
                }
                log(done === 3 ? 'uncrafteverything JEI recipe scan parallelized (synchronizedList + parallelStream)' : 'uncrafteverything: expected 3 edits, did ' + done + ' (mod updated?)');
                return classNode;
            }
        },
        // Fix 19: townstead's EmfAnimationSourceAdapter.isAvailable() calls the
        // STATIC resolvePlayerCem() uncached on every invocation — per player
        // per frame. That method probes ALL resource packs (~700 in this pack)
        // x all candidate CEM paths through the union filesystem: measured
        // ~25% of render-thread time in-world (JFR). Only program() uses the
        // 'resolved' instance cache. Memoize resolvePlayerCem in an added
        // static field; skip caching the early Minecraft-null bail-out;
        // invalidate() clears it (resource reload correctness).
        'uvfixes_townstead_cem_probe_cache': {
            'target': { 'type': 'CLASS', 'name': 'com.aetherianartificer.townstead.client.animation.EmfAnimationSourceAdapter' },
            'transformer': function (classNode) {
                var FieldNode = Java.type('org.objectweb.asm.tree.FieldNode');
                var OWNER = 'com/aetherianartificer/townstead/client/animation/EmfAnimationSourceAdapter';
                var F = 'uvfixes$cemCache';
                var DESC = 'Ljava/util/Optional;';
                classNode.fields.add(new FieldNode(Opcodes.ACC_PRIVATE | Opcodes.ACC_STATIC | Opcodes.ACC_VOLATILE, F, DESC, null, null));
                var done = 0;
                for (var i = 0; i < classNode.methods.size(); i++) {
                    var m = classNode.methods.get(i);
                    if (m.name.equals('resolvePlayerCem') && m.desc.equals('()Ljava/util/Optional;')) {
                        // head: if (cache != null) return cache;
                        var head = new InsnList();
                        var compute = new LabelNode();
                        head.add(new FieldInsnNode(Opcodes.GETSTATIC, OWNER, F, DESC));
                        head.add(new JumpInsnNode(Opcodes.IFNULL, compute));
                        head.add(new FieldInsnNode(Opcodes.GETSTATIC, OWNER, F, DESC));
                        head.add(new InsnNode(Opcodes.ARETURN));
                        head.add(compute);
                        m.instructions.insert(head);
                        // cache at ARETURN #2 and #3 (#1 = early Minecraft-null
                        // bail before the scan, must stay uncached) — note the
                        // ARETURN our head added is now #1, so skip TWO.
                        var rets = 0;
                        var insns = m.instructions.toArray();
                        for (var j = 0; j < insns.length; j++) {
                            if (insns[j].getOpcode() == Opcodes.ARETURN) {
                                rets++;
                                if (rets >= 3) {
                                    var store = new InsnList();
                                    store.add(new InsnNode(Opcodes.DUP));
                                    store.add(new FieldInsnNode(Opcodes.PUTSTATIC, OWNER, F, DESC));
                                    m.instructions.insertBefore(insns[j], store);
                                    done++;
                                }
                            }
                        }
                    }
                    if (m.name.equals('invalidate') && m.desc.equals('()V')) {
                        var inv = new InsnList();
                        inv.add(new InsnNode(Opcodes.ACONST_NULL));
                        inv.add(new FieldInsnNode(Opcodes.PUTSTATIC, OWNER, F, DESC));
                        m.instructions.insert(inv);
                        done++;
                    }
                }
                log(done === 3 ? 'townstead CEM probe memoized (2 cache stores + invalidate hook; was ~25% of render thread)' : 'townstead: expected 3 edits, did ' + done + ' (mod updated?)');
                return classNode;
            }
        },
        // Fix 20: Smithing Template Viewer crashes its whole JEI plugin when
        // any SmithingTrimRecipe has a template Ingredient that resolves to an
        // empty stack array (template.getItems()[0] -> AIOOBE; empty/late tag).
        // Flaky across boots (resolution timing). Guard updateArmorStand:
        // broken trim shows an unequipped stand, rest of the plugin survives.
        // Silent (can run during GUI updates).
        'uvfixes_smithingtemplateviewer_empty_ingredient_guard': {
            'target': { 'type': 'CLASS', 'name': 'com.buuz135.smithingtemplateviewer.SmithingTrimWrapper' },
            'transformer': function (classNode) {
                var fixed = 0;
                for (var i = 0; i < classNode.methods.size(); i++) {
                    var m = classNode.methods.get(i);
                    if (m.name.equals('updateArmorStand') && m.desc.equals('(Lnet/minecraft/world/level/Level;)V')) {
                        var start = new LabelNode();
                        var end = new LabelNode();
                        var handler = new LabelNode();
                        m.instructions.insert(start);
                        var tail = new InsnList();
                        tail.add(end);
                        tail.add(handler);
                        tail.add(new InsnNode(Opcodes.POP));
                        tail.add(new InsnNode(Opcodes.RETURN));
                        m.instructions.add(tail);
                        m.tryCatchBlocks.add(new TryCatchBlockNode(start, end, handler, 'java/lang/Throwable'));
                        fixed++;
                    }
                }
                log(fixed === 1 ? 'smithingtemplateviewer armor-stand guard applied (empty trim ingredients skipped)' : 'smithingtemplateviewer: updateArmorStand not found (mod updated?)');
                return classNode;
            }
        },
        // Fix 21: Spawn 4.0.4 variant managers read entity.level().random /
        // blockEntity.getLevel().random — the SERVER THREAD's random — from
        // c2me chunkgen workers (finalizeSpawn / feature placement). c2me's
        // CheckedThreadLocalRandom then hard-fails the chunk: every broken
        // chunk + crash-report popup this week traced here (122 CMEs, 19
        // thrown-away chunks in one session). Swap the Level.random read for
        // a fresh local RandomSource: POP the Level, INVOKESTATIC
        // RandomSource.create(). Same distribution, no shared state.
        'uvfixes_spawn_animal_variant_random': {
            'target': { 'type': 'CLASS', 'name': 'com.ninni.spawn.server.data.AnimalVariantManager' },
            'transformer': function (classNode) {
                var n = swapLevelRandomForLocal(classNode, 'chooseWeightedVariant');
                log(n === 1 ? 'spawn AnimalVariantManager random made thread-safe (chunkgen no longer breaks chunks)' : 'spawn AnimalVariantManager: expected 1 Level.random read, found ' + n + ' (mod updated?)');
                return classNode;
            }
        },
        'uvfixes_spawn_block_variant_random': {
            'target': { 'type': 'CLASS', 'name': 'com.ninni.spawn.server.data.BlockVariantManager' },
            'transformer': function (classNode) {
                var n = swapLevelRandomForLocal(classNode, 'choose');
                log(n === 1 ? 'spawn BlockVariantManager random made thread-safe' : 'spawn BlockVariantManager: expected 1 Level.random read, found ' + n + ' (mod updated?)');
                return classNode;
            }
        },
        // Fix 22: NeoForge's BuildCreativeModeTabContentsEvent.insertAfter/
        // insertBefore throw IllegalArgumentException when the anchor stack is
        // missing from the tab (expanded_combat anchors on tipped_arrow, which
        // another mod removed). The underlying InsertableLinkedOpenCustomHashSet
        // .addAfter/.addBefore already fall back to a plain append when the
        // anchor is absent (contains() branch -> add()), so the assert is the
        // ONLY failure point. No-op it: items land at the tab end instead of
        // being dropped, and the per-tab-build stack spam stops. Our Fix 11
        // guard on expanded_combat stays as backstop for other throw shapes.
        'uvfixes_neoforge_tab_anchor_fallback': {
            'target': { 'type': 'CLASS', 'name': 'net.neoforged.neoforge.event.BuildCreativeModeTabContentsEvent' },
            'transformer': function (classNode) {
                var done = 0;
                for (var i = 0; i < classNode.methods.size(); i++) {
                    var m = classNode.methods.get(i);
                    if (m.name.equals('assertTargetExists') && m.desc.equals('(Lnet/neoforged/neoforge/common/util/InsertableLinkedOpenCustomHashSet;Lnet/minecraft/world/item/ItemStack;)V')) {
                        m.instructions.clear();
                        if (m.tryCatchBlocks !== null) m.tryCatchBlocks.clear();
                        if (m.localVariables !== null) m.localVariables.clear();
                        m.instructions.add(new InsnNode(Opcodes.RETURN));
                        done++;
                    }
                }
                log(done === 1 ? 'neoforge tab-anchor assert relaxed (missing anchors append at end instead of throwing)' : 'neoforge BuildCreativeModeTabContentsEvent: assertTargetExists not found (neoforge updated?)');
                return classNode;
            }
        },
        // Fix 23: fieldguide 1.11.2 SearchManager.matchByBiome iterates the whole
        // biome registry and, per matched biome x MobCategory x spawner entry,
        // does a FULL linear scan of all resolved guide entries
        // (getEntryForTarget) — the same EntityTypes repeat in nearly every
        // biome, so the scan runs thousands of times = a multi-second render
        // thread stall at every world join / resource reload (the mod ships 6
        // "!biome" group queries that resolve then). Memoize getEntryForTarget
        // per EntityType in a static HashMap, cleared at the head of both
        // top-level search entry points (cache window = one render-thread call;
        // the underlying entry map cannot change mid-call).
        'uvfixes_fieldguide_entry_cache': {
            'target': { 'type': 'CLASS', 'name': 'com.evandev.fieldguide.client.search.SearchManager' },
            'transformer': function (classNode) {
                var FieldNode = Java.type('org.objectweb.asm.tree.FieldNode');
                classNode.fields.add(new FieldNode(Opcodes.ACC_PUBLIC | Opcodes.ACC_STATIC, 'uv$entryCache', 'Ljava/util/HashMap;', null, null));
                var CACHE_DESC = 'Ljava/util/HashMap;';
                var resets = 0, wired = 0;
                for (var i = 0; i < classNode.methods.size(); i++) {
                    var m = classNode.methods.get(i);
                    var isReset = (m.name.equals('groupByQueries') && m.desc.equals('(Ljava/util/List;Ljava/util/List;)Ljava/util/List;'))
                               || (m.name.equals('searchEntries') && m.desc.equals('(Ljava/lang/String;Ljava/util/List;)Ljava/util/List;'));
                    if (isReset) {
                        var Lclear = new LabelNode();
                        var Lcont = new LabelNode();
                        var head = new InsnList();
                        head.add(new FieldInsnNode(Opcodes.GETSTATIC, classNode.name, 'uv$entryCache', CACHE_DESC));
                        head.add(new JumpInsnNode(Opcodes.IFNONNULL, Lclear));
                        head.add(new TypeInsnNode(Opcodes.NEW, 'java/util/HashMap'));
                        head.add(new InsnNode(Opcodes.DUP));
                        head.add(new MethodInsnNode(Opcodes.INVOKESPECIAL, 'java/util/HashMap', '<init>', '()V', false));
                        head.add(new FieldInsnNode(Opcodes.PUTSTATIC, classNode.name, 'uv$entryCache', CACHE_DESC));
                        head.add(new JumpInsnNode(Opcodes.GOTO, Lcont));
                        head.add(Lclear);
                        head.add(new FieldInsnNode(Opcodes.GETSTATIC, classNode.name, 'uv$entryCache', CACHE_DESC));
                        head.add(new MethodInsnNode(Opcodes.INVOKEVIRTUAL, 'java/util/HashMap', 'clear', '()V', false));
                        head.add(Lcont);
                        m.instructions.insert(head);
                        resets++;
                    }
                    if (m.name.equals('matchByBiome') && m.desc.equals('(Ljava/lang/String;Ljava/util/List;Z)Ljava/util/List;')) {
                        var insns = m.instructions.toArray();
                        for (var j = 0; j < insns.length; j++) {
                            var call = insns[j];
                            if (call instanceof MethodInsnNode && call.getOpcode() === Opcodes.INVOKEVIRTUAL
                                    && call.owner.equals('com/evandev/fieldguide/client/ClientFieldGuideManager')
                                    && call.name.equals('getEntryForTarget')) {
                                // walk back over labels/lines: GETFIELD type <- ALOAD slot <- INVOKESTATIC getInstance
                                var getf = call.getPrevious();
                                while (getf !== null && getf.getOpcode() < 0) getf = getf.getPrevious();
                                var aload = getf.getPrevious();
                                while (aload !== null && aload.getOpcode() < 0) aload = aload.getPrevious();
                                var getInst = aload.getPrevious();
                                while (getInst !== null && getInst.getOpcode() < 0) getInst = getInst.getPrevious();
                                var nstore = call.getNext();
                                while (nstore !== null && nstore.getOpcode() < 0) nstore = nstore.getNext();
                                if (getf.getOpcode() !== Opcodes.GETFIELD || aload.getOpcode() !== Opcodes.ALOAD
                                        || getInst.getOpcode() !== Opcodes.INVOKESTATIC || nstore.getOpcode() !== Opcodes.ASTORE) {
                                    break;
                                }
                                var slot = aload['var'];
                                var Lmiss = new LabelNode();
                                var Lstore = new LabelNode();
                                var chk = new InsnList();
                                chk.add(new FieldInsnNode(Opcodes.GETSTATIC, classNode.name, 'uv$entryCache', CACHE_DESC));
                                chk.add(new VarInsnNode(Opcodes.ALOAD, slot));
                                chk.add(new FieldInsnNode(Opcodes.GETFIELD, getf.owner, getf.name, getf.desc));
                                chk.add(new MethodInsnNode(Opcodes.INVOKEVIRTUAL, 'java/util/HashMap', 'containsKey', '(Ljava/lang/Object;)Z', false));
                                chk.add(new JumpInsnNode(Opcodes.IFEQ, Lmiss));
                                chk.add(new FieldInsnNode(Opcodes.GETSTATIC, classNode.name, 'uv$entryCache', CACHE_DESC));
                                chk.add(new VarInsnNode(Opcodes.ALOAD, slot));
                                chk.add(new FieldInsnNode(Opcodes.GETFIELD, getf.owner, getf.name, getf.desc));
                                chk.add(new MethodInsnNode(Opcodes.INVOKEVIRTUAL, 'java/util/HashMap', 'get', '(Ljava/lang/Object;)Ljava/lang/Object;', false));
                                chk.add(new JumpInsnNode(Opcodes.GOTO, Lstore));
                                chk.add(Lmiss);
                                m.instructions.insertBefore(getInst, chk);
                                var put = new InsnList();
                                put.add(new InsnNode(Opcodes.DUP));
                                put.add(new FieldInsnNode(Opcodes.GETSTATIC, classNode.name, 'uv$entryCache', CACHE_DESC));
                                put.add(new InsnNode(Opcodes.SWAP));
                                put.add(new VarInsnNode(Opcodes.ALOAD, slot));
                                put.add(new FieldInsnNode(Opcodes.GETFIELD, getf.owner, getf.name, getf.desc));
                                put.add(new InsnNode(Opcodes.SWAP));
                                put.add(new MethodInsnNode(Opcodes.INVOKEVIRTUAL, 'java/util/HashMap', 'put', '(Ljava/lang/Object;Ljava/lang/Object;)Ljava/lang/Object;', false));
                                put.add(new InsnNode(Opcodes.POP));
                                put.add(Lstore);
                                m.instructions.insertBefore(nstore, put);
                                wired++;
                                break;
                            }
                        }
                    }
                }
                log((resets === 2 && wired === 1) ? 'fieldguide entry-lookup cache wired (world-join biome search memoized)' : 'fieldguide: unexpected bytecode shape (resets=' + resets + ' wired=' + wired + ') — cache idle, mod behavior unchanged (mod updated?)');
                return classNode;
            }
        },
        // Fix 24: softimprints renders the first-person player model EVERY
        // frame into a discarding buffer (FirstPersonContactCapturer), while
        // its snapshot logic only accepts 1 frame in imprint_snapshot_interval
        // (=12). Gate the duplicate render with the mod's OWN admission check
        // (tryBeginLivingCapture: interval + same-frame dedupe + active-session
        // + immediate-request handling); on a passed gate, the inner mixin's
        // begin call no-ops (session already active) and capture proceeds
        // exactly as before. ~11/12 of the per-frame cost skipped.
        'uvfixes_softimprints_skip_wasted_capture_render': {
            'target': { 'type': 'CLASS', 'name': 'com.nine.softimprints.core.contact.model.render.FirstPersonContactCapturer' },
            'transformer': function (classNode) {
                var done = false;
                for (var i = 0; i < classNode.methods.size(); i++) {
                    var m = classNode.methods.get(i);
                    if (!m.name.equals('captureIfApplicable') || !m.desc.equals('(F)V')) continue;
                    var insns = m.instructions.toArray();
                    for (var j = 0; j < insns.length; j++) {
                        var insn = insns[j];
                        if (insn instanceof MethodInsnNode && insn.getOpcode() === Opcodes.INVOKESTATIC
                                && insn.owner.equals('com/nine/softimprints/core/contact/model/ModelContactSnapshotCache')
                                && insn.name.equals('beginCaptureRender')) {
                            var Lskip = new LabelNode();
                            var gate = new InsnList();
                            gate.add(new VarInsnNode(Opcodes.ALOAD, 2));
                            gate.add(new MethodInsnNode(Opcodes.INVOKESTATIC,
                                    'com/nine/softimprints/core/contact/model/ModelContactSnapshotCache',
                                    'tryBeginLivingCapture', '(Lnet/minecraft/world/entity/Entity;)Z', false));
                            gate.add(new JumpInsnNode(Opcodes.IFEQ, Lskip));
                            m.instructions.insertBefore(insn, gate);
                            var tail = new InsnList();
                            tail.add(Lskip);
                            tail.add(new InsnNode(Opcodes.RETURN));
                            m.instructions.add(tail);
                            done = true;
                            break;
                        }
                    }
                }
                log(done ? 'softimprints duplicate first-person capture render gated (skips ~11/12 frames)' : 'softimprints: captureIfApplicable/beginCaptureRender not found (mod updated?)');
                return classNode;
            }
        },
        // jeresources VillagerCategory crash guard: MCA registers professions
        // outlaw/guard/archer/adventurer/mercenary/cultist with
        // heldJobSite=PoiType.NONE (always-false predicate) yet gives them trades,
        // so JER keeps them; VillagersHelper.getPoiBlocks(Predicate) does
        // Stream.findFirst().get() on an empty Optional -> NoSuchElementException
        // at JEI villager-category build (VillagerCategory.setRecipe -> hasPois).
        // Not datapack-fixable (PoiType.NONE is hardcoded in MCA bytecode). Wrap
        // the method body: any throw -> Collections.emptySet() (hasPois()=false,
        // JEI skips the POI slot, no crash). Same guard style as
        // uvfixes_cavernschasms_jei_guard. Targets ONLY the Predicate overload.
        // Fix 33: Caverns & Chasms 3.0.0 server-join KICK ("Invalid player data" + accessory side-wipe).
        // CCCreativeTabs' two creative-tab display generators read a CLIENT config
        // (CCConfig.CLIENT.creativeTab / .copperCreativeTab via ModConfigSpec$BooleanValue.get()).
        // On a DEDICATED SERVER the CLIENT config is never loaded, so when Sawmill forces a
        // CreativeModeTabs rebuild during PlayerList.placeNewPlayer (to sync recipe order to a joining
        // client), .get() throws IllegalStateException "Cannot get config value before config is loaded"
        // -> "Couldn't place player in world" -> the FIRST player to join after a restart is kicked with
        // "Invalid player data", and the half-failed placement wipes their accessories. (ModernFix caches
        // tab contents after the first attempt, so retries connect -> wipe-then-works.)
        // FIX: wrap each (ItemDisplayParameters,Output)V tab-generator body in try{...}catch(Throwable){return}
        // so a config-not-loaded throw can't abort player placement. On a client the config IS loaded so the
        // guard never fires; on a dedicated server the tab contents are irrelevant (no GUI). Matched by
        // descriptor (not lambda index) so it survives a recompile. SERVER-side fix (also harmless on client).
        'uvfixes_caverns_creativetab_config_guard': {
            'target': { 'type': 'CLASS', 'name': 'com.teamabnormals.caverns_and_chasms.core.other.CCCreativeTabs' },
            'transformer': function (classNode) {
                var DESC = '(Lnet/minecraft/world/item/CreativeModeTab$ItemDisplayParameters;Lnet/minecraft/world/item/CreativeModeTab$Output;)V';
                var fixed = 0;
                for (var i = 0; i < classNode.methods.size(); i++) {
                    var m = classNode.methods.get(i);
                    if (m.desc.equals(DESC) && m.instructions.size() > 0) {
                        var start = new LabelNode();
                        var end = new LabelNode();
                        var handler = new LabelNode();
                        m.instructions.insert(start);
                        var tail = new InsnList();
                        tail.add(end);
                        tail.add(handler);
                        tail.add(new InsnNode(Opcodes.POP));
                        tail.add(new InsnNode(Opcodes.RETURN));
                        m.instructions.add(tail);
                        m.tryCatchBlocks.add(new TryCatchBlockNode(start, end, handler, 'java/lang/Throwable'));
                        fixed++;
                    }
                }
                log(fixed > 0 ? 'caverns_and_chasms CCCreativeTabs: guarded ' + fixed + ' creative-tab generator(s) (client-config read -> no server-join kick / accessory wipe)' : 'caverns_and_chasms CCCreativeTabs: no (ItemDisplayParameters,Output)V generators found, fixed=0 (mod updated?)');
                return classNode;
            }
        },
        'uvfixes_jeresources_villager_poi_guard': {
            'target': { 'type': 'CLASS', 'name': 'jeresources.util.VillagersHelper' },
            'transformer': function (classNode) {
                var fixed = 0;
                for (var i = 0; i < classNode.methods.size(); i++) {
                    var m = classNode.methods.get(i);
                    if (m.name.equals('getPoiBlocks') && m.desc.equals('(Ljava/util/function/Predicate;)Ljava/util/Set;')) {
                        var start = new LabelNode();
                        var end = new LabelNode();
                        var handler = new LabelNode();
                        m.instructions.insert(start);
                        var tail = new InsnList();
                        tail.add(end);
                        tail.add(handler);
                        tail.add(new InsnNode(Opcodes.POP));
                        tail.add(new MethodInsnNode(Opcodes.INVOKESTATIC, 'java/util/Collections', 'emptySet', '()Ljava/util/Set;', false));
                        tail.add(new InsnNode(Opcodes.ARETURN));
                        m.instructions.add(tail);
                        m.tryCatchBlocks.add(new TryCatchBlockNode(start, end, handler, 'java/lang/Throwable'));
                        fixed++;
                    }
                }
                log(fixed === 1 ? 'jeresources VillagersHelper.getPoiBlocks(Predicate) guarded (POI-less MCA professions -> emptySet, no JEI crash)' : 'jeresources: getPoiBlocks(Predicate) not found, fixed=' + fixed + ' (mod updated?)');
                return classNode;
            }
        },

        // hole_filler_mod: at the main menu (no integrated server started) HfmConfig.Server is null,
        // so HfmConfig.GetServerData() NPEs when JEI's background search indexer calls the items'
        // appendHoverText -> "Caught an error getting an Ingredient's tooltip" x10 per boot. Guard
        // GetServerData() with try/catch(Throwable) that returns a fresh new ServerConfigData(): its
        // no-arg ctor eagerly builds the full nested default graph (server_enforced.blacklist IntValues
        // default 0), so the immediate downstream deref (Permissions.GetFillerPermission) does NOT
        // re-NPE -> tooltip renders the default. In-world the real Server config is used unchanged.
        // Same wrap-body-in-try/catch pattern as the jeresources guard above. Self-no-ops if HFM moves.
        'uvfixes_hfm_serverdata_npe_guard': {
            'target': { 'type': 'CLASS', 'name': 'com.dannyboythomas.hole_filler_mod.config.HfmConfig' },
            'transformer': function (classNode) {
                var SCD = 'com/dannyboythomas/hole_filler_mod/config/ServerConfigData';
                var fixed = 0;
                for (var i = 0; i < classNode.methods.size(); i++) {
                    var m = classNode.methods.get(i);
                    if (m.name.equals('GetServerData') && m.desc.equals('()L' + SCD + ';')) {
                        var start = new LabelNode();
                        var end = new LabelNode();
                        var handler = new LabelNode();
                        m.instructions.insert(start);
                        var tail = new InsnList();
                        tail.add(end);
                        tail.add(handler);
                        tail.add(new InsnNode(Opcodes.POP));
                        tail.add(new TypeInsnNode(Opcodes.NEW, SCD));
                        tail.add(new InsnNode(Opcodes.DUP));
                        tail.add(new MethodInsnNode(Opcodes.INVOKESPECIAL, SCD, '<init>', '()V', false));
                        tail.add(new InsnNode(Opcodes.ARETURN));
                        m.instructions.add(tail);
                        m.tryCatchBlocks.add(new TryCatchBlockNode(start, end, handler, 'java/lang/Throwable'));
                        fixed++;
                    }
                }
                log(fixed === 1 ? 'hole_filler_mod HfmConfig.GetServerData guarded (menu-time Server==null -> fresh ServerConfigData, no JEI tooltip NPE)' : 'hfm: GetServerData()ServerConfigData not found, fixed=' + fixed + ' (mod updated?)');
                return classNode;
            }
        },

        // wakes 1.3.6: intermittent TICK-1 crash. WakeClientTicker.onClientTick (the client-tick event
        // handler) touches WakeHandler, whose <clinit> reads WakesConfig.APPEARANCE.wakeResolution.get()
        // at class-init. On a config-load race (tick 1 before the mod config has loaded) that throws
        // "Cannot get config value before config is loaded" -> ExceptionInInitializerError -> hard crash.
        // Guard BOTH static event handlers (onClientTick + onLevelUnload, the two WakeHandler entry points)
        // with try/catch(Throwable)->return (same wrap-body pattern as the jeresources/hfm guards above).
        // Effect: on the rare race, wakes' water ripples self-disable for that session instead of crashing;
        // normal (non-race) sessions are 100% unaffected. Self-no-ops with a log line if wakes updates.
        'uvfixes_wakes_clienttick_config_guard': {
            'target': { 'type': 'CLASS', 'name': 'com.leclowndu93150.wakes.event.WakeClientTicker' },
            'transformer': function (classNode) {
                var targets = [
                    { name: 'onClientTick', desc: '(Lnet/neoforged/neoforge/client/event/ClientTickEvent$Pre;)V' },
                    { name: 'onLevelUnload', desc: '(Lnet/neoforged/neoforge/event/level/LevelEvent$Unload;)V' }
                ];
                var fixed = 0;
                for (var i = 0; i < classNode.methods.size(); i++) {
                    var m = classNode.methods.get(i);
                    for (var t = 0; t < targets.length; t++) {
                        if (m.name.equals(targets[t].name) && m.desc.equals(targets[t].desc)) {
                            var start = new LabelNode();
                            var end = new LabelNode();
                            var handler = new LabelNode();
                            m.instructions.insert(start);
                            var tail = new InsnList();
                            tail.add(end);
                            tail.add(handler);
                            tail.add(new InsnNode(Opcodes.POP));    // discard the Throwable
                            tail.add(new InsnNode(Opcodes.RETURN)); // void return -> handler swallows it
                            m.instructions.add(tail);
                            m.tryCatchBlocks.add(new TryCatchBlockNode(start, end, handler, 'java/lang/Throwable'));
                            fixed++;
                        }
                    }
                }
                log(fixed === 2 ? 'wakes WakeClientTicker onClientTick+onLevelUnload guarded (tick-1 WakeHandler config-race no longer crashes; wakes self-disables that session)' : 'wakes: WakeClientTicker handlers not all found, fixed=' + fixed + ' (mod updated?)');
                return classNode;
            }
        },

        // Fix 42: DungeonCrawl 2.3.17 (The Dungeon) crashes chunk feature generation. Its
        // DungeonModelBlock$PropertyHolder.apply(BlockState) does state.setValue(this.property,
        // this.value) at line 298 -- guarded by hasProperty() but NOT by a null-check on this.value.
        // For some placed blocks (seen: minecraft:mossy_cobblestone_stairs) the resolved value is
        // null, so setValue(waterlogged, null) throws IllegalArgumentException -> "Feature placement"
        // ReportedException at ChunkGenerator.applyBiomeDecoration -> the whole chunk fails its
        // "features" stage -> "Failed to load chunk" (server-side worldgen, via c2me). Wrap apply()
        // in try/catch(Throwable) returning the INPUT BlockState unchanged: a property that can't be
        // applied is simply skipped, so the dungeon block keeps its default state (a dungeon stair
        // stays non-waterlogged, which is correct) and the chunk generates. Server-relevant (worldgen
        // runs on the dedicated server too). Self-no-ops with a log line if DungeonCrawl moves it.
        'uvfixes_dungeoncrawl_propertyholder_null_value_guard': {
            'target': { 'type': 'CLASS', 'name': 'xiroc.dungeoncrawl.dungeon.model.DungeonModelBlock$PropertyHolder' },
            'transformer': function (classNode) {
                var fixed = 0;
                for (var i = 0; i < classNode.methods.size(); i++) {
                    var m = classNode.methods.get(i);
                    if (!(m.name.equals('apply') && m.desc.equals('(Lnet/minecraft/world/level/block/state/BlockState;)Lnet/minecraft/world/level/block/state/BlockState;'))) continue;
                    var start = new LabelNode();
                    var end = new LabelNode();
                    var handler = new LabelNode();
                    m.instructions.insert(start);
                    var tail = new InsnList();
                    tail.add(end);
                    tail.add(handler);
                    tail.add(new InsnNode(Opcodes.POP));          // discard the Throwable
                    tail.add(new VarInsnNode(Opcodes.ALOAD, 1));  // load the input BlockState param
                    tail.add(new InsnNode(Opcodes.ARETURN));      // return it unchanged (skip the bad property)
                    m.instructions.add(tail);
                    m.tryCatchBlocks.add(new TryCatchBlockNode(start, end, handler, 'java/lang/Throwable'));
                    fixed++;
                }
                log(fixed === 1 ? 'dungeoncrawl DungeonModelBlock$PropertyHolder.apply guarded (null property value -> skip; no more chunk "Feature placement" crash from dungeon stairs)' : 'dungeoncrawl: PropertyHolder.apply not found, fixed=' + fixed + ' (mod updated?)');
                return classNode;
            }
        },

        // Fix 43: MineColonies builders getting STUCK on certain buildings. When a builder computes a
        // building's material requirements, structurize ItemStackUtils.getItemStacksOfTileEntity(
        // CompoundTag, BlockState, Level) deserializes each saved block-entity via BlockEntity.loadStatic.
        // If a blueprint/colony block carries a Domum Ornamentum materially_retexturable BLOCK ENTITY on a
        // non-DO block (seen: minecraft:white_concrete / minecraft:cobblestone -- a style-pack/version data
        // mismatch), MateriallyTexturedBlockEntity.<init> -> BlockEntity.validateBlockState throws
        // IllegalStateException "Invalid block entity ... got Block{...}". It propagates up through
        // GeneralBlockPlacementHandler.getRequiredItems -> AbstractEntityAIStructureWithWorkOrder
        // .requestMaterials -> the CitizenAI state machine, breaking the builder (stuck, won't build).
        // Wrap getItemStacksOfTileEntity in try/catch(Throwable) returning Collections.emptyList(): a
        // malformed TE just yields no items, the builder computes the rest and keeps building (the bad
        // block places as its plain block). Server-side (builder AI). Self-no-ops if structurize moves it.
        'uvfixes_structurize_tileentity_items_guard': {
            'target': { 'type': 'CLASS', 'name': 'com.ldtteam.structurize.api.ItemStackUtils' },
            'transformer': function (classNode) {
                var fixed = 0;
                for (var i = 0; i < classNode.methods.size(); i++) {
                    var m = classNode.methods.get(i);
                    if (!(m.name.equals('getItemStacksOfTileEntity') && m.desc.equals('(Lnet/minecraft/nbt/CompoundTag;Lnet/minecraft/world/level/block/state/BlockState;Lnet/minecraft/world/level/Level;)Ljava/util/List;'))) continue;
                    var start = new LabelNode();
                    var end = new LabelNode();
                    var handler = new LabelNode();
                    m.instructions.insert(start);
                    var tail = new InsnList();
                    tail.add(end);
                    tail.add(handler);
                    tail.add(new InsnNode(Opcodes.POP)); // discard the Throwable
                    tail.add(new MethodInsnNode(Opcodes.INVOKESTATIC, 'java/util/Collections', 'emptyList', '()Ljava/util/List;', false));
                    tail.add(new InsnNode(Opcodes.ARETURN)); // return an empty list (no items for the broken TE)
                    m.instructions.add(tail);
                    m.tryCatchBlocks.add(new TryCatchBlockNode(start, end, handler, 'java/lang/Throwable'));
                    fixed++;
                }
                log(fixed === 1 ? 'structurize ItemStackUtils.getItemStacksOfTileEntity guarded (malformed DO block-entity -> no items; MineColonies builders no longer stuck on bad colony blocks)' : 'structurize: getItemStacksOfTileEntity not found, fixed=' + fixed + ' (mod updated?)');
                return classNode;
            }
        },

        // Fix 38: MCA Reborn (enableVillagerPlayerModel) renders the player with its genetic
        // villager PlayerModel + a PoseStack scale, and its MixinHumanoidArmorLayer force-overrides
        // the armor model with PlayerArmorExtendedModel. That clobbers 3D/GeckoLib armor (Epic
        // Paladins etc.) -> misaligned/broken armor on the player. The ENTIRE genetic path is gated
        // on one plain (non-mixin) method: net.conczin.mca.MCAClient.useGeneticsRenderer(UUID)Z
        //   mca$injectScale: if useGeneticsRenderer -> scale + model=villagerModel; else model=vanillaModel, no scale.
        //   MixinHumanoidArmorLayer.mca$injectRender: mca$injectionActive = useGeneticsRenderer(uuid).
        // So make it return false when the player wears GeckoLib (GeoItem) armor: the player (body
        // AND armor) reverts to vanilla rendering, so GeckoLib armor renders on the vanilla skeleton
        // it was authored for and fits. Unarmored / vanilla-armored players keep the MCA genetic
        // model. Plain class (not a mixin target) -> no coremod-vs-mixin ordering risk; self-no-ops
        // with a log line if MCA renames/moves the method.
        'uvfixes_mca_vanilla_render_when_geckolib_armor': {
            'target': { 'type': 'CLASS', 'name': 'net.conczin.mca.MCAClient' },
            'transformer': function (classNode) {
                var done = false;
                for (var i = 0; i < classNode.methods.size(); i++) {
                    var m = classNode.methods.get(i);
                    if (!(m.name.equals('useGeneticsRenderer') && m.desc.equals('(Ljava/util/UUID;)Z'))) continue;
                    var cont = new LabelNode();
                    var retf = new LabelNode();
                    var list = new InsnList();
                    // ClientLevel level = Minecraft.getInstance().level; if (level == null) skip
                    list.add(new MethodInsnNode(Opcodes.INVOKESTATIC, 'net/minecraft/client/Minecraft', 'getInstance', '()Lnet/minecraft/client/Minecraft;', false));
                    list.add(new FieldInsnNode(Opcodes.GETFIELD, 'net/minecraft/client/Minecraft', 'level', 'Lnet/minecraft/client/multiplayer/ClientLevel;'));
                    list.add(new VarInsnNode(Opcodes.ASTORE, 1));
                    list.add(new VarInsnNode(Opcodes.ALOAD, 1));
                    list.add(new JumpInsnNode(Opcodes.IFNULL, cont));
                    // Player p = level.getPlayerByUUID(uuid); if (p == null) skip
                    list.add(new VarInsnNode(Opcodes.ALOAD, 1));
                    list.add(new VarInsnNode(Opcodes.ALOAD, 0));
                    list.add(new MethodInsnNode(Opcodes.INVOKEVIRTUAL, 'net/minecraft/world/level/Level', 'getPlayerByUUID', '(Ljava/util/UUID;)Lnet/minecraft/world/entity/player/Player;', false));
                    list.add(new VarInsnNode(Opcodes.ASTORE, 2));
                    list.add(new VarInsnNode(Opcodes.ALOAD, 2));
                    list.add(new JumpInsnNode(Opcodes.IFNULL, cont));
                    // for each armor slot: if the worn item carries a custom (non-vanilla-skeleton)
                    // model that clobbers the MCA genetic body, return false (render vanilla). Covers:
                    //   - GeckoLib GeoItem  (Epic Paladins etc.)
                    //   - magistuarmory MedievalArmorItem  (Epic Knights, NON-GeckoLib custom HumanoidModel armor;
                    //     DyeableMedievalArmorItem + the addon ArmorTypes all extend this base)
                    // Item is stashed in local 3 so each type check reads it fresh; every IFNE jumps to
                    // retf with an empty stack (consistent frame). COMPUTE_FRAMES handles local 3.
                    var slots = ['HEAD', 'CHEST', 'LEGS', 'FEET'];
                    var customArmor = ['software/bernie/geckolib/animatable/GeoItem',
                                       'com/magistuarmory/item/armor/MedievalArmorItem'];
                    for (var s = 0; s < slots.length; s++) {
                        list.add(new VarInsnNode(Opcodes.ALOAD, 2));
                        list.add(new FieldInsnNode(Opcodes.GETSTATIC, 'net/minecraft/world/entity/EquipmentSlot', slots[s], 'Lnet/minecraft/world/entity/EquipmentSlot;'));
                        list.add(new MethodInsnNode(Opcodes.INVOKEVIRTUAL, 'net/minecraft/world/entity/LivingEntity', 'getItemBySlot', '(Lnet/minecraft/world/entity/EquipmentSlot;)Lnet/minecraft/world/item/ItemStack;', false));
                        list.add(new MethodInsnNode(Opcodes.INVOKEVIRTUAL, 'net/minecraft/world/item/ItemStack', 'getItem', '()Lnet/minecraft/world/item/Item;', false));
                        list.add(new VarInsnNode(Opcodes.ASTORE, 3));
                        for (var c = 0; c < customArmor.length; c++) {
                            list.add(new VarInsnNode(Opcodes.ALOAD, 3));
                            list.add(new TypeInsnNode(Opcodes.INSTANCEOF, customArmor[c]));
                            list.add(new JumpInsnNode(Opcodes.IFNE, retf));
                        }
                    }
                    list.add(new JumpInsnNode(Opcodes.GOTO, cont));
                    list.add(retf);
                    list.add(new InsnNode(Opcodes.ICONST_0));
                    list.add(new InsnNode(Opcodes.IRETURN));
                    list.add(cont);
                    m.instructions.insert(list);
                    done = true;
                }
                log(done ? 'mca useGeneticsRenderer guarded: players wearing GeckoLib (GeoItem) armor render vanilla model+armor (Epic Paladins etc. fit again); unarmored/vanilla-armored keep MCA genetic model' : 'mca: useGeneticsRenderer(UUID)Z not found, patch skipped (MCA updated?)');
                return classNode;
            }
        },
    };
}

// Fix 21 helper: in the named method, replace every
// GETFIELD net/minecraft/world/level/Level.random : RandomSource
// with POP (drop the Level ref) + INVOKESTATIC RandomSource.create().
function swapLevelRandomForLocal(classNode, methodName) {
    var swapped = 0;
    for (var i = 0; i < classNode.methods.size(); i++) {
        var m = classNode.methods.get(i);
        if (!m.name.equals(methodName)) continue;
        var insns = m.instructions.toArray();
        for (var j = 0; j < insns.length; j++) {
            var insn = insns[j];
            if (insn instanceof FieldInsnNode && insn.getOpcode() === Opcodes.GETFIELD
                    && insn.owner.equals('net/minecraft/world/level/Level')
                    && insn.name.equals('random')
                    && insn.desc.equals('Lnet/minecraft/util/RandomSource;')) {
                m.instructions.insertBefore(insn, new InsnNode(Opcodes.POP));
                m.instructions.insertBefore(insn, new MethodInsnNode(Opcodes.INVOKESTATIC,
                        'net/minecraft/util/RandomSource', 'create', '()Lnet/minecraft/util/RandomSource;', true));
                m.instructions.remove(insn);
                swapped++;
            }
        }
    }
    return swapped;
}
