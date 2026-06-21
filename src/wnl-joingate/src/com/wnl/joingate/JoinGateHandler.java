package com.wnl.joingate;

import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.server.level.TicketType;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.ChunkPos;
import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.neoforge.event.entity.player.PlayerEvent;

import java.util.Comparator;

/**
 * On join / respawn / dimension-change, force-load a small ring of chunks around the player's
 * LANDING position to full right away, with a self-expiring chunk ticket.
 *
 * Why: vanilla's "Preparing spawn area" loads chunks around world-spawn (0,0). When you log into an
 * existing save far from spawn, that prep is useless for where you actually land — nothing makes the
 * landing chunks render-ready until the player's own view-distance tickets lazily propagate, so the
 * area meshes in around you ("feels unfinished"). This adds a temporary, high-priority ticket on the
 * landing chunks so the server loads + ticks + ships them to the client immediately.
 *
 * Safe by construction: the ticket TYPE carries an expiry (holdSeconds), so the force-load is removed
 * automatically — never persisted to forcedchunks, never blocks the login thread, no mixin.
 */
public class JoinGateHandler {

    // One reusable, self-expiring ticket type. The 3rd arg = lifespan in ticks: once it elapses the
    // chunk system drops the ticket on its own, so we never leave chunks forced. Built lazily because
    // the lifespan comes from config, which is loaded before this handler is ever invoked.
    private static TicketType<ChunkPos> type;

    private static TicketType<ChunkPos> ticketType() {
        if (type == null) {
            type = TicketType.create("wnl_joingate",
                    Comparator.comparingLong(ChunkPos::toLong), JGConfig.holdSeconds * 20);
        }
        return type;
    }

    @SubscribeEvent
    public void onLogin(PlayerEvent.PlayerLoggedInEvent e) {
        gate(e.getEntity());
    }

    @SubscribeEvent
    public void onRespawn(PlayerEvent.PlayerRespawnEvent e) {
        gate(e.getEntity());
    }

    @SubscribeEvent
    public void onChangedDimension(PlayerEvent.PlayerChangedDimensionEvent e) {
        gate(e.getEntity());
    }

    private void gate(Player player) {
        if (!JGConfig.enabled) return;
        if (!(player instanceof ServerPlayer sp)) return;        // server-side only (never on the client copy)
        if (!(sp.level() instanceof ServerLevel level)) return;

        final ChunkPos center = sp.chunkPosition();
        // addRegionTicket(type, center, radius, value): forces every chunk within `radius` of `center`
        // to a load level high enough to fully load (and tick) it. The ticket level is (33 - radius),
        // so radius 2 => the centre reaches level 31 (entity-ticking) and a 5x5 ring loads. The ticket
        // self-expires after holdSeconds, then normal player view-distance tickets carry the area.
        level.getChunkSource().addRegionTicket(ticketType(), center, JGConfig.radiusChunks, center);

        JoinGate.LOGGER.debug("[wnl_joingate] force-loaded r{} around {} for {}s ({})",
                JGConfig.radiusChunks, center, JGConfig.holdSeconds, sp.getGameProfile().getName());
    }
}
