package com.ultimatevibes.jeiboost.mixin;

import com.llamalad7.mixinextras.injector.wrapmethod.WrapMethod;
import com.llamalad7.mixinextras.injector.wrapoperation.Operation;
import com.ultimatevibes.jeiboost.Cfg;
import mezz.jei.api.recipe.RecipeType;
import mezz.jei.library.recipes.RecipeManagerInternal;
import org.spongepowered.asm.mixin.Mixin;

import java.util.List;

/**
 * JEI's recipe store is not thread-safe; when plugins register concurrently
 * (PluginCallerMixin) every addRecipes call must serialize on the manager.
 */
@Mixin(value = RecipeManagerInternal.class, remap = false)
public class RecipeManagerInternalMixin {

    @WrapMethod(method = "addRecipes", remap = false)
    private <T> void jeiboost$synchronizeAddRecipes(RecipeType<T> recipeType, List<T> recipes, Operation<Void> original) {
        if (!Cfg.parallelRecipes()) {
            original.call(recipeType, recipes);
            return;
        }
        synchronized (this) {
            original.call(recipeType, recipes);
        }
    }
}
