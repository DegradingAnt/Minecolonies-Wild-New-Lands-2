package com.wnl.colonyborder;

import net.neoforged.fml.loading.FMLPaths;

import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Arrays;
import java.util.HashSet;
import java.util.Properties;
import java.util.Set;

/** Plain-properties config at config/wnl_colonyborder.properties (matches the wnl_dhsmooth.properties style). */
public final class CBConfig {
    public static boolean enabled = true;
    public static int bufferBlocks = 8;
    public static int maxSteps = 32;          // 32 * 16 = 512 blocks max outward search
    public static boolean cancelIfNoBorder = true;
    public static boolean warnPlayers = true;     // chat-warn colony members of an inbound patrol (stock-raid style)
    public static Set<String> patrolNamespaces = new HashSet<>(Arrays.asList(
            "illagerinvasion", "raided", "takesapillage",
            "born_in_chaos_v1", "valarian_conquest", "knightquest"));
    public static Set<String> patrolIds = new HashSet<>();

    public static void load() {
        try {
            Path p = FMLPaths.CONFIGDIR.get().resolve("wnl_colonyborder.properties");
            if (Files.exists(p)) {
                Properties pr = new Properties();
                try (InputStream in = Files.newInputStream(p)) {
                    pr.load(in);
                }
                enabled = Boolean.parseBoolean(pr.getProperty("enabled", "true").trim());
                bufferBlocks = parseInt(pr.getProperty("bufferBlocks"), 8);
                maxSteps = Math.max(1, parseInt(pr.getProperty("maxSteps"), 32));
                cancelIfNoBorder = Boolean.parseBoolean(pr.getProperty("cancelIfNoBorder", "true").trim());
                warnPlayers = Boolean.parseBoolean(pr.getProperty("warnPlayers", "true").trim());
                patrolNamespaces = csv(pr.getProperty("patrolModNamespaces",
                        String.join(",", patrolNamespaces)));
                patrolIds = csv(pr.getProperty("patrolMobIds", ""));
            } else {
                writeDefault(p);
            }
        } catch (Exception e) {
            ColonyBorder.LOGGER.warn("[wnl_colonyborder] config load failed, using defaults: {}", e.toString());
        }
    }

    private static int parseInt(String s, int def) {
        try {
            return Integer.parseInt(s.trim());
        } catch (Exception e) {
            return def;
        }
    }

    private static Set<String> csv(String s) {
        Set<String> r = new HashSet<>();
        if (s != null) {
            for (String t : s.split(",")) {
                t = t.trim();
                if (!t.isEmpty()) r.add(t);
            }
        }
        return r;
    }

    private static void writeDefault(Path p) throws java.io.IOException {
        String content = String.join("\n",
                "# WNL Colony Border — relocate patrol/raid mobs to the colony edge instead of inside.",
                "enabled=true",
                "# Blocks past the claimed edge to drop relocated mobs.",
                "bufferBlocks=8",
                "# Max outward search in 16-block steps (32 = 512 blocks).",
                "maxSteps=32",
                "# If no edge found within range, cancel the in-colony spawn (true) or leave it (false).",
                "cancelIfNoBorder=true",
                "# Chat-warn colony members when a patrol is relocated to the border (like a stock raid alert).",
                "warnPlayers=true",
                "# Whole mods whose HOSTILE mobs get relocated when they'd spawn inside a colony.",
                "# (Illager-family / PatrollingMonster mobs are always caught, regardless of this list.)",
                "patrolModNamespaces=illagerinvasion,raided,takesapillage,born_in_chaos_v1,valarian_conquest,knightquest",
                "# Extra exact entity ids (comma-separated), e.g. minecraft:pillager,somemod:raider.",
                "patrolMobIds=",
                "") ;
        Files.write(p, content.getBytes(StandardCharsets.UTF_8));
    }

    private CBConfig() {
    }
}
