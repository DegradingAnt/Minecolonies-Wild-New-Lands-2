package com.wnl.colonyborder;

import net.neoforged.fml.common.Mod;
import net.neoforged.neoforge.common.NeoForge;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;

/**
 * Host mod for the colony-border patrol relocator. Reads its config from
 * config/wnl_colonyborder.properties and registers the game-bus handler.
 * Delete this jar to remove the feature. Addon to WNL-PackFixes.
 */
@Mod("wnl_colonyborder")
public class ColonyBorder {
    public static final Logger LOGGER = LogManager.getLogger("wnl_colonyborder");

    public ColonyBorder() {
        CBConfig.load();
        NeoForge.EVENT_BUS.register(new PatrolRelocator());
        LOGGER.info("[wnl_colonyborder] loaded (enabled={}, buffer={}, mods={})",
                CBConfig.enabled, CBConfig.bufferBlocks, CBConfig.patrolNamespaces);
    }
}
