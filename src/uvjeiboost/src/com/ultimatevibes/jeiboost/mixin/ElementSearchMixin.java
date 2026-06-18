package com.ultimatevibes.jeiboost.mixin;

import com.ultimatevibes.jeiboost.Cfg;
import com.ultimatevibes.jeiboost.JEIBoost;
import com.ultimatevibes.jeiboost.WorkerPool;
import mezz.jei.api.ingredients.IIngredientHelper;
import mezz.jei.api.ingredients.ITypedIngredient;
import mezz.jei.api.ingredients.subtypes.UidContext;
import mezz.jei.api.runtime.IIngredientManager;
import mezz.jei.core.search.ISearchStorage;
import mezz.jei.core.search.PrefixInfo;
import mezz.jei.core.search.PrefixedSearchable;
import mezz.jei.core.search.SearchMode;
import mezz.jei.gui.ingredients.IListElement;
import mezz.jei.gui.ingredients.IListElementInfo;
import mezz.jei.gui.search.ElementSearch;
import org.spongepowered.asm.mixin.Final;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

import java.util.ArrayList;
import java.util.Collection;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ExecutionException;

/**
 * Parallelizes the JEI ingredient search-index build ("Building ingredient
 * filter"). Vanilla adds every element to every prefix index sequentially on
 * the render thread. Here: the uid->element map fills sequentially (fast),
 * then each prefix index builds on its own worker — a prefix's
 * ISearchStorage is only ever touched by one thread, so no locking needed.
 */
@Mixin(value = ElementSearch.class, remap = false)
public abstract class ElementSearchMixin {

    @Shadow @Final
    private Map<PrefixInfo<IListElementInfo<?>, IListElement<?>>, PrefixedSearchable<IListElementInfo<?>, IListElement<?>>> prefixedSearchables;

    @Shadow @Final
    private Map<Object, IListElement<?>> allElements;

    @Inject(method = "addAll", at = @At("HEAD"), cancellable = true, remap = false)
    private void jeiboost$parallelAddAll(Collection<IListElementInfo<?>> infos,
                                         IIngredientManager ingredientManager, CallbackInfo ci) {
        if (!Cfg.parallelFilter()) {
            return;
        }
        ci.cancel();
        long t0 = System.nanoTime();

        List<IListElementInfo<?>> added = new ArrayList<>(infos.size());
        for (IListElementInfo<?> info : infos) {
            IListElement<?> element = info.getElement();
            Object uid = jeiboost$uid(element.getTypedIngredient(), ingredientManager);
            if (allElements.putIfAbsent(uid, element) == null) {
                added.add(info);
            }
        }
        long t1 = System.nanoTime();

        try {
            WorkerPool.get().submit(() ->
                prefixedSearchables.values().parallelStream().forEach(searchable -> {
                    if (searchable.getMode() == SearchMode.DISABLED) {
                        return;
                    }
                    ISearchStorage<IListElement<?>> storage = searchable.getSearchStorage();
                    for (IListElementInfo<?> info : added) {
                        IListElement<?> element = info.getElement();
                        for (String s : searchable.getStrings(info)) {
                            storage.put(s, element);
                        }
                    }
                })
            ).get();
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new RuntimeException("[JEIBoost] interrupted during search index build", e);
        } catch (ExecutionException e) {
            throw new RuntimeException("[JEIBoost] search index build failed", e.getCause());
        }

        JEIBoost.LOGGER.info("[JEIBoost] search index: {} infos x {} prefixes in {} ms (uid map: {} ms, parallel index: {} ms)",
                added.size(), prefixedSearchables.size(),
                (System.nanoTime() - t0) / 1_000_000L,
                (t1 - t0) / 1_000_000L,
                (System.nanoTime() - t1) / 1_000_000L);
    }

    private static <T> Object jeiboost$uid(ITypedIngredient<T> typed, IIngredientManager mgr) {
        IIngredientHelper<T> helper = mgr.getIngredientHelper(typed.getType());
        return helper.getUid(typed, UidContext.Ingredient);
    }
}
