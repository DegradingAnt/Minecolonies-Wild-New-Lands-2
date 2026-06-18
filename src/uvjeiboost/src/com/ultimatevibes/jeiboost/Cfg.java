package com.ultimatevibes.jeiboost;

import java.io.IOException;
import java.io.Reader;
import java.io.Writer;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Arrays;
import java.util.HashSet;
import java.util.Properties;
import java.util.Set;

/** Plain properties config: config/jeiboost.properties (written with defaults on first run). */
public final class Cfg {
    private static boolean parallelRecipes = true;
    private static boolean parallelFilter = true;
    private static boolean creativeTabCache = true;
    private static int creativeTabCacheSalt = 0;
    private static boolean creativeTabCacheDailyInvalidate = false;
    private static int workers = 0;
    private static Set<String> pinned = new HashSet<>(Set.of("at.xander.jrftl.JEIConfig"));

    static void load() {
        Path p = Path.of("config", "jeiboost.properties");
        Properties props = new Properties();
        try {
            if (Files.isRegularFile(p)) {
                try (Reader r = Files.newBufferedReader(p)) { props.load(r); }
            } else {
                props.setProperty("parallelRecipes", "true");
                props.setProperty("parallelFilter", "true");
                props.setProperty("creativeTabCache", "true");
                props.setProperty("creativeTabCacheSalt", "0");
                props.setProperty("creativeTabCacheDailyInvalidate", "false");
                props.setProperty("workers", "0");
                props.setProperty("pinnedPlugins", "at.xander.jrftl.JEIConfig");
                Files.createDirectories(p.getParent());
                try (Writer w = Files.newBufferedWriter(p)) {
                    props.store(w, "JEIBoost — parallel JEI plugin registration + join-time caches.\n"
                            + "parallelRecipes: run the 'Registering recipes' phase on worker threads (failed plugins retry on the main thread).\n"
                            + "parallelFilter: build the ingredient search index on worker threads.\n"
                            + "creativeTabCache: cache the 'Registering ingredients' creative-tab scan to disk (local/jeiboost/creative-items.nbt) — saves ~10s per world join after the first. Auto-rebuilds when the mod set or relevant datapack registries change. Disabled automatically when JEI 'show creative tab names' or the creative-tab search mode are enabled (those features need the live scan).\n"
                            + "creativeTabCacheSalt: bump this integer to force a one-time rebuild of the creative-tab cache (e.g. after a mod CONFIG change that altered tab contents).\n"
                            + "creativeTabCacheDailyInvalidate: also rebuild the creative-tab cache once per calendar day (only needed if a mod gates tab items by real-world date; default false so the cache persists across days).\n"
                            + "workers: 0 = auto (cores-2, min 2).\n"
                            + "pinnedPlugins: comma-separated plugin class names that must ALWAYS run on the main thread.");
                }
            }
        } catch (IOException ignored) {
        }
        parallelRecipes = Boolean.parseBoolean(props.getProperty("parallelRecipes", "true"));
        parallelFilter = Boolean.parseBoolean(props.getProperty("parallelFilter", "true"));
        creativeTabCache = Boolean.parseBoolean(props.getProperty("creativeTabCache", "true"));
        creativeTabCacheDailyInvalidate = Boolean.parseBoolean(props.getProperty("creativeTabCacheDailyInvalidate", "false"));
        try { creativeTabCacheSalt = Integer.parseInt(props.getProperty("creativeTabCacheSalt", "0").trim()); } catch (NumberFormatException e) { creativeTabCacheSalt = 0; }
        try { workers = Integer.parseInt(props.getProperty("workers", "0").trim()); } catch (NumberFormatException e) { workers = 0; }
        String pin = props.getProperty("pinnedPlugins", "at.xander.jrftl.JEIConfig");
        pinned = new HashSet<>();
        Arrays.stream(pin.split(",")).map(String::trim).filter(s -> !s.isEmpty()).forEach(pinned::add);
    }

    public static boolean parallelRecipes() { return parallelRecipes; }
    public static boolean parallelFilter() { return parallelFilter; }
    public static boolean creativeTabCache() { return creativeTabCache; }
    public static int creativeTabCacheSalt() { return creativeTabCacheSalt; }
    public static boolean creativeTabCacheDailyInvalidate() { return creativeTabCacheDailyInvalidate; }
    public static int workers() { return workers; }
    public static boolean isPinned(String className) { return pinned.contains(className); }

    private Cfg() {}
}
