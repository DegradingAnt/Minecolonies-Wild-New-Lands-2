package com.ultimatevibes.jeiboost;

import java.util.concurrent.ForkJoinPool;
import java.util.concurrent.ForkJoinWorkerThread;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * Lazy worker pool. Threads copy the context classloader of the thread that
 * first requested the pool (the render thread) — without this, ServiceLoader
 * calls inside mod JEI plugins fail on workers (seen: just_enough_beacons).
 */
public final class WorkerPool {
    private static volatile ForkJoinPool pool;

    public static ForkJoinPool get() {
        ForkJoinPool p = pool;
        if (p == null) {
            synchronized (WorkerPool.class) {
                if (pool == null) {
                    ClassLoader tccl = Thread.currentThread().getContextClassLoader();
                    int n = Cfg.workers() > 0 ? Cfg.workers()
                            : Math.max(2, Runtime.getRuntime().availableProcessors() - 2);
                    AtomicInteger idx = new AtomicInteger();
                    pool = new ForkJoinPool(n, fjp -> {
                        ForkJoinWorkerThread t = ForkJoinPool.defaultForkJoinWorkerThreadFactory.newThread(fjp);
                        t.setName("JEIBoost-Worker-" + idx.getAndIncrement());
                        t.setContextClassLoader(tccl);
                        t.setDaemon(true);
                        return t;
                    }, null, false);
                }
                p = pool;
            }
        }
        return p;
    }

    private WorkerPool() {}
}
