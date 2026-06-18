package com.ultimatevibes.dhsmooth.mixin;

import com.seibel.distanthorizons.core.util.objects.SortedArraySet;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.gen.Accessor;

import java.util.ArrayList;

/**
 * Exposes SortedArraySet's backing {@code private final ArrayList<E> list} so the
 * render-list throttle can remove deferred (just-appeared) buffers in O(n) without
 * the O(n^2) clear()+re-add (sorted-insert) the public API would force. Removal
 * preserves the near->far order, so the sorted invariant is kept.
 */
@Mixin(value = SortedArraySet.class, remap = false)
public interface SortedArraySetAccessor {

    @Accessor("list")
    ArrayList<Object> uvdh$getBackingList();
}
