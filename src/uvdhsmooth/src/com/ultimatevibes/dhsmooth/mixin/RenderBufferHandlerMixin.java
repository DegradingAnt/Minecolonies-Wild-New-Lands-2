package com.ultimatevibes.dhsmooth.mixin;

import com.seibel.distanthorizons.core.render.RenderBufferHandler;
import com.seibel.distanthorizons.core.render.RenderParams;
import com.seibel.distanthorizons.core.util.objects.SortedArraySet;
import com.seibel.distanthorizons.core.wrapperInterfaces.modAccessor.IIrisAccessor;
import com.ultimatevibes.dhsmooth.DhSmooth;
import org.spongepowered.asm.mixin.Final;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.Unique;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

import java.util.ArrayList;
import java.util.IdentityHashMap;
import java.util.Iterator;
import java.util.Map;

/**
 * Caps how many GENUINELY-NEW LOD buffers join the per-frame draw list so a finished
 * async batch fades in over a few frames instead of spiking one frame -- while bringing
 * RECENTLY-SHOWN terrain back instantly (no ramp) so turning the camera around or
 * re-entering a view is immediate. See {@link com.ultimatevibes.dhsmooth.DhSmooth}.
 *
 * buildRenderList() clears loadedNearToFarBuffers and rebuilds it (near->far) every
 * frame. We run at its TAIL (after rebuild, before renderTerrain draws the set):
 *   - a buffer seen within rememberFrames -> kept instantly (already on the GPU; no spike),
 *     and its "last seen" stamp is refreshed;
 *   - a buffer NOT seen recently (genuinely new / long-gone) -> admitted only up to an
 *     adaptive per-frame budget; the rest are dropped from THIS frame's list and re-offered
 *     next frame, so they ramp in over a few frames.
 * Main pass only. Stamps live in a reused long[] holder per buffer (no per-frame boxing);
 * stale stamps are evicted periodically. All in try/catch -> on any issue, DH renders normally.
 */
@Mixin(value = RenderBufferHandler.class, remap = false)
public abstract class RenderBufferHandlerMixin {

    @Shadow @Final private SortedArraySet<?> loadedNearToFarBuffers;
    @Shadow @Final private static IIrisAccessor IRIS_ACCESSOR;

    /** buffer identity -> { lastSeenFrame }. long[] holder is mutated in place (no boxing). */
    @Unique private final IdentityHashMap<Object, long[]> uvdh$lastSeen = new IdentityHashMap<>();
    @Unique private final ArrayList<Object> uvdh$keep = new ArrayList<>();
    @Unique private long uvdh$frame = 0L;

    @Inject(method = "buildRenderList", at = @At("TAIL"))
    private void uvdh$smoothDrawBatch(RenderParams renderParams, CallbackInfo ci) {
        try {
            if (!DhSmooth.ENABLED) {
                return;
            }
            // Only smooth the main pass; leave the shadow pass untouched.
            if (IRIS_ACCESSOR != null && IRIS_ACCESSOR.isRenderingShadowPass()) {
                return;
            }
            final long frame = ++uvdh$frame;
            final long ttl = DhSmooth.REMEMBER_FRAMES;

            @SuppressWarnings("unchecked")
            ArrayList<Object> list = ((SortedArraySetAccessor) (Object) this.loadedNearToFarBuffers).uvdh$getBackingList();
            final int n = list.size();
            if (n == 0) {
                return;
            }

            // Count genuinely-new (not seen within ttl) to size the adaptive budget.
            int newCount = 0;
            for (int i = 0; i < n; i++) {
                long[] s = uvdh$lastSeen.get(list.get(i));
                if (s == null || frame - s[0] > ttl) {
                    newCount++;
                }
            }
            int budget = DhSmooth.NEW_BUFFERS_PER_FRAME;
            if (DhSmooth.ADAPTIVE && newCount > budget) {
                // catch up faster the bigger the backlog, but never above the cap
                budget = Math.min(DhSmooth.MAX_BUFFERS_PER_FRAME, budget + (newCount - budget) / 2);
            }

            final ArrayList<Object> keep = uvdh$keep;
            keep.clear();
            int admittedNew = 0;
            boolean deferred = false;
            for (int i = 0; i < n; i++) {
                Object b = list.get(i);
                long[] s = uvdh$lastSeen.get(b);
                boolean recent = (s != null && frame - s[0] <= ttl);
                if (recent) {
                    keep.add(b);
                    s[0] = frame; // refresh, no allocation
                } else if (admittedNew < budget) {
                    keep.add(b);
                    if (s == null) {
                        uvdh$lastSeen.put(b, new long[]{frame});
                    } else {
                        s[0] = frame;
                    }
                    admittedNew++;
                } else {
                    deferred = true; // genuinely-new beyond budget -> draw it a frame or two later
                }
            }

            if (deferred) {
                list.clear();
                list.addAll(keep); // near->far order preserved; sorted invariant intact
            }

            // Evict stale stamps every 64 frames so the map stays bounded.
            if ((frame & 63L) == 0L && !uvdh$lastSeen.isEmpty()) {
                Iterator<Map.Entry<Object, long[]>> it = uvdh$lastSeen.entrySet().iterator();
                while (it.hasNext()) {
                    if (frame - it.next().getValue()[0] > ttl) {
                        it.remove();
                    }
                }
            }
        } catch (Throwable t) {
            DhSmooth.LOGGER.warn("[uvdhsmooth] smoothing skipped this frame (DH internals changed?): {}", t.toString());
        }
    }
}
