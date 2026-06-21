package com.wnl.colonyborder;

import com.minecolonies.api.colony.IColony;
import com.minecolonies.api.colony.IColonyManager;
import com.minecolonies.api.util.MessageUtils;

import net.minecraft.ChatFormatting;
import net.minecraft.core.BlockPos;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.WorldGenRegion;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.monster.Enemy;
import net.minecraft.world.entity.monster.PatrollingMonster;
import net.minecraft.world.level.levelgen.Heightmap;
import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.neoforge.event.entity.living.FinalizeSpawnEvent;

/**
 * When a qualifying "patrol" mob is about to spawn INSIDE an active MineColonies colony,
 * move it to the nearest claimed-edge (+ buffer) so it approaches from the border instead of
 * materialising in the base, and warn the colony's players (like a stock raid alert). The mob
 * still spawns — only its position changes. MineColonies' own raiders are not in the qualifying
 * set, so they are left untouched.
 *
 * Performance contract: do NOTHING unless an active colony is loaded and the mob is actually
 * spawning inside it, and NEVER force a chunk to load/generate. Colony lookups use the in-memory
 * colony list (getClosestColony walks colonies by center distance, no chunk access); every
 * world probe is gated on an already-loaded chunk. This is what makes it safe during c2me
 * parallel worldgen — the old version's getColonyByPosFromWorld forced a re-entrant, blocking
 * getChunkAt() from inside the chunk generator and deadlocked the worker pool.
 */
public class PatrolRelocator {

    /** 8 compass directions; we push out along whichever exits the colony soonest. */
    private static final int[][] DIRS = {
        {1, 0}, {-1, 0}, {0, 1}, {0, -1}, {1, 1}, {1, -1}, {-1, 1}, {-1, -1}
    };

    /** Per-colony warn cooldown so a multi-mob patrol fires ONE alert, not one per member. */
    private static final java.util.Map<Long, Long> LAST_WARN = new java.util.concurrent.ConcurrentHashMap<>();
    private static final long WARN_COOLDOWN_TICKS = 200L; // ~10s

    @SubscribeEvent
    public void onFinalizeSpawn(FinalizeSpawnEvent event) {
        if (!CBConfig.enabled) return;

        final Mob mob = event.getEntity();
        if (!qualifies(mob)) return;

        // Worldgen places mobs on c2me worker threads with a WorldGenRegion; touching the colony
        // system there forces a re-entrant, blocking getChunkAt() inside the chunk generator and
        // deadlocks the worker pool. Colonies only exist on player-built, already-loaded chunks.
        if (event.getLevel() instanceof WorldGenRegion) return;

        final ServerLevel level = event.getLevel().getLevel();
        final BlockPos spawn = BlockPos.containing(event.getX(), event.getY(), event.getZ());
        if (!level.hasChunkAt(spawn)) return; // never force-load the spawn chunk

        // Performant, no-load lookup: getClosestColony walks the in-memory colony list by center
        // distance (no chunk access). Only act if there IS an active colony and the mob is spawning
        // inside its claim -- otherwise this is wilderness and we do nothing at all.
        final IColony colony = IColonyManager.getInstance().getClosestColony(level, spawn);
        if (colony == null || !colony.isActive()) return;
        if (!colony.isCoordInColony(level, spawn)) return;

        final BlockPos border = nearestBorder(level, colony, spawn);
        if (border == null) {
            if (CBConfig.cancelIfNoBorder) {
                event.setSpawnCancelled(true);
                ColonyBorder.LOGGER.debug("[wnl_colonyborder] cancelled in-colony patrol {} (no edge within {} blocks)",
                        mob.getType(), CBConfig.maxSteps * 16);
            }
            return;
        }
        mob.moveTo(border.getX() + 0.5D, border.getY(), border.getZ() + 0.5D, mob.getYRot(), mob.getXRot());
        warnColony(level, colony, mob, spawn, border);
    }

    /** Vanilla/illager-family patrols are caught by class; mod mobs by hostile + namespace/id list. */
    private boolean qualifies(Mob mob) {
        if (mob instanceof PatrollingMonster) return true;
        if (!(mob instanceof Enemy)) return false; // never relocate friendly/neutral mod mobs
        ResourceLocation id = BuiltInRegistries.ENTITY_TYPE.getKey(mob.getType());
        if (id == null) return false;
        return CBConfig.patrolIds.contains(id.toString())
                || CBConfig.patrolNamespaces.contains(id.getNamespace());
    }

    /** Walk outward in 16-block steps along 8 dirs against THIS colony's claim; first exit wins
     *  (nearest edge). Uses only the in-memory colony + already-loaded chunks -- an unloaded chunk
     *  holds no claim, so it counts as the edge, and we never force a chunk to generate. */
    private BlockPos nearestBorder(ServerLevel level, IColony colony, BlockPos spawn) {
        final int step = 16;
        BlockPos best = null;
        int bestDist = Integer.MAX_VALUE;
        for (int[] d : DIRS) {
            for (int s = 1; s <= CBConfig.maxSteps; s++) {
                int x = spawn.getX() + d[0] * step * s;
                int z = spawn.getZ() + d[1] * step * s;
                BlockPos probe = new BlockPos(x, spawn.getY(), z);
                boolean outside = !level.hasChunkAt(probe) || !colony.isCoordInColony(level, probe);
                if (outside) {
                    int dist = step * s;
                    if (dist < bestDist) {
                        bestDist = dist;
                        int bx = x + d[0] * CBConfig.bufferBlocks;
                        int bz = z + d[1] * CBConfig.bufferBlocks;
                        int by;
                        if (level.hasChunkAt(new BlockPos(bx, spawn.getY(), bz))) {
                            try {
                                by = level.getHeight(Heightmap.Types.MOTION_BLOCKING_NO_LEAVES, bx, bz);
                            } catch (Throwable t) {
                                by = spawn.getY();
                            }
                        } else {
                            by = spawn.getY(); // distant chunk unloaded -> don't force it, reuse spawn Y
                        }
                        best = new BlockPos(bx, by, bz);
                    }
                    break; // exited the colony in this direction
                }
            }
        }
        return best;
    }

    /** Warn the colony's players that a patrol is inbound -- routed through MineColonies' own
     *  MessageUtils (member targeting) but deliberately NOT a generic raid line: it's a scout
     *  report that names the actual creatures and which mod they hail from, so it reads as a
     *  distinct, immersive in-world event. Deduped per colony so a whole patrol = one alert. */
    private void warnColony(ServerLevel level, IColony colony, Mob mob, BlockPos spawn, BlockPos border) {
        if (!CBConfig.warnPlayers) return;
        final long key = colony.getCenter().asLong();
        final long now = level.getGameTime();
        final Long prev = LAST_WARN.get(key);
        if (prev != null && now - prev < WARN_COOLDOWN_TICKS) return; // already warned this wave
        LAST_WARN.put(key, now);

        final String dir = compass(border.getX() - spawn.getX(), border.getZ() - spawn.getZ());
        final ResourceLocation id = BuiltInRegistries.ENTITY_TYPE.getKey(mob.getType());
        final boolean modded = id != null && !id.getNamespace().equals("minecraft");
        final String origin = modded
                ? net.neoforged.fml.ModList.get().getModContainerById(id.getNamespace())
                        .map(c -> c.getModInfo().getDisplayName()).orElse(id.getNamespace())
                : "";

        // "Scouts report a <Mob> war-band [from <Mod>] approaching from the <dir>!"
        final MutableComponent msg = Component.literal("⚔ Scouts report a ").withStyle(ChatFormatting.RED)
                .append(mob.getType().getDescription().copy().withStyle(ChatFormatting.GOLD))
                .append(Component.literal(" war-band").withStyle(ChatFormatting.RED));
        if (modded) {
            msg.append(Component.literal(" from ").withStyle(ChatFormatting.RED))
               .append(Component.literal(origin).withStyle(ChatFormatting.GOLD));
        }
        msg.append(Component.literal(" approaching from the " + dir + "!").withStyle(ChatFormatting.RED));
        MessageUtils.format(msg).sendTo(colony).forAllPlayers();
    }

    private static String compass(int dx, int dz) {
        String ns = dz < 0 ? "north" : dz > 0 ? "south" : "";
        String ew = dx < 0 ? "west" : dx > 0 ? "east" : "";
        String s = ns + ew;
        return s.isEmpty() ? "border" : s;
    }
}
