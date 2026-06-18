package com.ultimatevibes.mccache.mixin.client;

import com.minecolonies.core.client.render.worldevent.ColonyBlueprintRenderer;
import com.minecolonies.core.event.ClientEventHandler;
import com.ultimatevibes.mccache.MineColoniesCache;
import net.neoforged.neoforge.client.event.ClientPlayerNetworkEvent;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

/**
 * Fixes the recurring client crash:
 *   java.lang.IllegalStateException: World mismatch
 *   at structurize Blueprint.setRotationMirrorRelative (the registryAccess != check)
 *   via minecolonies ColonyBlueprintRenderer build-preview rendering on the render thread.
 *
 * Root cause: ColonyBlueprintRenderer.blueprintDataCache (Guava, keyed only on
 * packName/path/special/orientation — no level/registry identity) is NOT flushed on
 * client disconnect, even though ClientEventHandler.onPlayerLogout already flushes three
 * sibling client caches (ColonyBorderRenderer, WindowBuildingBrowser, IColonyManager views).
 * So after a reconnect (fresh client Level + fresh registryAccess) the preview renderer gets
 * a cache HIT returning a Blueprint bound to the dead level's registryAccess, and
 * applyRotationMirrorAndSync -> setRotationMirror throws "World mismatch".
 *
 * Fix: complete the pattern — also invalidate the blueprint preview cache on logout. The next
 * reconnect rebuilds previews against the live Level (cache MISS -> makeBlueprintPreview with
 * the current registryAccess), so the reference check passes. Self-healing; cannot affect
 * legitimate building/placement (which always uses the correct, matching Level). Client-only.
 */
@Mixin(value = ClientEventHandler.class, remap = false)
public abstract class ClientEventHandlerLogoutMixin {

    @Inject(method = "onPlayerLogout(Lnet/neoforged/neoforge/client/event/ClientPlayerNetworkEvent$LoggingOut;)V",
            at = @At("TAIL"))
    private static void uvmc$flushBlueprintPreviewCache(ClientPlayerNetworkEvent.LoggingOut event, CallbackInfo ci) {
        try {
            ColonyBlueprintRendererAccessor.uvmc$getBlueprintDataCache().invalidateAll(); // evict stale-registry Blueprints
            ColonyBlueprintRenderer.invalidateCache();                                    // nulls lastCacheRebuild -> rebuild derived maps
            MineColoniesCache.LOGGER.info("[uvmccache] flushed blueprint preview cache on logout (World-mismatch guard)");
        } catch (Throwable t) {
            MineColoniesCache.LOGGER.warn("[uvmccache] blueprint preview cache flush failed: {}", t.toString());
        }
    }
}
