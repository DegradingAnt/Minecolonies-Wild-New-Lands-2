package com.ultimatevibes.jeiboost.mixin;

import com.ultimatevibes.jeiboost.Cfg;
import com.ultimatevibes.jeiboost.JEIBoost;
import com.ultimatevibes.jeiboost.WorkerPool;
import mezz.jei.api.IModPlugin;
import mezz.jei.library.load.PluginCaller;
import mezz.jei.library.plugins.vanilla.VanillaPlugin;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.ConcurrentLinkedQueue;
import java.util.concurrent.ExecutionException;
import java.util.function.Consumer;

/**
 * Parallelizes JEI's "Registering recipes" phase across worker threads.
 * Safety model (lessons from jeioptimizer 1.0.0 failures in this pack):
 *  - VanillaPlugin and config-pinned plugins (default: jrftl, which calls
 *    IngredientManager.removeIngredientsAtRuntime — main-thread asserted)
 *    always run sequentially on the calling thread, vanilla first.
 *  - Workers get the caller's context classloader (see WorkerPool).
 *  - Any plugin that fails on a worker is RETRIED sequentially on the
 *    calling thread after the pool drains; only if that also fails is the
 *    error logged (JEI-style) and the plugin skipped.
 */
@Mixin(value = PluginCaller.class, remap = false)
public class PluginCallerMixin {

    @Inject(method = "callOnPlugins", at = @At("HEAD"), cancellable = true, remap = false)
    private static void jeiboost$parallelRecipes(String title, List<IModPlugin> plugins,
                                                 Consumer<IModPlugin> func, CallbackInfo ci) {
        if (!"Registering recipes".equals(title) || !Cfg.parallelRecipes() || plugins.size() < 4) {
            return;
        }
        ci.cancel();
        long t0 = System.nanoTime();

        List<IModPlugin> pinned = new ArrayList<>();
        List<IModPlugin> parallel = new ArrayList<>();
        for (IModPlugin p : plugins) {
            if (p instanceof VanillaPlugin || Cfg.isPinned(p.getClass().getName())) {
                pinned.add(p);
            } else {
                parallel.add(p);
            }
        }
        JEIBoost.LOGGER.info("[JEIBoost] {} (parallel)… [{} plugins, {} pinned to main thread]",
                title, plugins.size(), pinned.size());

        for (IModPlugin p : pinned) {
            if (p instanceof VanillaPlugin) {
                func.accept(p); // vanilla errors stay fatal, as in stock JEI
            } else {
                runLogged(title, p, func);
            }
        }

        ConcurrentLinkedQueue<IModPlugin> failed = new ConcurrentLinkedQueue<>();
        try {
            WorkerPool.get().submit(() -> parallel.parallelStream().forEach(p -> {
                try {
                    func.accept(p);
                } catch (Throwable t) {
                    JEIBoost.LOGGER.warn("[JEIBoost] {}: {} failed on worker, will retry on main thread ({})",
                            title, p.getClass().getName(), t.toString());
                    failed.add(p);
                }
            })).get();
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new RuntimeException("[JEIBoost] interrupted during parallel '" + title + "'", e);
        } catch (ExecutionException e) {
            throw new RuntimeException("[JEIBoost] parallel '" + title + "' failed", e.getCause());
        }

        for (IModPlugin p : failed) {
            runLogged(title, p, func);
        }

        JEIBoost.LOGGER.info("[JEIBoost] {} took {} ms (parallel, {} retried on main thread)",
                title, (System.nanoTime() - t0) / 1_000_000L, failed.size());
    }

    private static void runLogged(String title, IModPlugin plugin, Consumer<IModPlugin> func) {
        try {
            func.accept(plugin);
        } catch (Throwable t) {
            // mirror JEI's own per-plugin error handling: log and continue
            JEIBoost.LOGGER.error("Caught an error from mod plugin: {} {}",
                    plugin.getClass(), plugin.getPluginUid(), t);
        }
    }
}
