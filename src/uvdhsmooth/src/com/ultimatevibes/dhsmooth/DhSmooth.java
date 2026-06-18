package com.ultimatevibes.dhsmooth;

import net.neoforged.fml.common.Mod;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Properties;

/**
 * Smooths Distant Horizons LOD draw-batch spikes WITHOUT lowering graphics.
 *
 * DH builds + uploads LOD render buffers async; when a batch finishes, the next
 * frame's near->far draw list jumps and that one frame draws all the new geometry
 * at once -> on a GPU already saturated by DH-through-shaders, a multi-hundred-ms
 * hitch. This caps how many GENUINELY-NEW (just-built) buffers join the draw per
 * frame so a batch fades in over a few frames instead of one.
 *
 * v1.1.0: terrain shown within the last {@code rememberFrames} frames is brought
 * back INSTANTLY (no ramp) -- so turning the camera around, or re-entering a view
 * you just had, shows immediately (those LODs are already on the GPU; there is no
 * spike to smooth). Only never-recently-seen geometry is ramped. The per-frame
 * admit rate is adaptive: it scales up with the new-buffer backlog (capped) so
 * exploring into fresh terrain fills in fast while a lone batch still eases in.
 * Quality-neutral: identical pixels, nothing lowered.
 *
 * config/uvdhsmooth.properties:
 *   enabled=true
 *   newBuffersPerFrame=16   base admit rate for brand-new LODs (higher = faster fill-in)
 *   maxBuffersPerFrame=64   adaptive cap when exploring (a big backlog admits up to this)
 *   rememberFrames=200      how long (frames) a shown LOD is remembered -> instant on return
 *   adaptive=true           scale the admit rate with the backlog
 */
@Mod("uvdhsmooth")
public class DhSmooth {
    public static final Logger LOGGER = LogManager.getLogger("uvdhsmooth");

    public static volatile boolean ENABLED = true;
    public static volatile boolean ADAPTIVE = true;
    public static volatile int NEW_BUFFERS_PER_FRAME = 16;
    public static volatile int MAX_BUFFERS_PER_FRAME = 64;
    public static volatile int REMEMBER_FRAMES = 200;

    public DhSmooth() {
        loadConfig();
        LOGGER.info("[uvdhsmooth] loaded — DH LOD draw-batch smoothing (enabled={}, new/frame={}, max/frame={}, remember={}f, adaptive={})",
                ENABLED, NEW_BUFFERS_PER_FRAME, MAX_BUFFERS_PER_FRAME, REMEMBER_FRAMES, ADAPTIVE);
    }

    private static int clampInt(String v, int def, int lo, int hi) {
        try {
            return Math.max(lo, Math.min(hi, Integer.parseInt(v.trim())));
        } catch (Exception e) {
            return def;
        }
    }

    private static void loadConfig() {
        Path f = Path.of("config", "uvdhsmooth.properties");
        try {
            if (Files.isRegularFile(f)) {
                Properties p = new Properties();
                try (var in = Files.newInputStream(f)) {
                    p.load(in);
                }
                ENABLED = Boolean.parseBoolean(p.getProperty("enabled", "true").trim());
                ADAPTIVE = Boolean.parseBoolean(p.getProperty("adaptive", "true").trim());
                NEW_BUFFERS_PER_FRAME = clampInt(p.getProperty("newBuffersPerFrame", "16"), 16, 1, 4096);
                MAX_BUFFERS_PER_FRAME = clampInt(p.getProperty("maxBuffersPerFrame", "64"), 64, NEW_BUFFERS_PER_FRAME, 8192);
                REMEMBER_FRAMES = clampInt(p.getProperty("rememberFrames", "200"), 200, 0, 100000);
                return;
            }
            Files.createDirectories(f.getParent());
            Files.writeString(f, "# UltimateVibes DH LOD draw-batch smoothing\n"
                    + "enabled=true\n"
                    + "# Base number of brand-new distant-LOD buffers drawn per frame.\n"
                    + "# Higher = new terrain fills in faster but bigger draw spikes. 8-32 sensible.\n"
                    + "newBuffersPerFrame=16\n"
                    + "# Adaptive cap: when exploring (big backlog) the rate rises up to this.\n"
                    + "maxBuffersPerFrame=64\n"
                    + "# How long (in frames) a shown LOD is remembered so it returns INSTANTLY\n"
                    + "# (turning around / re-entering a view). ~200 = a couple seconds.\n"
                    + "rememberFrames=200\n"
                    + "adaptive=true\n");
        } catch (Throwable t) {
            LOGGER.warn("[uvdhsmooth] config load failed, using defaults: {}", t.toString());
        }
    }
}
