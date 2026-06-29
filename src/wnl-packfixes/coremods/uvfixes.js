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

// Fix 54: MineColonies_Tweaks 3.30 (May) + MineColonies_Compatibility 3.51 (May) were built
// against an OLDER minecolonies; today's 1.1.1332 snapshot refactored internals, so ~20 of their
// @Inject/@Redirect/@WrapOperation/@Modify* injectors no longer resolve (out-of-range @At ordinal,
// moved/removed call sites). Each defaults to require=1, so the first one mixin tries to apply
// throws a Critical InjectionError -> the DEDICATED SERVER reaches "Done" then crashes on the first
// tick (DataPackSyncEventHandler -> CompatibilityManager.discoverFood -> FoodUtils) -> DatHost
// boot-loops it. FIX: set require=0 + expect=0 on EVERY injector in every minecolonies-targeting
// mixin of both addons. `require` is a FLOOR, never a ceiling: a still-resolving injector applies
// exactly as before; only a genuinely-unresolvable one no-ops (graceful degradation) instead of
// aborting the load. No jar edit. Self-heals once the addons ship 1.1.1332-matched builds (their
// injectors resolve again and apply normally). Accessors/Invokers verified intact (offline scan),
// so there is no require-less break mode left unhandled.
var UV_INJECTOR_ANNS = [
    'Lorg/spongepowered/asm/mixin/injection/Inject;',
    'Lorg/spongepowered/asm/mixin/injection/Redirect;',
    'Lorg/spongepowered/asm/mixin/injection/ModifyArg;',
    'Lorg/spongepowered/asm/mixin/injection/ModifyArgs;',
    'Lorg/spongepowered/asm/mixin/injection/ModifyConstant;',
    'Lorg/spongepowered/asm/mixin/injection/ModifyVariable;'
];
function uvIsInjectorAnn(desc) {
    if (desc.startsWith('Lcom/llamalad7/mixinextras/injector/')) return true; // @WrapOperation/@ModifyExpressionValue/@WrapWithCondition/...
    for (var x = 0; x < UV_INJECTOR_ANNS.length; x++) if (desc.equals(UV_INJECTOR_ANNS[x])) return true;
    return false;
}
// Set an int element on an annotation node. A bare JS number added to a java.util.List is
// auto-boxed by Nashorn to java.lang.Integer (the sandbox blocks java.lang.* directly; see the
// coremod-nashorn-sandbox note) -- which is exactly the type Mixin's annotation reader expects.
function uvSetAnnInt(an, key, val) {
    if (an.values == null) an.values = new java.util.ArrayList();
    for (var i = 0; i < an.values.size(); i += 2) {
        if (an.values.get(i).equals(key)) { an.values.set(i + 1, val); return; }
    }
    an.values.add(key);
    an.values.add(val);
}
function uvOptionalizeInjectors(classNode, label) {
    var n = 0;
    for (var i = 0; i < classNode.methods.size(); i++) {
        var anns = classNode.methods.get(i).visibleAnnotations;
        if (anns == null) continue;
        for (var k = 0; k < anns.size(); k++) {
            if (uvIsInjectorAnn(anns.get(k).desc)) {
                uvSetAnnInt(anns.get(k), 'require', 0);
                uvSetAnnInt(anns.get(k), 'expect', 0);
                n++;
            }
        }
    }
    log('mc-addon ' + label + ': ' + n + ' injector(s) made optional (require=0) vs minecolonies 1.1.1332 drift');
    return classNode;
}

// Fix 63: sable VoxelNeighborhoodState$1/$2 (the static singletons IS_SOLID_MEMOIZED / IS_FULL_BLOCK)
// memoize the per-blockstate "is solid"/"is full block" result in a `private final Int2BooleanOpenHashMap
// cache`, keyed PURELY on blockState.hashCode() (position/getter ignored for keying — the result is a pure
// function of the state). The map is NOT thread-safe; c2me / c2me-OpenCL run worldgen block-changes across
// many threads, so two threads hit computeIfAbsent -> insert -> rehash() at once, corrupt the map, and
// rehash() throws ArrayIndexOutOfBoundsException (Index -1 out of bounds for length 65) -> "Exception
// ticking world" crash (only under parallel gen; single-thread gen never races it).
//
// FIRST fix (synchronized apply) cured the crash but added a GLOBAL monitor on a singleton: every solidity
// query across all gen threads serialized through one lock -> OCL parallel gen dropped 18 -> 4 chunks/s.
// PROPER fix (this one): give each thread its OWN cache. Convert the `cache` field from a shared
// Int2BooleanOpenHashMap to a ThreadLocal of per-thread Int2BooleanOpenHashMaps. Because the cached value
// is a pure function of blockState.hashCode(), per-thread caches yield byte-identical results — we only
// lose cross-thread reuse (re-derived solidity hits vanilla's own BlockState shape cache anyway). NO shared
// mutable state -> no rehash race, no lock, no contention -> sable's caching kept, OCL parallelism restored.
// c2me's gen pool is fixed-size, so the number of per-thread maps is bounded (no leak).
//
// Three retargets per $N (field + <init> + typed apply; bytecode verified, both $N identical):
//   (1) field  cache: Int2BooleanOpenHashMap  ->  ThreadLocal
//   (2) <init>: `new Int2BooleanOpenHashMap()` (new/invokespecial/putfield) -> `new ThreadLocal()`
//   (3) apply : after `getfield cache` (now a ThreadLocal), lazily fetch this thread's map:
//        tl.get(); dup; ifnonnull HAVE; pop; <new map; tl.set(map); leave map>; HAVE: checkcast map
//       -> leaves the same Int2BooleanOpenHashMap on the stack the original computeIfAbsent consumes.
// The synthetic bridge apply(Object,Object) and the static lambda$apply$0 are untouched.
var SABLE_MAP = 'it/unimi/dsi/fastutil/ints/Int2BooleanOpenHashMap';
var SABLE_MAPD = 'L' + SABLE_MAP + ';';
var SABLE_TL = 'java/lang/ThreadLocal';
var SABLE_TLD = 'L' + SABLE_TL + ';';
function sableVoxelCacheThreadLocal(classNode) {
    var fieldFixed = false, initFixed = false, applyFixed = false;

    // (1) field cache: Int2BooleanOpenHashMap -> ThreadLocal
    for (var f = 0; f < classNode.fields.size(); f++) {
        var fld = classNode.fields.get(f);
        if (fld.name.equals('cache') && fld.desc.equals(SABLE_MAPD)) { fld.desc = SABLE_TLD; fieldFixed = true; }
    }

    for (var i = 0; i < classNode.methods.size(); i++) {
        var m = classNode.methods.get(i);

        if (m.name.equals('<init>')) {
            // (2) retarget the map allocation + putfield to a bare ThreadLocal
            var iarr = m.instructions.toArray();
            var nNew = false, nInit = false, nPut = false;
            for (var j = 0; j < iarr.length; j++) {
                var insn = iarr[j];
                if (insn instanceof TypeInsnNode && insn.getOpcode() == Opcodes.NEW && insn.desc.equals(SABLE_MAP)) {
                    insn.desc = SABLE_TL; nNew = true;
                } else if (insn instanceof MethodInsnNode && insn.getOpcode() == Opcodes.INVOKESPECIAL
                        && insn.owner.equals(SABLE_MAP) && insn.name.equals('<init>')) {
                    insn.owner = SABLE_TL; nInit = true;
                } else if (insn instanceof FieldInsnNode && insn.getOpcode() == Opcodes.PUTFIELD
                        && insn.name.equals('cache') && insn.desc.equals(SABLE_MAPD)) {
                    insn.desc = SABLE_TLD; nPut = true;
                }
            }
            if (nNew && nInit && nPut) initFixed = true;

        } else if (m.name.equals('apply') && m.desc.endsWith(')Ljava/lang/Boolean;')) {
            // (3) rewrite the leading `getfield cache` into a lazy per-thread fetch
            var aarr = m.instructions.toArray();
            for (var k = 0; k < aarr.length; k++) {
                var gi = aarr[k];
                if (gi instanceof FieldInsnNode && gi.getOpcode() == Opcodes.GETFIELD
                        && gi.name.equals('cache') && gi.desc.equals(SABLE_MAPD)) {
                    gi.desc = SABLE_TLD; // now leaves a ThreadLocal on the stack
                    var HAVE = new LabelNode();
                    var list = new InsnList();
                    list.add(new MethodInsnNode(Opcodes.INVOKEVIRTUAL, SABLE_TL, 'get', '()Ljava/lang/Object;', false));
                    list.add(new InsnNode(Opcodes.DUP));
                    list.add(new JumpInsnNode(Opcodes.IFNONNULL, HAVE));
                    list.add(new InsnNode(Opcodes.POP));                 // discard the null
                    list.add(new VarInsnNode(Opcodes.ALOAD, 0));
                    list.add(new FieldInsnNode(Opcodes.GETFIELD, classNode.name, 'cache', SABLE_TLD));
                    list.add(new TypeInsnNode(Opcodes.NEW, SABLE_MAP));
                    list.add(new InsnNode(Opcodes.DUP));
                    list.add(new MethodInsnNode(Opcodes.INVOKESPECIAL, SABLE_MAP, '<init>', '()V', false));
                    list.add(new InsnNode(Opcodes.DUP_X1));              // stack: map, tl, map
                    list.add(new MethodInsnNode(Opcodes.INVOKEVIRTUAL, SABLE_TL, 'set', '(Ljava/lang/Object;)V', false));
                    list.add(HAVE);
                    list.add(new TypeInsnNode(Opcodes.CHECKCAST, SABLE_MAP));
                    m.instructions.insert(gi, list);                    // splice in AFTER the getfield
                    applyFixed = true;
                    break;
                }
            }
        }
    }
    log((fieldFixed && initFixed && applyFixed)
        ? 'sable ' + classNode.name + ' solidity cache -> per-thread ThreadLocal (contention-free; c2me/OCL parallel-gen AIOOBE fix, no global lock)'
        : 'sable ' + classNode.name + ': threadlocal rewrite incomplete (field=' + fieldFixed + ' init=' + initFixed + ' apply=' + applyFixed + ' — sable updated?)');
    return classNode;
}

// Fix 64: alltheleaks 1.1.9 (confirmed latest) AthenaResourceLoaderMixin @Shadows athena's setGetter as an
// INSTANCE method, but athena 4.0.6 made setGetter (+ the `getter` field) STATIC -> @Shadow static-modifier
// mismatch -> InvalidMixinException, the mixin fails to apply (fail-soft: athena's resource-loader leak-fix
// is lost, no crash). No newer alltheleaks exists. Match the mixin to athena 4.0.6:
//   (1) make the @Shadow setGetter static (drop ACC_ABSTRACT, add ACC_STATIC, give it a stub RETURN body that
//       Mixin discards when it rebinds the @Shadow to athena's static setGetter);
//   (2) in clearGetter rewrite `this.setGetter(null)` to a static call: clearGetter's body is exactly
//       `aload_0; aconst_null; invokevirtual setGetter` (verified) -> drop the receiver aload_0 and replace
//       the invokevirtual with invokestatic (same owner/name/desc; Mixin rewrites the owner to athena).
function alltheleaksAthenaStaticSetter(classNode) {
    var DESC = '(Ljava/util/function/Function;)V';
    var shadowed = false, callfixed = false;
    for (var i = 0; i < classNode.methods.size(); i++) {
        var m = classNode.methods.get(i);
        if (m.name.equals('setGetter') && m.desc.equals(DESC)) {
            m.access = (m.access & ~Opcodes.ACC_ABSTRACT) | Opcodes.ACC_STATIC;
            var body = new InsnList();
            body.add(new InsnNode(Opcodes.RETURN));
            m.instructions = body;
            shadowed = true;
        } else if (m.name.equals('clearGetter')) {
            var insns = m.instructions.toArray();
            for (var j = 0; j < insns.length; j++) {
                var insn = insns[j];
                if (insn instanceof MethodInsnNode && insn.getOpcode() == Opcodes.INVOKEVIRTUAL
                        && insn.name.equals('setGetter') && insn.desc.equals(DESC)) {
                    var receiver = insn.getPrevious().getPrevious(); // invokevirtual <- aconst_null <- aload_0
                    if (receiver instanceof VarInsnNode && receiver.getOpcode() == Opcodes.ALOAD && receiver.var == 0) {
                        m.instructions.remove(receiver);
                        m.instructions.set(insn, new MethodInsnNode(Opcodes.INVOKESTATIC, insn.owner, insn.name, insn.desc, false));
                        callfixed = true;
                    }
                    break;
                }
            }
        }
    }
    log((shadowed && callfixed)
        ? 'alltheleaks AthenaResourceLoaderMixin setGetter @Shadow static-ified for athena 4.0.6 (athena leak-fix restored)'
        : 'alltheleaks AthenaResourceLoaderMixin: shadow=' + shadowed + ' callfixed=' + callfixed + ' (alltheleaks/athena updated? leak-fix stays fail-soft)');
    return classNode;
}

function initializeCoreMod() {
    var UVMAP = {
        // (ScalableLux spike removed 2026-06-27: confirmed ModInfo is NOT coremod-transformable — FML
        //  loading runs in the boot layer, before the transforming classloader. The deployed PackFixes
        //  1.46.0 jar still carries the harmless dead spike entry; the next PackFixes build drops it.
        //  ScalableLux tag-drop needs a boot-layer ITransformationService, not a coremod. See task #164.)
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
        'uvfixes_sable_voxelcache_threadlocal_1': {
            'target': { 'type': 'CLASS', 'name': 'dev.ryanhcode.sable.physics.chunk.VoxelNeighborhoodState$1' },
            'transformer': sableVoxelCacheThreadLocal
        },
        'uvfixes_sable_voxelcache_threadlocal_2': {
            'target': { 'type': 'CLASS', 'name': 'dev.ryanhcode.sable.physics.chunk.VoxelNeighborhoodState$2' },
            'transformer': sableVoxelCacheThreadLocal
        },
        'uvfixes_alltheleaks_athena_static_setter': {
            'target': { 'type': 'CLASS', 'name': 'dev.uncandango.alltheleaks.mixin.core.main.AthenaResourceLoaderMixin' },
            'transformer': alltheleaksAthenaStaticSetter
        },
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
        // Fix: AdditionalStructures Events.onClientTick reads Config.UPDATE_CHECKER.get() EVERY client tick
        // (its update-checker phone-home). Its only guard is a field-null check, NOT a config-loaded check,
        // so at the main menu -- before AS's client config loads -- .get() throws "Cannot get config value
        // before config is loaded" and the game crashes on the first client tick. Became deterministic once
        // ~10 added mods delayed config load past tick 1. (smsn mixins the same CLASS but only its
        // SupporterCheck/SupporterRewards/onPlayerLogin methods -- NOT onClientTick -- so it's a red herring.)
        // The whole method IS the update checker, a network feature the pack already neuters via smsn, so the
        // safest fix is to no-op the tick entirely: insert RETURN at HEAD. No content lost. Self-no-ops with a
        // log line if AS renames/removes onClientTick (mod updated -> recheck if upstream guarded it).
        'uvfixes_additionalstructures_kill_updatechecker_tick': {
            'target': { 'type': 'CLASS', 'name': 'xxrexraptorxx.additionalstructures.utils.Events' },
            'transformer': function (classNode) {
                var done = false;
                for (var i = 0; i < classNode.methods.size(); i++) {
                    var m = classNode.methods.get(i);
                    if (m.name.equals('onClientTick')
                            && m.desc.equals('(Lnet/neoforged/neoforge/client/event/ClientTickEvent$Pre;)V')) {
                        var list = new InsnList();
                        list.add(new InsnNode(Opcodes.RETURN));
                        m.instructions.insert(list);
                        done = true;
                        break;
                    }
                }
                log(done ? 'additionalstructures Events.onClientTick no-op\'d (kills update-checker config-before-load crash at menu)' : 'additionalstructures: onClientTick(ClientTickEvent$Pre)V not found, patch skipped (mod updated?)');
                return classNode;
            }
        },
        // Fix 58: Galosphere ForgottenRuinsMapLootModifier.doApply calls MapItem.renderBiomePreviewMap, which
        // SYNCHRONOUSLY scans biomes across a large radius on the SERVER THREAD whenever a Forgotten Ruins
        // treasure map is rolled in loot -> 40s+ server-tick stalls at world load-in (during Ksyxis prepareLevels)
        // and again whenever the map drops. (Verified thread dump: Server thread in MapItem.renderBiomePreviewMap
        // <- net.orcinus.galosphere.util.loot_modifiers.ForgottenRuinsMapLootModifier.doApply.) FIX: skip the
        // renderBiomePreviewMap call (replace the INVOKESTATIC with POP,POP to discard its two args). The treasure
        // map still drops + keeps its target decoration + name; it just fills its biome colours in as the player
        // explores (exactly like a vanilla explorer map) instead of pre-rendering them in one huge synchronous
        // scan. Self-no-ops with a log line if Galosphere renames the method or drops the call.
        'uvfixes_galosphere_forgottenruins_map_stall': {
            'target': { 'type': 'CLASS', 'name': 'net.orcinus.galosphere.util.loot_modifiers.ForgottenRuinsMapLootModifier' },
            'transformer': function (classNode) {
                var done = false;
                for (var i = 0; i < classNode.methods.size() && !done; i++) {
                    var m = classNode.methods.get(i);
                    if (!m.name.equals('doApply')) continue;
                    var insns = m.instructions.toArray();
                    for (var j = 0; j < insns.length; j++) {
                        var insn = insns[j];
                        if (insn instanceof MethodInsnNode
                                && insn.getOpcode() == Opcodes.INVOKESTATIC
                                && insn.owner.equals('net/minecraft/world/item/MapItem')
                                && insn.name.equals('renderBiomePreviewMap')
                                && insn.desc.equals('(Lnet/minecraft/server/level/ServerLevel;Lnet/minecraft/world/item/ItemStack;)V')) {
                            m.instructions.insertBefore(insn, new InsnNode(Opcodes.POP));   // discard ItemStack (the map)
                            m.instructions.insertBefore(insn, new InsnNode(Opcodes.POP));   // discard ServerLevel
                            m.instructions.remove(insn);
                            done = true;
                            break;
                        }
                    }
                }
                log(done ? 'galosphere ForgottenRuinsMap renderBiomePreviewMap skipped (kills the 40s load-in biome-scan stall; map still drops + locates)' : 'galosphere: ForgottenRuinsMapLootModifier.doApply renderBiomePreviewMap call not found, patch skipped (mod updated?)');
                return classNode;
            }
        },
        // Fix 59: minecolonies research-load RESILIENCE (whole bug-class backstop for the Fix-58-sibling
        // world-load brick). minecolonies snapshots periodically ship a research file with a malformed cost
        // -- e.g. 1.1.1341 shipped combat/thathitthemark + combat/slicedanddecided with cost
        // "type":"minecolonies:item_simple", an ingredient type the mod no longer registers (only
        // counted/plant/food). The cost codec then throws (Utils.deserializeCodecMessFromJson ->
        // DataResult.resultOrPartial().get() on an empty Optional -> NoSuchElementException), and because the
        // throw propagates all the way up through ResearchListener.apply, the ENTIRE datapack reload aborts ->
        // "Errors in currently selected data packs prevented the world from loading" -> the world cannot be
        // entered AT ALL. WNL-Compat already data-fixes the specific 1341 files, but this guards the whole bug
        // class so the NEXT snapshot typo can't re-brick the save: wrap ResearchListener.parseResearchCosts in
        // try/catch(Throwable) -> on any parse failure return an empty cost List, so that one research becomes
        // cost-free instead of killing every world; all other research loads normally. (Scoped to research
        // costs on purpose -- guarding the shared Utils.deserializeCodecMessFromJson util globally would risk
        // returning null to unrelated callers.) Self-no-ops with a log line if minecolonies renames the method.
        'uvfixes_minecolonies_research_cost_resilience': {
            'target': { 'type': 'CLASS', 'name': 'com.minecolonies.core.datalistener.ResearchListener' },
            'transformer': function (classNode) {
                var done = false;
                for (var i = 0; i < classNode.methods.size(); i++) {
                    var m = classNode.methods.get(i);
                    if (m.name.equals('parseResearchCosts')
                            && m.desc.equals('(Lnet/minecraft/resources/ResourceLocation;Lcom/google/gson/JsonArray;Lcom/google/gson/JsonArray;)Ljava/util/List;')) {
                        var start = new LabelNode();
                        var end = new LabelNode();
                        var handler = new LabelNode();
                        m.instructions.insert(start);                                       // try-region start at method head
                        var tail = new InsnList();
                        tail.add(end);                                                      // try-region end (after original body)
                        tail.add(handler);                                                  // catch handler entry
                        tail.add(new InsnNode(Opcodes.POP));                                // discard the caught Throwable
                        tail.add(new TypeInsnNode(Opcodes.NEW, 'java/util/ArrayList'));
                        tail.add(new InsnNode(Opcodes.DUP));
                        tail.add(new MethodInsnNode(Opcodes.INVOKESPECIAL, 'java/util/ArrayList', '<init>', '()V', false));
                        tail.add(new InsnNode(Opcodes.ARETURN));                            // return an empty cost List
                        m.instructions.add(tail);
                        m.tryCatchBlocks.add(new TryCatchBlockNode(start, end, handler, 'java/lang/Throwable'));
                        done = true;
                        break;
                    }
                }
                log(done ? 'minecolonies ResearchListener.parseResearchCosts wrapped (bad cost -> empty list, never bricks world-load again)' : 'minecolonies: parseResearchCosts target missing, patch skipped (mod updated?)');
                return classNode;
            }
        },
        // Fix 60: slabbed 0.4.2-beta.1+26.2 (updated 2026-06-28) re-entrant chunk-load DEADLOCK at spawn.
        // slabbed mixins BlockBehaviour.getShape (slabbed$offsetOutline) -> SlabSupport.getYOffset ->
        // SlabAnchorAttachment.isAnchored, which does a BLOCKING Level.getChunk(int,int) (the (II)LevelChunk
        // overload that loads-to-FULL + parks). getShape is called per-block during wnllux StarLight THREADED
        // lighting on a c2me-worker, so this re-enters the chunk system from a worker -> the worker blocks on a
        // neighbour-chunk future -> c2me worker-pool starvation -> the spawn-chunk future never completes -> the
        // Server thread parks forever in PlayerRespawnLogic.getOverworldRespawnPos during player login (145s->
        // 300s+ watchdog ticks, world never loads). Verified from the live hang dump. Same class as the
        // DO×Farsight (Fix 26) + colonyborder (Fix 60-mod) re-entrant-getChunk guards. FIX: redirect every
        // blocking Level.getChunk(II) in SlabAnchorAttachment to a non-blocking helper -> on the SERVER use
        // ServerChunkCache.getChunkNow(II) (returns null if the chunk isn't already FULL — never loads/parks),
        // on the CLIENT keep the original Level.getChunk (ClientChunkCache is already non-blocking). isAnchored
        // already returns false on a null chunk, so an absent neighbour simply reads as 'not anchored' and the
        // slab outline self-corrects once that chunk is on the main thread — no deadlock, no behaviour change on
        // a loaded neighbour. (slabbed is a MOD class -> its vanilla calls are mojmap at coremod time, target as-is.)
        'uvfixes_slabbed_anchor_reentrant_getchunk': {
            'target': { 'type': 'CLASS', 'name': 'com.slabbed.anchor.SlabAnchorAttachment' },
            'transformer': function (classNode) {
                var MethodNode = Java.type('org.objectweb.asm.tree.MethodNode');
                var SELF = classNode.name;                              // com/slabbed/anchor/SlabAnchorAttachment
                var HELPER = 'wnl$nbGetChunk';
                var HDESC = '(Lnet/minecraft/world/level/Level;II)Lnet/minecraft/world/level/chunk/LevelChunk;';
                // 1) add the non-blocking helper (idempotent)
                var hasHelper = false;
                for (var h = 0; h < classNode.methods.size(); h++)
                    if (classNode.methods.get(h).name.equals(HELPER)) { hasHelper = true; break; }
                if (!hasHelper) {
                    var mn = new MethodNode(Opcodes.ACC_PRIVATE | Opcodes.ACC_STATIC | Opcodes.ACC_SYNTHETIC, HELPER, HDESC, null, null);
                    var il = new InsnList();
                    var L_client = new LabelNode();
                    il.add(new VarInsnNode(Opcodes.ALOAD, 0));                                   // level
                    il.add(new TypeInsnNode(Opcodes.INSTANCEOF, 'net/minecraft/server/level/ServerLevel'));
                    il.add(new JumpInsnNode(Opcodes.IFEQ, L_client));
                    il.add(new VarInsnNode(Opcodes.ALOAD, 0));                                   // server path
                    il.add(new TypeInsnNode(Opcodes.CHECKCAST, 'net/minecraft/server/level/ServerLevel'));
                    il.add(new MethodInsnNode(Opcodes.INVOKEVIRTUAL, 'net/minecraft/server/level/ServerLevel', 'getChunkSource', '()Lnet/minecraft/server/level/ServerChunkCache;', false));
                    il.add(new VarInsnNode(Opcodes.ILOAD, 1));
                    il.add(new VarInsnNode(Opcodes.ILOAD, 2));
                    il.add(new MethodInsnNode(Opcodes.INVOKEVIRTUAL, 'net/minecraft/server/level/ServerChunkCache', 'getChunkNow', '(II)Lnet/minecraft/world/level/chunk/LevelChunk;', false));
                    il.add(new InsnNode(Opcodes.ARETURN));
                    il.add(L_client);                                                            // client path (unchanged, non-blocking)
                    il.add(new VarInsnNode(Opcodes.ALOAD, 0));
                    il.add(new VarInsnNode(Opcodes.ILOAD, 1));
                    il.add(new VarInsnNode(Opcodes.ILOAD, 2));
                    il.add(new MethodInsnNode(Opcodes.INVOKEVIRTUAL, 'net/minecraft/world/level/Level', 'getChunk', '(II)Lnet/minecraft/world/level/chunk/LevelChunk;', false));
                    il.add(new InsnNode(Opcodes.ARETURN));
                    mn.instructions = il;
                    classNode.methods.add(mn);
                }
                // 2) redirect every blocking Level.getChunk(II) in this class -> the helper (skip the helper itself)
                var redirected = 0;
                for (var i = 0; i < classNode.methods.size(); i++) {
                    var m = classNode.methods.get(i);
                    if (m.name.equals(HELPER)) continue;
                    var arr = m.instructions.toArray();
                    for (var j = 0; j < arr.length; j++) {
                        var insn = arr[j];
                        if (insn instanceof MethodInsnNode
                                && insn.getOpcode() == Opcodes.INVOKEVIRTUAL
                                && insn.owner.equals('net/minecraft/world/level/Level')
                                && insn.name.equals('getChunk')
                                && insn.desc.equals('(II)Lnet/minecraft/world/level/chunk/LevelChunk;')) {
                            m.instructions.set(insn, new MethodInsnNode(Opcodes.INVOKESTATIC, SELF, HELPER, HDESC, false));
                            redirected++;
                        }
                    }
                }
                log(redirected > 0 ? ('slabbed SlabAnchorAttachment: ' + redirected + ' blocking Level.getChunk redirected to non-blocking getChunkNow (server) -- kills the spawn-load re-entrant deadlock') : 'slabbed: SlabAnchorAttachment Level.getChunk(II) not found, patch skipped (mod updated?)');
                return classNode;
            }
        },
        // Fix 56: createaeronauticscurios 2.1 (aeronautics_curios_compat) ClientKeyInputHandler.onClientTick
        // calls ModKeyBindings.REMOTE_USE.consumeClick() every client tick, but REMOTE_USE is null because the
        // mod's keybinding/feature init is skipped under the bundled Create Aeronautics 1.3.0 mismatch (same
        // family as the LinkedTypewriter injector strips above) -> NPE on the first client tick, hard crash.
        // HEAD-guard: if REMOTE_USE is null, return (skip the whole handler -- the remote-use + remote-typewriter
        // feature is already non-functional under the mismatch). Self-heals (runs normally) if a matched Create
        // Aeronautics ever registers the keybinding. Self-no-ops with a log line if the mod renames the method.
        'uvfixes_aerocurios_guard_null_keybind_tick': {
            'target': { 'type': 'CLASS', 'name': 'com.titammods.aeronautics_curios_compat.event.client.ClientKeyInputHandler' },
            'transformer': function (classNode) {
                var done = false;
                for (var i = 0; i < classNode.methods.size(); i++) {
                    var m = classNode.methods.get(i);
                    if (m.name.equals('onClientTick')
                            && m.desc.equals('(Lnet/neoforged/neoforge/client/event/ClientTickEvent$Post;)V')) {
                        var list = new InsnList();
                        var cont = new LabelNode();
                        // if (ModKeyBindings.REMOTE_USE == null) return;
                        list.add(new FieldInsnNode(Opcodes.GETSTATIC, 'com/titammods/aeronautics_curios_compat/registry/ModKeyBindings', 'REMOTE_USE', 'Lnet/minecraft/client/KeyMapping;'));
                        list.add(new JumpInsnNode(Opcodes.IFNONNULL, cont));
                        list.add(new InsnNode(Opcodes.RETURN));
                        list.add(cont);
                        m.instructions.insert(list);
                        done = true;
                        break;
                    }
                }
                log(done ? 'aerocurios ClientKeyInputHandler.onClientTick null-REMOTE_USE guard added (no keybinding NPE under the Create Aeronautics version mismatch)' : 'aerocurios: onClientTick(ClientTickEvent$Post)V not found, patch skipped (mod updated?)');
                return classNode;
            }
        },
        // Fix 57: GLOBAL forgified-fabric-api (FFAPI) entity-attribute timing fix. FFAPI's
        // FabricDefaultAttributeRegistry.register(EntityType, AttributeSupplier) eagerly puts into vanilla
        // DefaultAttributes DURING a mod's RegisterEvent, forcing DefaultAttributes.<clinit> before later
        // registries (e.g. atmospheric's camel_variant entity_data_serializer) have bound -> "Trying to
        // access unbound value" NPE poisons the vanilla class -> whole-load cascade (lne_wizards ->
        // takesapillage/magistuarmory unbound -> animatica config-not-loaded at render). FIX: rewrite the
        // register(EntityType, AttributeSupplier) body to HEAD-call WNL-FFAPIAttrFix's enqueue() in place of
        // the eager put, then RETURN; the wnl_ffapiattr addon replays the queue at EntityAttributeCreationEvent
        // (correct NeoForge timing, after ALL registration). The Builder overload funnels through this one, so
        // this single redirect covers every FFAPI-attribute mod (the LNE series + future). SHIP WITH
        // WNL-FFAPIAttrFix-1.0.0.jar (removing that jar makes this enqueue() call dangle).
        'uvfixes_ffapi_defer_attribute_register': {
            'target': { 'type': 'CLASS', 'name': 'net.fabricmc.fabric.api.object.builder.v1.entity.FabricDefaultAttributeRegistry' },
            'transformer': function (classNode) {
                var done = false;
                for (var i = 0; i < classNode.methods.size(); i++) {
                    var m = classNode.methods.get(i);
                    if (m.name.equals('register')
                            && m.desc.equals('(Lnet/minecraft/world/entity/EntityType;Lnet/minecraft/world/entity/ai/attributes/AttributeSupplier;)V')) {
                        var list = new InsnList();
                        list.add(new VarInsnNode(Opcodes.ALOAD, 0));   // EntityType (static -> slot 0)
                        list.add(new VarInsnNode(Opcodes.ALOAD, 1));   // AttributeSupplier
                        list.add(new MethodInsnNode(Opcodes.INVOKESTATIC, 'com/wnl/ffapiattr/FfapiAttrDefer', 'enqueue', '(Lnet/minecraft/world/entity/EntityType;Lnet/minecraft/world/entity/ai/attributes/AttributeSupplier;)V', false));
                        list.add(new InsnNode(Opcodes.RETURN));
                        m.instructions.insert(list);
                        done = true;
                        break;
                    }
                }
                log(done ? 'FFAPI FabricDefaultAttributeRegistry.register(type,supplier) deferred to wnl_ffapiattr queue (kills the DefaultAttributes-clinit-too-early cascade for ALL FFAPI-attribute mods)' : 'FFAPI: register(EntityType,AttributeSupplier)V not found, patch skipped (FFAPI updated?)');
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
        // Fix 50: Fusion 1.3.1 x Continuity 3.0.0 SpriteLoader stitch-order collision (nature-block
        // atlas renders the WRONG texture region with a Fusion-format Better-Grass pack present).
        // Both @Mixin(SpriteLoader). Fusion's SpriteLoaderMixin is priority=900 (it deliberately runs
        // OUTSIDE other sprite mixins): @Inject getStitchedSprites RETURN -> afterLoadSprites() does
        // map.remove(dummy)+map.put(realSprite), baking the connected-texture atlas regions. Continuity's
        // SpriteLoaderMixin is DEFAULT priority=1000 (higher applies FIRST) with @ModifyArg on
        // loadAndStitch + @Inject stitch RETURN. At 1000 Continuity wraps INSIDE Fusion's 900, inverting
        // the order Fusion's 900 was written for -> grass/dirt/path/farmland/podzol/mycelium resolve to
        // the wrong stitched region. Silent (no parse error; matches the clean log). Fix: lower Continuity
        // SpriteLoaderMixin priority 1000 -> 800 (below Fusion 900) so Fusion's map-rewrite is authoritative
        // and Continuity reads the corrected map for emissives after. Class-annotation only; no method
        // bytecode touched; emissive CTM still works. Keeps Fusion 1.3.1 + Continuity + the pack.
        'uvfixes_continuity_spriteloader_priority': {
            'target': { 'type': 'CLASS', 'name': 'me.pepperbell.continuity.client.mixin.SpriteLoaderMixin' },
            'transformer': function (classNode) {
                var MIXIN_DESC = 'Lorg/spongepowered/asm/mixin/Mixin;';
                var done = false;
                var anns = classNode.invisibleAnnotations; // @Mixin is RuntimeInvisible (CLASS retention)
                if (anns != null) {
                    for (var i = 0; i < anns.size(); i++) {
                        var a = anns.get(i);
                        if (!a.desc.equals(MIXIN_DESC)) continue;
                        // Rebuild the values list FRESH (flat [key,value,...]): copy every existing
                        // pair except any 'priority', then append a clean ['priority', 800]. This is
                        // atomic + always even-length (a half-mutated/odd list corrupts AnnotationNode.
                        // accept -> "Index N out of bounds"). Integer.valueOf, not new Integer(...),
                        // which Nashorn can mishandle.
                        var nv = new java.util.ArrayList();
                        if (a.values != null) {
                            for (var j = 0; j + 1 < a.values.size(); j += 2) {
                                if (!a.values.get(j).equals('priority')) {
                                    nv.add(a.values.get(j));
                                    nv.add(a.values.get(j + 1));
                                }
                            }
                        }
                        nv.add('priority');
                        // The coremod Nashorn sandbox (CoreModScriptingEngine.checkClass) whitelists
                        // ONLY java.util / java.util.function / org.objectweb.asm.* -- ALL of java.lang
                        // is blocked, so EVERY route to java.lang.Integer fails:
                        //   new java.lang.Integer(800)         -> bare path = JavaPackage, not a class
                        //   java.lang.Integer.valueOf(800)     -> same JavaPackage
                        //   Java.type('java.lang.Integer')...  -> ClassNotFoundException (filtered)
                        // BUT a bare JS int literal added to a List<Object> is auto-boxed by Nashorn
                        // (15.4) to java.lang.Integer -- never Double -- which is exactly what ASM's
                        // AnnotationNode wants for an int element. Verified empirically (BoxTest).
                        nv.add(800);
                        a.values = nv;
                        done = true;
                        break;
                    }
                }
                log(done ? 'continuity SpriteLoaderMixin priority -> 800 (below Fusion 900; fixes nature-block atlas region swap)'
                         : 'continuity SpriteLoaderMixin: @Mixin annotation not found, patch skipped (mod updated?)');
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
                // modelBake calls Map.compute on ModernFix's immutable EmulatedModelRegistry (dynamic_resources):
                // compute's internal put()/remove() both throw UnsupportedOperationException on the read-only
                // DynamicMap. ModernFix re-fires the ModifyBakingResult event per-namespace so the throw surfaces
                // under foreign-mod scope (e.g. supplementaries). Guard modelBake to no-op on UOE only -- the one
                // exception that is impossible-to-satisfy here (the tiny_potato model wrapper is already abandoned
                // today when the op throws, so this removes the spam + aborted-iteration with no behaviour change).
                var uoe = false;
                for (var k = 0; k < classNode.methods.size(); k++) {
                    var mm = classNode.methods.get(k);
                    if (mm.name.equals('modelBake') && mm.desc.equals('(Lorg/violetmoon/zeta/client/event/load/ZModel$ModifyBakingResult;)V')) {
                        var ps = new LabelNode();
                        var pe = new LabelNode();
                        var ph = new LabelNode();
                        mm.instructions.insert(ps);
                        var ptail = new InsnList();
                        ptail.add(pe);
                        ptail.add(ph);
                        ptail.add(new InsnNode(Opcodes.POP));
                        ptail.add(new InsnNode(Opcodes.RETURN));
                        mm.instructions.add(ptail);
                        mm.tryCatchBlocks.add(new TryCatchBlockNode(ps, pe, ph, 'java/lang/UnsupportedOperationException'));
                        uoe = true;
                        break;
                    }
                }
                log(uoe ? 'quark tiny-potato modelBake compute UOE-guard applied' : 'quark tiny-potato: modelBake target missing, skipped (mod updated?)');
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
        // Fix 53: minecolonies 1.1.1332 ItemFood (the base class of every minecolonies food item)
        // has an un-dist-guarded CLIENT reference -- getTooltipImage() calls
        // Minecraft.getInstance().level (a ClientLevel) for a tooltip preview. ItemFood is loaded
        // for the first time when ModItemsInitializer.init constructs ItemMilkyBread; on a DEDICATED
        // SERVER, verifying ItemFood forces ClientLevel to load -> RuntimeDistCleaner throws
        // "Attempted to load class ClientLevel for invalid dist DEDICATED_SERVER" -> minecolonies'
        // item RegisterEvent aborts mid-registration -> the item registry never finalises -> EVERY
        // item DeferredHolder stays unbound -> knightlib/simulated/spawn/aeronautics/paladins all
        // cascade "unbound value"/null-item -> total server boot crash. THIS is the true root; the
        // other "unbound" failures were victims. Neutralise getTooltipImage to return
        // Optional.empty() (removes the only Minecraft/ClientLevel reference in the class). Drops a
        // minor client tooltip-preview image; nothing functional, and the server boots.
        'uvfixes_minecolonies_itemfood_clientlevel': {
            'target': { 'type': 'CLASS', 'name': 'com.minecolonies.core.items.ItemFood' },
            'transformer': function (classNode) {
                var done = false;
                for (var i = 0; i < classNode.methods.size(); i++) {
                    var m = classNode.methods.get(i);
                    if (!m.name.equals('getTooltipImage') || !m.desc.equals('(Lnet/minecraft/world/item/ItemStack;)Ljava/util/Optional;')) continue;
                    m.instructions.clear();
                    if (m.tryCatchBlocks != null) m.tryCatchBlocks.clear();
                    if (m.localVariables != null) m.localVariables.clear();
                    m.visibleLocalVariableAnnotations = null;
                    m.invisibleLocalVariableAnnotations = null;
                    var il = new InsnList();
                    il.add(new MethodInsnNode(Opcodes.INVOKESTATIC, 'java/util/Optional', 'empty', '()Ljava/util/Optional;', false));
                    il.add(new InsnNode(Opcodes.ARETURN));
                    m.instructions.add(il);
                    m.maxStack = 1; m.maxLocals = 2;
                    done = true;
                    break;
                }
                log(done ? 'minecolonies ItemFood.getTooltipImage neutralised -> Optional.empty (removes the ClientLevel ref that aborted dedicated-server item registration; THE root fix)'
                         : 'minecolonies: ItemFood.getTooltipImage not matched (mod updated? check whether the ClientLevel leak moved)');
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
        // Fix 44: server DISCONNECTS from client<->server MOD DRIFT. When the server syncs an entity
        // whose mod set registers a SynchedEntityData field N with a DIFFERENT serializer than the
        // client has (e.g. a mod auto-updated on the client but not the server -> field 15 is Boolean
        // server-side but Integer client-side), SynchedEntityData.assignValue throws IllegalStateException
        // "Invalid entity data item type for field %d ...". That propagates out of assignValues, the
        // ClientboundSetEntityDataPacket handler fails -> "Network Protocol Error" -> the client is
        // disconnected, and re-disconnected on rejoin (the same entities reload). FIX: wrap assignValue's
        // whole body in try { ... } catch (Throwable) { return; } so an un-applyable field is SKIPPED (its
        // value just stays the client default) instead of aborting the entire entity-sync packet. Valid
        // fields in the same packet still apply (assignValues loops; each assignValue call is independent;
        // a normal matching field never reaches the handler -> behaviour unchanged). Silent at runtime by
        // design -- a mismatch can recur every entity tick, so no log spam; the boot-time
        // "[uvfixes] ... guard applied" line confirms it's installed. Client-side relief for the drift
        // symptom; the real cure is matching client+server mod versions. Does NOT cover an out-of-range
        // field id (server has MORE fields than client -> AIOOBE in assignValues itself) -- not the
        // observed case; add an assignValues per-iteration guard if that ever appears.
        'uvfixes_synched_entity_data_skip_bad_field': {
            'target': { 'type': 'CLASS', 'name': 'net.minecraft.network.syncher.SynchedEntityData' },
            'transformer': function (classNode) {
                var DESC = '(Lnet/minecraft/network/syncher/SynchedEntityData$DataItem;Lnet/minecraft/network/syncher/SynchedEntityData$DataValue;)V';
                var done = false;
                for (var i = 0; i < classNode.methods.size(); i++) {
                    var m = classNode.methods.get(i);
                    if (!m.name.equals('assignValue') || !m.desc.equals(DESC)) continue;
                    if (m.instructions.size() === 0) break;
                    var L_start = new LabelNode();
                    var L_handler = new LabelNode();
                    m.instructions.insert(L_start);             // try {  (at method head)
                    m.instructions.add(L_handler);              // } catch (Throwable t) {
                    m.instructions.add(new InsnNode(Opcodes.POP));    //   discard the exception
                    m.instructions.add(new InsnNode(Opcodes.RETURN)); //   skip this field (void)  }
                    m.tryCatchBlocks.add(new TryCatchBlockNode(L_start, L_handler, L_handler, 'java/lang/Throwable'));
                    if (m.maxStack < 2) m.maxStack = 2;
                    done = true;
                    break;
                }
                log(done ? 'SynchedEntityData.assignValue guard applied (type-mismatched entity-data field skipped, not thrown -> no Network-Protocol-Error disconnect under client/server mod drift)'
                         : 'SynchedEntityData: assignValue(DataItem,DataValue)V not found, patch skipped (MC/mappings changed?)');
                return classNode;
            }
        },
        // Fix 45: more_rpg_classes FrostedParticles.spawnParticles -> spell_engine ParticleHelper.play
        // hands a NULL ParticleOptions into ClientLevel.addParticle when a living entity carries a frost
        // status effect. addParticle then calls particle.getType() on null -> NPE, ~20x per burst. Neruina
        // catches it (no crash) but it floods STDERR every frost tick. Guard: HEAD null-check on the
        // addParticle(ParticleOptions,boolean,double*6) overload -- the chokepoint the simpler overloads
        // delegate to -- returns immediately when the ParticleOptions is null. A null particle never
        // renders, so this is a pure no-op for the broken call; every valid (non-null) particle is
        // completely unaffected. General: silences any mod that fires a null particle, not just frost.
        'uvfixes_clientlevel_skip_null_particle': {
            'target': { 'type': 'CLASS', 'name': 'net.minecraft.client.multiplayer.ClientLevel' },
            'transformer': function (classNode) {
                var DESC = '(Lnet/minecraft/core/particles/ParticleOptions;ZDDDDDD)V';
                var done = false;
                for (var i = 0; i < classNode.methods.size(); i++) {
                    var m = classNode.methods.get(i);
                    if (!m.name.equals('addParticle') || !m.desc.equals(DESC)) continue;
                    if (m.instructions.size() === 0) break;
                    var list = new InsnList();
                    var cont = new LabelNode();
                    list.add(new VarInsnNode(Opcodes.ALOAD, 1));          // ParticleOptions param0 (slot 1)
                    list.add(new JumpInsnNode(Opcodes.IFNONNULL, cont));  // non-null -> run original body
                    list.add(new InsnNode(Opcodes.RETURN));              // null -> no-op (void)
                    list.add(cont);
                    m.instructions.insert(list);                          // prepend at method head
                    if (m.maxStack < 1) m.maxStack = 1;
                    done = true;
                    break;
                }
                log(done ? 'ClientLevel.addParticle null-particle guard applied (null ParticleOptions no-ops instead of NPE -> silences more_rpg_classes/spell_engine FrostedParticles STDERR spam)'
                         : 'ClientLevel: addParticle(ParticleOptions,Z,D6)V not found, patch skipped (MC/mappings changed?)');
                return classNode;
            }
        },
        // Fix 46: structurize Blueprint "World mismatch" crash on reconnect. Blueprint.setRotationMirrorRelative
        // does `if (level.registryAccess() != this.registryAccess) throw IllegalStateException("World mismatch")`
        // -- an over-strict reference-IDENTITY check. After a disconnect+reconnect to the same server the new
        // ClientLevel's registryAccess is content-identical but a DIFFERENT object, so an active build preview
        // whose Blueprint is still bound to the dead level throws here (render thread, via
        // BlueprintPreviewData.getBlueprint -> setBlueprint -> applyRotationMirrorAndSync) -> hard client crash.
        // (uvmccache 1.1.0 already flushes ColonyBlueprintRenderer.blueprintDataCache on logout, but
        // BlueprintPreviewData is a SEPARATE stale-blueprint holder it doesn't cover.) The throw is the FIRST
        // thing the method does (before any mutation), so wrapping the body in try/catch(IllegalStateException)
        // -> return cleanly skips the rotation for that stale preview instead of crashing; the preview self-heals
        // when the player re-selects a building (a fresh Blueprint replaces the stale one). Real placement is
        // unaffected -- the check only fires on a genuine level mismatch, which now no-ops instead of crashing.
        'uvfixes_structurize_blueprint_world_mismatch_guard': {
            'target': { 'type': 'CLASS', 'name': 'com.ldtteam.structurize.blueprints.v1.Blueprint' },
            'transformer': function (classNode) {
                var DESC = '(Lcom/ldtteam/structurize/api/RotationMirror;Lnet/minecraft/world/level/Level;)V';
                var done = false;
                for (var i = 0; i < classNode.methods.size(); i++) {
                    var m = classNode.methods.get(i);
                    if (!m.name.equals('setRotationMirrorRelative') || !m.desc.equals(DESC)) continue;
                    if (m.instructions.size() === 0) break;
                    var L_start = new LabelNode();
                    var L_handler = new LabelNode();
                    m.instructions.insert(L_start);                   // try {  (method head)
                    m.instructions.add(L_handler);                    // } catch (IllegalStateException e) {
                    m.instructions.add(new InsnNode(Opcodes.POP));    //   discard the exception
                    m.instructions.add(new InsnNode(Opcodes.RETURN)); //   skip rotation for the stale preview (void) }
                    m.tryCatchBlocks.add(new TryCatchBlockNode(L_start, L_handler, L_handler, 'java/lang/IllegalStateException'));
                    if (m.maxStack < 2) m.maxStack = 2;
                    done = true;
                    break;
                }
                log(done ? 'structurize Blueprint.setRotationMirrorRelative World-mismatch guard applied (stale build-preview after reconnect no-ops instead of crashing the client)'
                         : 'structurize Blueprint: setRotationMirrorRelative(RotationMirror,Level)V not found, patch skipped (structurize changed?)');
                return classNode;
            }
        },
        // Fix 47: Fusion x Blueprint join-stall NPE. On client login, Blueprint (Team Abnormals)
        // bakes armor-trim item-model overrides (BlueprintTrims.modifyTrimmableItemModels ->
        // ModelBakery.bake) -- a LATE phase, AFTER Fusion's static atlasStitchResults map has been
        // cleared (it is only populated during the TextureAtlasStitchedEvent). Fusion's bake mixin then
        // calls the STATIC FusionBlockModelData.containsFusionModelsOrTextures(BlockModel), which does
        // `atlasStitchResults.get(...)` -> NullPointerException. NeoForge's EventBus catches it (no hard
        // crash) but it aborts the trim baking and stalls the join ~40s (ModernFix watchdog fires) ->
        // "world won't load". Guard: HEAD null-check on the static field -- when atlasStitchResults is
        // null (the late-bake window), return false ("no fusion models/textures") instead of NPE, so the
        // trim model bakes as a plain model and the join proceeds. During normal baking (right after the
        // atlas stitch) the map is non-null -> IFNONNULL falls through to the original body, zero change.
        // Pure no-op for the broken late call; correct behavior for every in-window bake.
        'uvfixes_fusion_atlasstitch_null_guard': {
            'target': { 'type': 'CLASS', 'name': 'com.supermartijn642.fusion.model.FusionBlockModelData' },
            'transformer': function (classNode) {
                var OWNER = 'com/supermartijn642/fusion/model/FusionBlockModelData';
                var DESC = '(Lnet/minecraft/client/renderer/block/model/BlockModel;)Z';
                var done = false;
                for (var i = 0; i < classNode.methods.size(); i++) {
                    var m = classNode.methods.get(i);
                    if (!m.name.equals('containsFusionModelsOrTextures') || !m.desc.equals(DESC)) continue;
                    if (m.instructions.size() === 0) break;
                    var list = new InsnList();
                    var cont = new LabelNode();
                    list.add(new FieldInsnNode(Opcodes.GETSTATIC, OWNER, 'atlasStitchResults', 'Ljava/util/Map;'));
                    list.add(new JumpInsnNode(Opcodes.IFNONNULL, cont)); // map populated -> run original body
                    list.add(new InsnNode(Opcodes.ICONST_0));            // map null -> "no fusion data"
                    list.add(new InsnNode(Opcodes.IRETURN));             //   return false (skip, no NPE)
                    list.add(cont);
                    m.instructions.insert(list);                          // prepend at method head
                    if (m.maxStack < 1) m.maxStack = 1;
                    done = true;
                    break;
                }
                log(done ? 'Fusion containsFusionModelsOrTextures atlasStitchResults null-guard applied (late Blueprint trim bake on login no longer NPEs/stalls the world join)'
                         : 'Fusion: containsFusionModelsOrTextures(BlockModel)Z not found, patch skipped (Fusion changed?)');
                return classNode;
            }
        },
        // Fix 48: DH 3.1.0-b worldgen deadlock with c2me. DH's INTERNAL_SERVER distant-generator
        // (InternalServerGenerator.requestChunkFromServerAsync) force-generates each LOD chunk to
        // ChunkStatus.FULL via ChunkHolder.scheduleChunkGenerationTask, and fires a whole batch of
        // these concurrently with NO throttle on modern MC (the limiting semaphore is gated
        // `#if MC_VER <= MC_1_12_2`). DH's own comment: "If C2ME is present the CPU will still be well
        // utilized" -- it dumps the FULL-chunk flood onto c2me and trusts c2me to absorb it. c2me's
        // 0.3.0-alpha.0.93 chunk scheduler can't, alongside player-chunk demand: a task is lost, the
        // workers go idle, the server thread parks forever in getChunk -> hard worldgen deadlock
        // (void terrain / "no chunks past spawn" / 40s->250s watchdog ticks). DH commit eb82ab14
        // (2026-06-08, shipped in 3.1.0-b) introduced this by bumping the status FEATURES -> FULL;
        // before that it generated to FEATURES and didn't deadlock. FEATURES already places
        // structures (structure pieces are placed in the features step) and DH bakes its own LOD
        // lighting, so reverting keeps distant structures + lighting -- zero graphics loss -- while
        // each chunk is far lighter so the batch drains instead of flooding c2me. We swap ONLY the
        // ChunkStatus.FULL that feeds a scheduleChunkGenerationTask/getOrScheduleFuture call (the
        // gen-request path), so no unrelated FULL use is touched. Reverts eb82ab14 at class-load,
        // no jar edit. Self-no-ops + logs if DH fixes it upstream or remaps.
        'uvfixes_dh_internalserver_features_not_full': {
            'target': { 'type': 'CLASS', 'name': 'com.seibel.distanthorizons.common.wrappers.worldGeneration.InternalServerGenerator_neoforge' },
            'transformer': function (classNode) {
                var CS = 'net/minecraft/world/level/chunk/status/ChunkStatus';
                var CSDESC = 'Lnet/minecraft/world/level/chunk/status/ChunkStatus;';
                var swapped = 0;
                for (var i = 0; i < classNode.methods.size(); i++) {
                    var m = classNode.methods.get(i);
                    var insns = m.instructions.toArray();
                    for (var j = 0; j < insns.length; j++) {
                        var insn = insns[j];
                        if (!(insn instanceof FieldInsnNode)) continue;
                        if (insn.getOpcode() !== Opcodes.GETSTATIC) continue;
                        if (!insn.owner.equals(CS) || !insn.name.equals('FULL') || !insn.desc.equals(CSDESC)) continue;
                        // only swap when this FULL feeds a chunk-generation schedule call (the gen-request
                        // path) -- never an unrelated ChunkStatus.FULL use.
                        var feedsGen = false;
                        for (var k = j + 1; k < insns.length && k < j + 15; k++) {
                            var nx = insns[k];
                            if (nx instanceof MethodInsnNode
                                    && (nx.name.equals('scheduleChunkGenerationTask') || nx.name.equals('getOrScheduleFuture'))) {
                                feedsGen = true; break;
                            }
                        }
                        if (feedsGen) { insn.name = 'FEATURES'; swapped++; }
                    }
                }
                log(swapped > 0
                    ? 'DH InternalServerGenerator: reverted ChunkStatus.FULL -> FEATURES on the internal-server chunk request (x' + swapped + ') -- undoes DH eb82ab14; keeps distant structures, stops the FULL-chunk batch flooding/deadlocking c2me'
                    : 'DH InternalServerGenerator: FULL gen-request not found, patch skipped (DH reverted eb82ab14 upstream, or class/mappings changed)');
                return classNode;
            }
        },
        // Fix 49 -- DH gen-ticket priority. Companion to Fix 48. DH adds its background gen
        // ticket at chunk LEVEL 33 (== FULL) in BOTH the request (addTicket) and release
        // (removeTicket) lambdas of InternalServerGenerator. Level 33 puts DH's distant chunks
        // at the SAME priority as the player's own view-distance chunks, so on a fresh world
        // DH's huge volume starves the player in the c2me queue ("spawn loads, nothing past it",
        // server thread parks forever in ServerChunkCache.getChunk -> 40s..300s watchdog). It
        // also forces FULL generation independently of Fix 48's schedule swap. Bumping BOTH
        // ticket sites 33 -> 34: (a) deprioritises DH below every player chunk (all <= 33) so
        // the player's chunks always win, DH backfills with spare worker capacity; (b) caps the
        // chunk at INITIALIZE_LIGHT (one past FEATURES) -- keeps features + structures, drops
        // only the FULL lighting/spawn finalise that DH bakes itself = zero graphics loss.
        // add + remove are bumped together so the ticket is still removed (no leak).
        'uvfixes_dh_internalserver_gen_ticket_level': {
            'target': { 'type': 'CLASS', 'name': 'com.seibel.distanthorizons.common.wrappers.worldGeneration.InternalServerGenerator_neoforge' },
            'transformer': function (classNode) {
                var swapped = 0;
                for (var i = 0; i < classNode.methods.size(); i++) {
                    var m = classNode.methods.get(i);
                    var insns = m.instructions.toArray();
                    // only the two ticket lambdas -- methods that actually call add/removeTicket
                    var ticketsHere = false;
                    for (var t = 0; t < insns.length; t++) {
                        var ti = insns[t];
                        if (ti instanceof MethodInsnNode
                                && (ti.name.equals('addTicket') || ti.name.equals('removeTicket'))) { ticketsHere = true; break; }
                    }
                    if (!ticketsHere) continue;
                    for (var j = 0; j + 1 < insns.length; j++) {
                        var insn = insns[j];
                        if (insn.getOpcode() !== Opcodes.BIPUSH) continue;
                        if (insn.operand !== 33) continue;                       // the level constant
                        if (insns[j + 1].getOpcode() !== Opcodes.ISTORE) continue; // stored as the level local
                        insn.operand = 34; swapped++;
                    }
                }
                log(swapped > 0
                    ? 'DH InternalServerGenerator: bumped gen-ticket level 33 -> 34 (x' + swapped + ') -- DH distant gen now yields to player chunks (no starvation) + caps at initialize_light (keeps features/structures)'
                    : 'DH InternalServerGenerator: gen-ticket level-33 site not found, patch skipped (DH internals changed)');
                return classNode;
            }
        },
        // Fix 50: CIT Resewn's brokenpaths probe (AbstractFileResourcePackMixin, @Inject TAIL of
        // PackResources.getMetadataSection) loops namespaces calling listResources(type, ns, "", noop)
        // with an EMPTY path-prefix. For folder packs FileUtil.decomposePath("") -> DataResult.error ->
        // 'Invalid path : Invalid path ' logged 1337x/boot (91% of all error spam). decomposePath("/") ->
        // success(emptyList) -> walks the namespace root identically; the no-op consumer discards results
        // exactly as before -- a TRUE fix (the probe still completes), not a mask. Rewrite the "" prefix LDC
        // -> "/" in the mixin class BEFORE Mixin merges it into every pack class so the corrected constant
        // propagates. (NOT Veil -- its empty-prefix site is dead code for these packs; verifier-corrected.)
        'uvfixes_citresewn_brokenpaths_empty_prefix': {
            'target': { 'type': 'CLASS', 'name': 'schm.shsupercm.citresewn.mixin.AbstractFileResourcePackMixin' },
            'transformer': function (classNode) {
                var hits = 0;
                for (var i = 0; i < classNode.methods.size(); i++) {
                    var m = classNode.methods.get(i);
                    if (!m.name.equals('citresewn$brokenpaths$parseMetadata')) continue;
                    var insns = m.instructions.toArray();
                    for (var j = 0; j < insns.length; j++) {
                        var insn = insns[j];
                        if (insn instanceof LdcInsnNode && insn.cst.equals('')) {
                            insn.cst = '/';
                            hits++;
                        }
                    }
                }
                log(hits > 0 ? 'citresewn AbstractFileResourcePackMixin brokenpaths empty listResources prefix -> "/" (' + hits + ' sites)' : 'citresewn AbstractFileResourcePackMixin: 0 empty-prefix sites (citresewn updated?)');
                return classNode;
            }
        },
        // Fix 51: ItemStack.parse logs 'Tried to load invalid item: {}' at ERROR for every baked structure
        // air-slot (65/boot) and removed-content ref (apotheosis:long_sundering potion). The CODEC recovery
        // is unchanged (resultOrPartial still returns the partial/EMPTY -> empty slot / plain arrow); only the
        // cosmetic ERROR line is spurious -- the data genuinely refs absent content across 39 structure mods,
        // nothing fixable exists to point them at. Suppress just the log by returning at the head of the
        // error-log lambda. Matched robustly (lambda index drifts across MC patches): name startsWith
        // lambda$parse$ + desc (String)V + body LDCs the exact message string.
        'uvfixes_itemstack_invalid_item_log': {
            'target': { 'type': 'CLASS', 'name': 'net.minecraft.world.item.ItemStack' },
            'transformer': function (classNode) {
                var done = false;
                var MSG = "Tried to load invalid item: '{}'";
                for (var i = 0; i < classNode.methods.size(); i++) {
                    var m = classNode.methods.get(i);
                    if (!(m.name.startsWith('lambda$parse$') && m.desc.equals('(Ljava/lang/String;)V'))) continue;
                    var ok = false;
                    var insns = m.instructions.toArray();
                    for (var j = 0; j < insns.length; j++) {
                        if (insns[j] instanceof LdcInsnNode && insns[j].cst.equals(MSG)) { ok = true; break; }
                    }
                    if (!ok) continue;
                    m.instructions.insert(new InsnNode(Opcodes.RETURN));
                    done = true;
                    break;
                }
                log(done ? 'itemstack invalid-item log suppressed (baked structure air/removed-potion slots; CODEC recovery unchanged)' : 'itemstack: lambda$parse$ invalid-item log not found, patch skipped (mod updated?)');
                return classNode;
            }
        },
        // Fix 52: AllTheLeaks 1.1.9 UntrackedIssue001 hard-references supplementaries ColoredMapHandler
        // (REMOVED in supplementaries 3.7.4); its open versionRange [1.21-3.1.8,) runs it anyway -> the
        // <clinit> ReflectionHelper.getMethodFromClass(ColoredMapHandler,...) throws -> ExceptionInInitializer
        // 'Failed to instantiate constructor' (the whole leak-fix silently never applies). Remove the two
        // ColoredMapHandler refs: (A) the direct clearIdCache()V invokestatic in clearRemaining, and (B) the
        // <clinit> reflection-lookup block (anchor `ldc class ColoredMapHandler` through its `astore_0`; the
        // resolved handle is stored to a write-only discarded local, so excision leaves valid bytecode). The
        // other two clears (WeatheredMapRecipe, EndermanSkullBlockTile) stay -> the leak-fix initialises +
        // runs its still-valid parts. Revert when AllTheLeaks drops/guards the ref.
        'uvfixes_alltheleaks_coloredmaphandler': {
            'target': { 'type': 'CLASS', 'name': 'dev.uncandango.alltheleaks.leaks.common.mods.supplementaries.UntrackedIssue001' },
            'transformer': function (classNode) {
                var removed = 0;
                var CMH = 'net/mehvahdjukaar/supplementaries/common/misc/map_data/ColoredMapHandler';
                for (var i = 0; i < classNode.methods.size(); i++) {
                    var m = classNode.methods.get(i);
                    if (m.name.equals('clearRemaining') && m.desc.equals('(Lnet/neoforged/neoforge/event/server/ServerStoppedEvent;)V')) {
                        var insnsA = m.instructions.toArray();
                        for (var a = 0; a < insnsA.length; a++) {
                            var ia = insnsA[a];
                            if (ia instanceof MethodInsnNode && ia.getOpcode() === Opcodes.INVOKESTATIC
                                && ia.owner.equals(CMH) && ia.name.equals('clearIdCache') && ia.desc.equals('()V')) {
                                m.instructions.remove(ia);
                                removed++;
                            }
                        }
                    }
                    if (m.name.equals('<clinit>') && m.desc.equals('()V')) {
                        var insnsB = m.instructions.toArray();
                        for (var b = 0; b < insnsB.length; b++) {
                            var ib = insnsB[b];
                            if (ib instanceof LdcInsnNode && ib.cst instanceof AsmType
                                && ib.cst.getInternalName().equals(CMH)) {
                                var seq = [];
                                var cur = ib;
                                var foundStore = false;
                                for (var c = 0; c < 12 && cur !== null; c++) {
                                    seq.push(cur);
                                    if (cur instanceof VarInsnNode && cur.getOpcode() === Opcodes.ASTORE) { foundStore = true; break; }
                                    cur = cur.getNext();
                                }
                                if (foundStore) {
                                    for (var r = 0; r < seq.length; r++) { m.instructions.remove(seq[r]); removed++; }
                                }
                                break;
                            }
                        }
                    }
                }
                log(removed > 0 ? 'alltheleaks UntrackedIssue001 ColoredMapHandler refs removed (' + removed + ' insns; ran on supp 3.7.4 where ColoredMapHandler was removed)' : 'alltheleaks UntrackedIssue001: ColoredMapHandler refs not found (0) -- AllTheLeaks or Supplementaries updated? auto-disarm');
                return classNode;
            }
        },
    };

    // Fix 54 (cont.): register the require=0 graceful-degradation transformer for every
    // minecolonies-targeting mixin in MineColonies_Tweaks 3.30 + MineColonies_Compatibility 3.51.
    // Listed exhaustively (enumerated from both mods' mixin configs by ScanTweaks.java) so a snapshot
    // break in ANY of them no-ops instead of boot-looping the server -- not just the ~20 currently
    // confirmed broken. Optionalising an already-resolving injector is a no-op (require is a floor).
    var UV_MC_ADDON_MIXINS = [
        // MineColonies_Compatibility 3.51 (35)
        'steve_gall.minecolonies_compatibility.mixin.client.minecolonies.AbstractModuleWindowAccessor',
        'steve_gall.minecolonies_compatibility.mixin.client.minecolonies.SettingsModuleViewMixin',
        'steve_gall.minecolonies_compatibility.mixin.client.minecolonies.SettingsModuleWindow1Mixin',
        'steve_gall.minecolonies_compatibility.mixin.client.minecolonies.WindowCraftingMixin',
        'steve_gall.minecolonies_compatibility.mixin.client.minecolonies.WindowListRecipes1Mixin',
        'steve_gall.minecolonies_compatibility.mixin.client.minecolonies.WindowListRecipesAcccessor',
        'steve_gall.minecolonies_compatibility.mixin.common.minecolonies.AbstractBuildingGuardsMixin',
        'steve_gall.minecolonies_compatibility.mixin.common.minecolonies.AbstractEntityAIBasicMixin',
        'steve_gall.minecolonies_compatibility.mixin.common.minecolonies.AbstractEntityAICraftingAccessor',
        'steve_gall.minecolonies_compatibility.mixin.common.minecolonies.AbstractEntityAICraftingMixin',
        'steve_gall.minecolonies_compatibility.mixin.common.minecolonies.AbstractEntityAIFightMixin',
        'steve_gall.minecolonies_compatibility.mixin.common.minecolonies.AbstractEntityAIHerderMixin',
        'steve_gall.minecolonies_compatibility.mixin.common.minecolonies.AbstractWarehouseRequestResolverMixin',
        'steve_gall.minecolonies_compatibility.mixin.common.minecolonies.AnimalHerdingModuleMixin',
        'steve_gall.minecolonies_compatibility.mixin.common.minecolonies.AttackMoveAIMixin',
        'steve_gall.minecolonies_compatibility.mixin.common.minecolonies.BuildingEntryMixin',
        'steve_gall.minecolonies_compatibility.mixin.common.minecolonies.CompatibilityManagerMixin',
        'steve_gall.minecolonies_compatibility.mixin.common.minecolonies.ContainerCraftingMixin',
        'steve_gall.minecolonies_compatibility.mixin.common.minecolonies.EntityAIArcherTrainingMixin',
        'steve_gall.minecolonies_compatibility.mixin.common.minecolonies.EntityAICombatTrainingMixin',
        'steve_gall.minecolonies_compatibility.mixin.common.minecolonies.EntityAIKnightMixin',
        'steve_gall.minecolonies_compatibility.mixin.common.minecolonies.EntityAIRangerMixin',
        'steve_gall.minecolonies_compatibility.mixin.common.minecolonies.EntityAIWorkBlacksmithMixin',
        'steve_gall.minecolonies_compatibility.mixin.common.minecolonies.EntityAIWorkDeliverymanMixin',
        'steve_gall.minecolonies_compatibility.mixin.common.minecolonies.EntityAIWorkFarmerMixin',
        'steve_gall.minecolonies_compatibility.mixin.common.minecolonies.EquipmentTypeEntryMixin',
        'steve_gall.minecolonies_compatibility.mixin.common.minecolonies.GenericRecipeCategoryMixin',
        'steve_gall.minecolonies_compatibility.mixin.common.minecolonies.ItemStackUtilsMixin',
        'steve_gall.minecolonies_compatibility.mixin.common.minecolonies.KnightCombatAIMixin',
        'steve_gall.minecolonies_compatibility.mixin.common.minecolonies.PrivateCraftingTeachingTransferHandlerMixin',
        'steve_gall.minecolonies_compatibility.mixin.common.minecolonies.PrivateWorkerCraftingRequestResolverMixin',
        'steve_gall.minecolonies_compatibility.mixin.common.minecolonies.RangerCombatAIMixin',
        'steve_gall.minecolonies_compatibility.mixin.common.minecolonies.RecipeStorageMixin',
        'steve_gall.minecolonies_compatibility.mixin.common.minecolonies.TileEntityWareHouseMixin',
        'steve_gall.minecolonies_compatibility.mixin.common.minecolonies.TinkersToolHelperMixin',
        // MineColonies_Tweaks 3.30 (74)
        'steve_gall.minecolonies_tweaks.mixin.client.minecolonies.AbstractBuildingMainWindowMixin',
        'steve_gall.minecolonies_tweaks.mixin.client.minecolonies.AbstractWindowSkeletonMixin',
        'steve_gall.minecolonies_tweaks.mixin.client.minecolonies.AbstractWindowSkeletonsMixin',
        'steve_gall.minecolonies_tweaks.mixin.client.minecolonies.ColonyBlueprintRendererBuildGogglesMixin',
        'steve_gall.minecolonies_tweaks.mixin.client.minecolonies.ItemListModuleWindowMixin',
        'steve_gall.minecolonies_tweaks.mixin.client.minecolonies.MainWindowCitizenMixin',
        'steve_gall.minecolonies_tweaks.mixin.client.minecolonies.RestaurantMenuModuleWindow1Mixin',
        'steve_gall.minecolonies_tweaks.mixin.client.minecolonies.RestaurantMenuModuleWindow2Mixin',
        'steve_gall.minecolonies_tweaks.mixin.client.minecolonies.RestaurantMenuModuleWindowMixin',
        'steve_gall.minecolonies_tweaks.mixin.client.minecolonies.TabsWindowModuleMixin',
        'steve_gall.minecolonies_tweaks.mixin.client.minecolonies.TileEntityScarecrowRendererMixin',
        'steve_gall.minecolonies_tweaks.mixin.client.minecolonies.ToolRecipeCategoryMixin',
        'steve_gall.minecolonies_tweaks.mixin.client.minecolonies.TownhallWindowMainPageMixin',
        'steve_gall.minecolonies_tweaks.mixin.client.minecolonies.WindowCraftingsMixin',
        'steve_gall.minecolonies_tweaks.mixin.client.minecolonies.WindowFieldMixin',
        'steve_gall.minecolonies_tweaks.mixin.client.minecolonies.WindowHutAllInventoryMixin',
        'steve_gall.minecolonies_tweaks.mixin.client.minecolonies.WindowInventoriesMixin',
        'steve_gall.minecolonies_tweaks.mixin.client.minecolonies.WindowResearchTreeMixin',
        'steve_gall.minecolonies_tweaks.mixin.common.minecolonies.AbstractBuildingMixin',
        'steve_gall.minecolonies_tweaks.mixin.common.minecolonies.AbstractEntityAICraftingAccessor',
        'steve_gall.minecolonies_tweaks.mixin.common.minecolonies.AbstractEntityAICraftingMixin',
        'steve_gall.minecolonies_tweaks.mixin.common.minecolonies.AbstractEntityAIInteractMixin',
        'steve_gall.minecolonies_tweaks.mixin.common.minecolonies.AbstractEntityAIStructureAccessor',
        'steve_gall.minecolonies_tweaks.mixin.common.minecolonies.AbstractEntityAIStructureMixin',
        'steve_gall.minecolonies_tweaks.mixin.common.minecolonies.AbstractEntityMinecoloniesRaiderMixin',
        'steve_gall.minecolonies_tweaks.mixin.common.minecolonies.AbstractTileEntityRackMixin',
        'steve_gall.minecolonies_tweaks.mixin.common.minecolonies.BuildingDyerCraftingModuleMixin',
        'steve_gall.minecolonies_tweaks.mixin.common.minecolonies.BuildingExtensionsModuleMixin',
        'steve_gall.minecolonies_tweaks.mixin.common.minecolonies.BuildingStructureHandlerMixin',
        'steve_gall.minecolonies_tweaks.mixin.common.minecolonies.CitizenDataMixin',
        'steve_gall.minecolonies_tweaks.mixin.common.minecolonies.CitizenDiseaseHandlerAccessor',
        'steve_gall.minecolonies_tweaks.mixin.common.minecolonies.CitizenFoodHandlerMixin',
        'steve_gall.minecolonies_tweaks.mixin.common.minecolonies.CitizenMournHandlerMixin',
        'steve_gall.minecolonies_tweaks.mixin.common.minecolonies.ColonyMixin',
        'steve_gall.minecolonies_tweaks.mixin.common.minecolonies.CompatibilityManagerMixin',
        'steve_gall.minecolonies_tweaks.mixin.common.minecolonies.CourierAssignmentModuleMixin',
        'steve_gall.minecolonies_tweaks.mixin.common.minecolonies.CourierAssignmentModuleViewMixin',
        'steve_gall.minecolonies_tweaks.mixin.common.minecolonies.CreativeBuildingStructureHandlerMixin',
        'steve_gall.minecolonies_tweaks.mixin.common.minecolonies.EntityAIStructureBuilderAccessor',
        'steve_gall.minecolonies_tweaks.mixin.common.minecolonies.EntityAIStudyMixin',
        'steve_gall.minecolonies_tweaks.mixin.common.minecolonies.EntityAIWorkCookMixin',
        'steve_gall.minecolonies_tweaks.mixin.common.minecolonies.EntityAIWorkFarmerAccessor',
        'steve_gall.minecolonies_tweaks.mixin.common.minecolonies.EntityAIWorkFarmerMixin',
        'steve_gall.minecolonies_tweaks.mixin.common.minecolonies.EntityAIWorkLumberjackMixin',
        'steve_gall.minecolonies_tweaks.mixin.common.minecolonies.EntityAIWorkSifterAccessor',
        'steve_gall.minecolonies_tweaks.mixin.common.minecolonies.EntityAIWorkSifterMixin',
        'steve_gall.minecolonies_tweaks.mixin.common.minecolonies.EntityAIWorkUndertakerMixin',
        'steve_gall.minecolonies_tweaks.mixin.common.minecolonies.EntityCitizenMixin',
        'steve_gall.minecolonies_tweaks.mixin.common.minecolonies.EquipmentTypeEntryMixin',
        'steve_gall.minecolonies_tweaks.mixin.common.minecolonies.FoodUtilsMixin',
        'steve_gall.minecolonies_tweaks.mixin.common.minecolonies.GlobalResearchBranchMixin',
        'steve_gall.minecolonies_tweaks.mixin.common.minecolonies.GlobalResearchEffectMixin',
        'steve_gall.minecolonies_tweaks.mixin.common.minecolonies.ItemClipboardAccessor',
        'steve_gall.minecolonies_tweaks.mixin.common.minecolonies.ItemColonyMapAccessor',
        'steve_gall.minecolonies_tweaks.mixin.common.minecolonies.ItemCropMixin',
        'steve_gall.minecolonies_tweaks.mixin.common.minecolonies.ItemListModuleViewAccessor',
        'steve_gall.minecolonies_tweaks.mixin.common.minecolonies.ItemQuestLogAccessor',
        'steve_gall.minecolonies_tweaks.mixin.common.minecolonies.ItemResourceScrollAccessor',
        'steve_gall.minecolonies_tweaks.mixin.common.minecolonies.ItemStackUtilsMixin',
        'steve_gall.minecolonies_tweaks.mixin.common.minecolonies.LoadOnlyStructureHandlerMixin',
        'steve_gall.minecolonies_tweaks.mixin.common.minecolonies.LocalResearchTreeMixin',
        'steve_gall.minecolonies_tweaks.mixin.common.minecolonies.MinecoloniesCropBlockMixin',
        'steve_gall.minecolonies_tweaks.mixin.common.minecolonies.PostBoxRequestMessageMixin',
        'steve_gall.minecolonies_tweaks.mixin.common.minecolonies.RecipeStorageMixin',
        'steve_gall.minecolonies_tweaks.mixin.common.minecolonies.RegisteredStructureManagerViewMixin',
        'steve_gall.minecolonies_tweaks.mixin.common.minecolonies.ResearchEffectCategoryMixin',
        'steve_gall.minecolonies_tweaks.mixin.common.minecolonies.ResearchEffectManagerMixin',
        'steve_gall.minecolonies_tweaks.mixin.common.minecolonies.ResearchListenerMixin',
        'steve_gall.minecolonies_tweaks.mixin.common.minecolonies.ResearchManagerMixin',
        'steve_gall.minecolonies_tweaks.mixin.common.minecolonies.RestaurantMenuModuleMixin',
        'steve_gall.minecolonies_tweaks.mixin.common.minecolonies.RestaurantMenuModuleViewMixin',
        'steve_gall.minecolonies_tweaks.mixin.common.minecolonies.StackMixin',
        'steve_gall.minecolonies_tweaks.mixin.common.minecolonies.TreeMixin',
        'steve_gall.minecolonies_tweaks.mixin.common.minecolonies.TryResearchMessageMixin'
    ];
    for (var uvi = 0; uvi < UV_MC_ADDON_MIXINS.length; uvi++) {
        (function (fqcn) {
            UVMAP['uvfixes_mcaddon_optional_' + fqcn.split('.').join('_')] = {
                'target': { 'type': 'CLASS', 'name': fqcn },
                'transformer': function (classNode) {
                    return uvOptionalizeInjectors(classNode, fqcn.substring(fqcn.lastIndexOf('.') + 1));
                }
            };
        })(UV_MC_ADDON_MIXINS[uvi]);
    }

    // Fix 61: GENERAL duplicate-enum-name crash guard (recurring incompat class). A mis-packaged multi-loader
    // mod (e.g. hybrid_birds, which adds MobCategory spawn-groups via BOTH the native NeoForge
    // enumextensions.json AND a Forge-style $VALUES-append mixin), or two mods registering an enum constant
    // with the same getSerializedName, makes StringRepresentable.createNameLookup's Collectors.toMap throw
    // "Duplicate key ..." during Bootstrap -> the whole pack fails to load before the window opens. Make the
    // name-lookup tolerant: de-dupe the input array by serialized name (keep-first) at method head, so the
    // duplicate is skipped instead of crashing. Vanilla target = mojmap at runtime (NeoForge 1.21.1), no SRG.
    UVMAP['uvfixes_stringrepresentable_dedupe_namelookup'] = {
        'target': { 'type': 'CLASS', 'name': 'net.minecraft.util.StringRepresentable' },
        'transformer': function (classNode) {
            var MethodNode = Java.type('org.objectweb.asm.tree.MethodNode');
            var IincInsnNode = Java.type('org.objectweb.asm.tree.IincInsnNode');
            var SR = 'net/minecraft/util/StringRepresentable';
            var HELPER = 'wnl$dedupeByName';
            var HELPER_DESC = '([L' + SR + ';Ljava/util/function/Function;)[L' + SR + ';';
            // ---- add helper: StringRepresentable[] wnl$dedupeByName(StringRepresentable[] values, Function nameFn) ----
            var mn = new MethodNode(Opcodes.ACC_PUBLIC | Opcodes.ACC_STATIC, HELPER, HELPER_DESC, null, null);
            var ins = mn.instructions;
            var loop = new LabelNode(), end = new LabelNode(), skip = new LabelNode();
            ins.add(new TypeInsnNode(Opcodes.NEW, 'java/util/ArrayList'));
            ins.add(new InsnNode(Opcodes.DUP));
            ins.add(new MethodInsnNode(Opcodes.INVOKESPECIAL, 'java/util/ArrayList', '<init>', '()V', false));
            ins.add(new VarInsnNode(Opcodes.ASTORE, 2));                 // list
            ins.add(new TypeInsnNode(Opcodes.NEW, 'java/util/HashSet'));
            ins.add(new InsnNode(Opcodes.DUP));
            ins.add(new MethodInsnNode(Opcodes.INVOKESPECIAL, 'java/util/HashSet', '<init>', '()V', false));
            ins.add(new VarInsnNode(Opcodes.ASTORE, 3));                 // seen
            ins.add(new InsnNode(Opcodes.ICONST_0));
            ins.add(new VarInsnNode(Opcodes.ISTORE, 4));                 // i = 0
            ins.add(loop);
            ins.add(new VarInsnNode(Opcodes.ILOAD, 4));
            ins.add(new VarInsnNode(Opcodes.ALOAD, 0));
            ins.add(new InsnNode(Opcodes.ARRAYLENGTH));
            ins.add(new JumpInsnNode(Opcodes.IF_ICMPGE, end));           // if i >= values.length -> end
            ins.add(new VarInsnNode(Opcodes.ALOAD, 0));
            ins.add(new VarInsnNode(Opcodes.ILOAD, 4));
            ins.add(new InsnNode(Opcodes.AALOAD));
            ins.add(new VarInsnNode(Opcodes.ASTORE, 5));                 // v = values[i]
            ins.add(new VarInsnNode(Opcodes.ALOAD, 1));                  // nameFn
            ins.add(new VarInsnNode(Opcodes.ALOAD, 5));
            ins.add(new MethodInsnNode(Opcodes.INVOKEINTERFACE, SR, 'getSerializedName', '()Ljava/lang/String;', true));
            ins.add(new MethodInsnNode(Opcodes.INVOKEINTERFACE, 'java/util/function/Function', 'apply', '(Ljava/lang/Object;)Ljava/lang/Object;', true));
            ins.add(new VarInsnNode(Opcodes.ASTORE, 6));                 // key = nameFn.apply(v.getSerializedName())
            ins.add(new VarInsnNode(Opcodes.ALOAD, 3));
            ins.add(new VarInsnNode(Opcodes.ALOAD, 6));
            ins.add(new MethodInsnNode(Opcodes.INVOKEINTERFACE, 'java/util/Set', 'add', '(Ljava/lang/Object;)Z', true));
            ins.add(new JumpInsnNode(Opcodes.IFEQ, skip));               // if !seen.add(key) -> skip
            ins.add(new VarInsnNode(Opcodes.ALOAD, 2));
            ins.add(new VarInsnNode(Opcodes.ALOAD, 5));
            ins.add(new MethodInsnNode(Opcodes.INVOKEINTERFACE, 'java/util/List', 'add', '(Ljava/lang/Object;)Z', true));
            ins.add(new InsnNode(Opcodes.POP));                          // list.add(v)
            ins.add(skip);
            ins.add(new IincInsnNode(4, 1));                            // i++
            ins.add(new JumpInsnNode(Opcodes.GOTO, loop));
            ins.add(end);
            ins.add(new VarInsnNode(Opcodes.ALOAD, 2));
            ins.add(new InsnNode(Opcodes.ICONST_0));
            ins.add(new TypeInsnNode(Opcodes.ANEWARRAY, SR));
            ins.add(new MethodInsnNode(Opcodes.INVOKEINTERFACE, 'java/util/List', 'toArray', '([Ljava/lang/Object;)[Ljava/lang/Object;', true));
            ins.add(new TypeInsnNode(Opcodes.CHECKCAST, '[L' + SR + ';'));
            ins.add(new InsnNode(Opcodes.ARETURN));                      // return (SR[]) list.toArray(new SR[0])
            classNode.methods.add(mn);
            // ---- insert at HEAD of createNameLookup: values = wnl$dedupeByName(values, nameFn) ----
            var done = false;
            for (var i = 0; i < classNode.methods.size(); i++) {
                var m = classNode.methods.get(i);
                if (m.name.equals('createNameLookup') && m.desc.equals('([L' + SR + ';Ljava/util/function/Function;)Ljava/util/function/Function;')) {
                    var head = new InsnList();
                    head.add(new VarInsnNode(Opcodes.ALOAD, 0));
                    head.add(new VarInsnNode(Opcodes.ALOAD, 1));
                    head.add(new MethodInsnNode(Opcodes.INVOKESTATIC, SR, HELPER, HELPER_DESC, true)); // itf=true: StringRepresentable is an interface
                    head.add(new VarInsnNode(Opcodes.ASTORE, 0));
                    m.instructions.insert(head);
                    done = true; break;
                }
            }
            log(done ? 'StringRepresentable.createNameLookup de-dupes enum names (keep-first) -> duplicate-enum-name crash class guarded (e.g. hybrid_birds MobCategory terrestrial_bird)' : 'StringRepresentable: createNameLookup not found, skipped (MC changed?)');
            return classNode;
        }
    };

    // Fix 62: jearchaeology x dungeon_difficulty player-JOIN DEADLOCK (confirmed hard-stuck: identical park
    // addr across dumps, all 14 c2me workers idle, world never loads). jearchaeology JEArchaeology$Events
    // .onDataSync fires when a player joins -> Helper.getAllBrushingRecipes ROLLS every brushing recipe's loot
    // table. Those tables carry dungeon_difficulty's LocalScalingLootFunction -> ItemScaling.scale ->
    // PatternMatching.getDifficultyResult -> LocationData.matches(Filters, ServerLevel), which runs a BLOCKING
    // StructureManager.startsForStructure(ChunkPos, Predicate) -> Level.getChunk(FULL, load=true) on the Server
    // thread. At login the spawn chunk isn't FULL yet + c2me can't service it (main thread parked) -> permanent
    // park in PlayerList.placeNewPlayer. Same blocking-main-thread-getChunk-under-c2me class as Fix 26 / Fix 60
    // / the byepregen FasterGetChunk deadlock. FIX (nothing breaks): gate the structure lookup on a NON-blocking
    // ServerLevel.hasChunkAt(this.position) -- inserted right before the startsForStructure block, after the
    // match flag is reset to false; if the chunk isn't loaded, IFEQ jumps to the result builder so the zone
    // reads as 'no structure match' (flag already false). Real gameplay (mob drops / chests) always has the
    // chunk loaded -> full structure scaling UNCHANGED; only the join-time enumeration (which has no real
    // location to scale to anyway) skips it. hasChunkAt -> getChunk(FULL, create=false) is non-blocking;
    // dungeon_difficulty is mojmap at runtime and already invokevirtuals a LevelReader default (getBiome) on
    // ServerLevel, so hasChunkAt resolves identically. Self-no-ops with a log line if the mod moves the seam.
    UVMAP['uvfixes_dungeondiff_nonblocking_structure_lookup'] = {
        'target': { 'type': 'CLASS', 'name': 'net.dungeon_difficulty.logic.PatternMatching$LocationData' },
        'transformer': function (classNode) {
            var SELF = classNode.name;                              // net/dungeon_difficulty/logic/PatternMatching$LocationData
            var MATCH_DESC = '(Lnet/dungeon_difficulty/config/Config$Zone$Filters;Lnet/minecraft/server/level/ServerLevel;)Lnet/dungeon_difficulty/logic/PatternMatching$LocationData$Match;';
            var status = 'method-not-found';
            for (var i = 0; i < classNode.methods.size(); i++) {
                var m = classNode.methods.get(i);
                if (!(m.name.equals('matches') && m.desc.equals(MATCH_DESC))) continue;
                // anchors: the ServerLevel.structureManager() call (start of the blocking structure block) +
                // the inline `new ...Match` (the result builder all skip-branches converge on).
                var smCall = null, newMatch = null;
                var arr = m.instructions.toArray();
                for (var j = 0; j < arr.length; j++) {
                    var insn = arr[j];
                    if (insn instanceof MethodInsnNode && insn.getOpcode() == Opcodes.INVOKEVIRTUAL
                            && insn.owner.equals('net/minecraft/server/level/ServerLevel')
                            && insn.name.equals('structureManager')) smCall = insn;
                    if (insn instanceof TypeInsnNode && insn.getOpcode() == Opcodes.NEW
                            && insn.desc.equals('net/dungeon_difficulty/logic/PatternMatching$LocationData$Match')) newMatch = insn;
                }
                if (smCall == null || newMatch == null) { status = 'anchors-not-found'; break; }
                // receiver ALOAD of structureManager() = the (clean-stack) point to insert the guard before
                var aload = smCall.getPrevious();
                while (aload != null && !(aload instanceof VarInsnNode && aload.getOpcode() == Opcodes.ALOAD)) aload = aload.getPrevious();
                // skip target = the LabelNode just before the inline `new Match` (the convergence label)
                var lEnd = newMatch.getPrevious();
                while (lEnd != null && !(lEnd instanceof LabelNode)) lEnd = lEnd.getPrevious();
                if (aload == null || lEnd == null) { status = 'insertion-points-not-found'; break; }
                var g = new InsnList();
                g.add(new VarInsnNode(Opcodes.ALOAD, 2));                                   // ServerLevel
                g.add(new VarInsnNode(Opcodes.ALOAD, 0));                                   // this
                g.add(new FieldInsnNode(Opcodes.GETFIELD, SELF, 'position', 'Lnet/minecraft/core/BlockPos;'));
                g.add(new MethodInsnNode(Opcodes.INVOKEVIRTUAL, 'net/minecraft/server/level/ServerLevel', 'hasChunkAt', '(Lnet/minecraft/core/BlockPos;)Z', false));
                g.add(new JumpInsnNode(Opcodes.IFEQ, lEnd));                                 // chunk not loaded -> skip structure lookup (match stays false)
                m.instructions.insertBefore(aload, g);
                status = 'patched';
                break;
            }
            log(status == 'patched'
                ? 'dungeon_difficulty LocationData.matches: structure lookup gated on non-blocking hasChunkAt -- kills the jearchaeology join-time startsForStructure deadlock (structure scaling preserved when chunk is loaded)'
                : ('dungeon_difficulty: LocationData.matches structure guard NOT applied (' + status + '), skipped (mod updated?)'));
            return classNode;
        }
    };

    return UVMAP;
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
