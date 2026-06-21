package com.wnl.joingate;

import net.neoforged.fml.common.Mod;
import net.neoforged.neoforge.common.NeoForge;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;

/**
 * Host mod for the join-gate chunk pre-loader. Reads config/wnl_joingate.properties and registers
 * the game-bus handler. Delete this jar to remove the feature. Addon to WNL-PackFixes.
 */
@Mod("wnl_joingate")
public class JoinGate {
    public static final Logger LOGGER = LogManager.getLogger("wnl_joingate");

    public JoinGate() {
        JGConfig.load();
        NeoForge.EVENT_BUS.register(new JoinGateHandler());
        LOGGER.info("[wnl_joingate] loaded (enabled={}, radiusChunks={}, holdSeconds={})",
                JGConfig.enabled, JGConfig.radiusChunks, JGConfig.holdSeconds);
    }
}
