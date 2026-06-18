package com.ultimatevibes.ftbchunks.mixin;

import com.ultimatevibes.ftbchunks.FTBChunksOffload;
import dev.ftb.mods.ftbchunks.client.FTBChunksClient;
import dev.ftb.mods.ftbchunks.client.map.MapRegionData;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

/**
 * Offloads the expensive MapRegionData.write() snapshot (five 512x512
 * BufferedImage allocations + ~1.3M setRGB calls) from the render thread to
 * FTB Chunks' own single-threaded MAP_EXECUTOR — the same thread the PNG
 * encode/zip/file write already use, so region file IO stays serialized and
 * UtilMixin's existing executor shutdown still flushes pending saves at world
 * exit. Vanilla runs the whole thing on the render thread, causing periodic
 * spikes at the hardcoded 60s autosave and on every pause-screen open.
 *
 * Accepted (cosmetic) risk: the data arrays aren't snapshotted before the async
 * copy, so a save that races a concurrent map update can store mixed-age pixels
 * — overwritten on the next save. The mod already reads these arrays on
 * MAP_EXECUTOR concurrently (RenderMapImageTask), so this doesn't add a new race
 * class. write() is read-only over the arrays (no in-memory corruption).
 */
@Mixin(targets = "dev.ftb.mods.ftbchunks.client.map.MapRegion", remap = false)
public abstract class MapRegionOffloadMixin {

    @Shadow
    private MapRegionData data;

    @Inject(method = "runMapTask", at = @At("HEAD"), cancellable = true, remap = false)
    private void uvftb$offloadWrite(CallbackInfo ci) {
        if (!FTBChunksOffload.ENABLED) {
            return;
        }
        ci.cancel();
        final MapRegionData d = this.data;
        if (d == null) {
            return;
        }
        FTBChunksClient.MAP_EXECUTOR.execute(() -> {
            try {
                d.write();
            } catch (Throwable t) {
                FTBChunksOffload.LOGGER.warn("[uvftbchunks] async map-region write failed (will retry next save): {}", t.toString());
            }
        });
    }
}
