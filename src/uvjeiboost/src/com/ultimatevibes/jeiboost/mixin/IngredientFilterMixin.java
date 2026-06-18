package com.ultimatevibes.jeiboost.mixin;

import com.ultimatevibes.jeiboost.Cfg;
import com.ultimatevibes.jeiboost.JEIBoost;
import mezz.jei.api.helpers.IColorHelper;
import mezz.jei.api.helpers.IModIdHelper;
import mezz.jei.api.runtime.IIngredientManager;
import mezz.jei.api.runtime.IIngredientVisibility;
import mezz.jei.common.config.IClientConfig;
import mezz.jei.common.config.IClientToggleState;
import mezz.jei.common.config.IIngredientFilterConfig;
import mezz.jei.gui.filter.IFilterTextSource;
import mezz.jei.gui.ingredients.IListElement;
import mezz.jei.gui.ingredients.IListElementInfo;
import mezz.jei.gui.ingredients.IngredientFilter;
import mezz.jei.gui.search.IElementSearch;
import org.spongepowered.asm.mixin.Final;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.Redirect;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

import java.util.Comparator;
import java.util.List;

/**
 * The IngredientFilter constructor indexes every element one at a time
 * (updateHiddenState + 7 prefix-index puts each) on the render thread —
 * that is the whole "Building ingredient filter" phase. addAll (which
 * ElementSearchMixin parallelizes) is only used by rebuildItemFilter.
 * Here: keep updateHiddenState per element in the loop, skip the
 * per-element index put, then bulk-index once at constructor tail through
 * the parallel addAll path.
 */
@Mixin(value = IngredientFilter.class, remap = false)
public abstract class IngredientFilterMixin {

    @Shadow
    private IElementSearch elementSearch;

    @Shadow @Final
    private IIngredientManager ingredientManager;

    @Shadow
    protected abstract <V> boolean updateHiddenState(IListElement<V> element);

    @Shadow
    public abstract void invalidateCache();

    @Redirect(method = "<init>", at = @At(value = "INVOKE",
            target = "Lmezz/jei/gui/ingredients/IngredientFilter;addIngredient(Lmezz/jei/gui/ingredients/IListElementInfo;)V"))
    private void jeiboost$skipPerElementIndex(IngredientFilter self, IListElementInfo<?> info) {
        if (!Cfg.parallelFilter()) {
            self.addIngredient(info);
            return;
        }
        this.updateHiddenState(info.getElement());
    }

    @Inject(method = "<init>", at = @At("TAIL"))
    private void jeiboost$bulkIndex(IFilterTextSource filterTextSource, IClientConfig clientConfig,
                                    IIngredientFilterConfig filterConfig, IIngredientManager ingredientManager,
                                    Comparator<IListElement<?>> comparator, List<IListElementInfo<?>> elements,
                                    IModIdHelper modIdHelper, IIngredientVisibility ingredientVisibility,
                                    IColorHelper colorHelper, IClientToggleState toggleState, CallbackInfo ci) {
        if (!Cfg.parallelFilter()) {
            return;
        }
        long t0 = System.nanoTime();
        this.elementSearch.addAll(elements, this.ingredientManager);
        this.invalidateCache();
        JEIBoost.LOGGER.info("[JEIBoost] initial filter index: {} elements bulk-indexed in {} ms",
                elements.size(), (System.nanoTime() - t0) / 1_000_000L);
    }
}
