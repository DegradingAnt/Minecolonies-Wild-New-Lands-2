package com.ultimatevibes.mccache.mixin.client;

import com.google.common.cache.Cache;
import com.minecolonies.core.client.render.worldevent.ColonyBlueprintRenderer;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.gen.Accessor;

/**
 * Exposes ColonyBlueprintRenderer's private-static-final Guava preview cache
 *   private static final Cache&lt;BlueprintCacheKey, BlueprintPreviewData&gt; blueprintDataCache
 * so the logout hook can flush it. The cache key (packName, path, special,
 * orientation) carries no level/registry identity, so a reconnect is a cache
 * HIT that returns a Blueprint still bound to the dead level's registryAccess.
 */
@Mixin(value = ColonyBlueprintRenderer.class, remap = false)
public interface ColonyBlueprintRendererAccessor {

    @Accessor("blueprintDataCache")
    static Cache<?, ?> uvmc$getBlueprintDataCache() {
        throw new AssertionError(); // replaced by Mixin
    }
}
