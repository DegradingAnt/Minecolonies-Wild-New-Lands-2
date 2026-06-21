package com.wnl.joingate;

import net.neoforged.fml.loading.FMLPaths;

import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Properties;

/** Plain-properties config at config/wnl_joingate.properties (matches the wnl_colonyborder style). */
public final class JGConfig {
    public static boolean enabled = true;
    public static int radiusChunks = 2;   // force-load this many chunks (radius) around the landing spot
    public static int holdSeconds = 6;    // keep them force-loaded this long, then the ticket self-expires

    public static void load() {
        try {
            Path p = FMLPaths.CONFIGDIR.get().resolve("wnl_joingate.properties");
            if (Files.exists(p)) {
                Properties pr = new Properties();
                try (InputStream in = Files.newInputStream(p)) {
                    pr.load(in);
                }
                enabled = Boolean.parseBoolean(pr.getProperty("enabled", "true").trim());
                radiusChunks = clamp(parseInt(pr.getProperty("radiusChunks"), 2), 0, 8);
                holdSeconds = clamp(parseInt(pr.getProperty("holdSeconds"), 6), 1, 30);
            } else {
                writeDefault(p);
            }
        } catch (Exception e) {
            JoinGate.LOGGER.warn("[wnl_joingate] config load failed, using defaults: {}", e.toString());
        }
    }

    private static int parseInt(String s, int def) {
        try {
            return Integer.parseInt(s.trim());
        } catch (Exception e) {
            return def;
        }
    }

    private static int clamp(int v, int lo, int hi) {
        return Math.max(lo, Math.min(hi, v));
    }

    private static void writeDefault(Path p) throws java.io.IOException {
        String content = String.join("\n",
                "# WNL Join Gate — on join/respawn/dimension-change, force-load the chunks around the",
                "# player's ACTUAL landing position to FULL immediately, so the area is solid/meshed fast",
                "# instead of materialising around you. Self-expiring ticket; server-side; no mixins.",
                "enabled=true",
                "# Chunks around the player to force-load (radius). 2 = a 5x5 ring.",
                "radiusChunks=2",
                "# Seconds to hold the force-load before the ticket auto-expires.",
                "holdSeconds=6",
                "");
        Files.write(p, content.getBytes(StandardCharsets.UTF_8));
    }

    private JGConfig() {
    }
}
