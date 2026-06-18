package dev.uvfixes;

import cpw.mods.modlauncher.api.ITransformer;
import cpw.mods.modlauncher.api.ITransformerVotingContext;
import cpw.mods.modlauncher.api.TargetType;
import cpw.mods.modlauncher.api.TransformerVoteResult;
import org.objectweb.asm.Opcodes;
import org.objectweb.asm.Type;
import org.objectweb.asm.tree.AbstractInsnNode;
import org.objectweb.asm.tree.ClassNode;
import org.objectweb.asm.tree.FieldInsnNode;
import org.objectweb.asm.tree.InsnList;
import org.objectweb.asm.tree.InsnNode;
import org.objectweb.asm.tree.JumpInsnNode;
import org.objectweb.asm.tree.LabelNode;
import org.objectweb.asm.tree.LdcInsnNode;
import org.objectweb.asm.tree.MethodInsnNode;
import org.objectweb.asm.tree.MethodNode;
import org.objectweb.asm.tree.TryCatchBlockNode;
import org.objectweb.asm.tree.TypeInsnNode;
import org.objectweb.asm.tree.VarInsnNode;

import java.util.Set;

/**
 * Ultimate Vibes pack fixes, applied at class-load time so the original mod
 * jars stay untouched and mod updates keep working (each patch no-ops with a
 * log line if its target method is missing).
 *
 * Fix 1 (Quark 4.1-480): TinyPotatoModule$Client uses Map.compute and wraps a
 *   null model when a resource pack breaks the tiny potato model, which later
 *   NPEs in Continuity's model wrapping. Guard: null in -> null out.
 * Fix 2 (Spawn 4.0.4): FieldGuidePlugin.getEntityClass explodes with
 *   MalformedParameterizedTypeException reading generic signatures of
 *   DeferredHolder fields. Guard: any throw -> return null (caller skips null).
 * Fix 3 (MRPGC Skill Tree 1.1.2 vs Skill Tree 1.4.4): two base-mod classes were
 *   renamed (SkillTreeSounds->SkillSounds, Spells->SkillsCommon). Remap all
 *   references; member names/descriptors verified identical on 1.4.4.
 */
public class UVFixesTransformer implements ITransformer<ClassNode> {

    private static final String QUARK_CLIENT = "org.violetmoon.quark.addons.oddities.module.TinyPotatoModule$Client";
    private static final String SPAWN_PLUGIN = "com.ninni.spawn.compat.fieldguide.FieldGuidePlugin";
    private static final String MRPGC_SPELLS = "com.mrpgc_skill_tree.skills.MrpgSkillSpells";
    private static final String MRPGC_CLIENT = "com.mrpgc_skill_tree.client.MRPGCSkillTreeClient";

    private static final String OLD_SOUNDS = "net/skill_tree_rpgs/skills/SkillTreeSounds";
    private static final String NEW_SOUNDS = "net/skill_tree_rpgs/skills/SkillSounds";
    private static final String OLD_SPELLS = "net/skill_tree_rpgs/skills/Spells";
    private static final String NEW_SPELLS = "net/skill_tree_rpgs/skills/SkillsCommon";

    @Override
    public ClassNode transform(ClassNode node, ITransformerVotingContext context) {
        String dotted = node.name.replace('/', '.');
        try {
            switch (dotted) {
                case QUARK_CLIENT -> patchQuarkPotato(node);
                case SPAWN_PLUGIN -> patchSpawnFieldGuide(node);
                case MRPGC_SPELLS, MRPGC_CLIENT -> remapMrpgc(node);
                default -> log("unexpected target " + dotted);
            }
        } catch (Throwable t) {
            log("FAILED patching " + dotted + ": " + t);
        }
        return node;
    }

    private static void patchQuarkPotato(ClassNode node) {
        for (MethodNode m : node.methods) {
            if (m.name.startsWith("lambda$modelBake")
                    && m.desc.endsWith(")Lnet/minecraft/client/resources/model/BakedModel;")
                    && m.desc.contains("Lnet/minecraft/client/resources/model/BakedModel;)")) {
                boolean isStatic = (m.access & Opcodes.ACC_STATIC) != 0;
                int modelSlot = isStatic ? 1 : 2; // (location, model) -> model is 2nd arg
                InsnList guard = new InsnList();
                LabelNode cont = new LabelNode();
                guard.add(new VarInsnNode(Opcodes.ALOAD, modelSlot));
                guard.add(new JumpInsnNode(Opcodes.IFNONNULL, cont));
                guard.add(new InsnNode(Opcodes.ACONST_NULL));
                guard.add(new InsnNode(Opcodes.ARETURN));
                guard.add(cont);
                m.instructions.insert(guard);
                log("quark tiny potato null-guard applied (" + m.name + ")");
                return;
            }
        }
        log("quark: lambda$modelBake not found - mod updated? patch skipped");
    }

    private static void patchSpawnFieldGuide(ClassNode node) {
        for (MethodNode m : node.methods) {
            if (m.name.equals("getEntityClass") && m.desc.equals("(Ljava/lang/reflect/Field;)Ljava/lang/Class;")) {
                LabelNode start = new LabelNode();
                LabelNode end = new LabelNode();
                LabelNode handler = new LabelNode();
                m.instructions.insert(start);
                InsnList tail = new InsnList();
                tail.add(end);
                tail.add(handler);
                tail.add(new InsnNode(Opcodes.POP)); // discard the Throwable
                tail.add(new InsnNode(Opcodes.ACONST_NULL));
                tail.add(new InsnNode(Opcodes.ARETURN));
                m.instructions.add(tail);
                m.tryCatchBlocks.add(new TryCatchBlockNode(start, end, handler, "java/lang/Throwable"));
                log("spawn field-guide reflection guard applied");
                return;
            }
        }
        log("spawn: getEntityClass not found - mod updated? patch skipped");
    }

    private static void remapMrpgc(ClassNode node) {
        int changed = 0;
        for (MethodNode m : node.methods) {
            for (AbstractInsnNode insn : m.instructions) {
                if (insn instanceof FieldInsnNode f) {
                    String o = f.owner, d = f.desc;
                    f.owner = remapName(f.owner);
                    f.desc = remapDesc(f.desc);
                    if (!o.equals(f.owner) || !d.equals(f.desc)) changed++;
                } else if (insn instanceof MethodInsnNode mi) {
                    String o = mi.owner, d = mi.desc;
                    mi.owner = remapName(mi.owner);
                    mi.desc = remapDesc(mi.desc);
                    if (!o.equals(mi.owner) || !d.equals(mi.desc)) changed++;
                } else if (insn instanceof TypeInsnNode ti) {
                    String d = ti.desc;
                    ti.desc = remapName(ti.desc);
                    if (!d.equals(ti.desc)) changed++;
                } else if (insn instanceof LdcInsnNode ldc && ldc.cst instanceof Type t) {
                    String d = t.getDescriptor();
                    String nd = remapDesc(d);
                    if (!d.equals(nd)) {
                        ldc.cst = Type.getType(nd);
                        changed++;
                    }
                }
            }
        }
        log("mrpgc remap applied to " + node.name + " (" + changed + " refs)");
    }

    private static String remapName(String internal) {
        if (OLD_SOUNDS.equals(internal)) return NEW_SOUNDS;
        if (OLD_SPELLS.equals(internal)) return NEW_SPELLS;
        return internal;
    }

    private static String remapDesc(String desc) {
        return desc.replace("L" + OLD_SOUNDS + ";", "L" + NEW_SOUNDS + ";")
                   .replace("L" + OLD_SPELLS + ";", "L" + NEW_SPELLS + ";");
    }

    private static void log(String msg) {
        System.out.println("[uvfixes] " + msg);
    }

    @Override
    public TransformerVoteResult castVote(ITransformerVotingContext context) {
        return TransformerVoteResult.YES;
    }

    @Override
    public Set<Target<ClassNode>> targets() {
        return Set.of(
                Target.targetClass(QUARK_CLIENT),
                Target.targetClass(SPAWN_PLUGIN),
                Target.targetClass(MRPGC_SPELLS),
                Target.targetClass(MRPGC_CLIENT)
        );
    }

    @Override
    public TargetType<ClassNode> getTargetType() {
        return TargetType.CLASS;
    }
}
