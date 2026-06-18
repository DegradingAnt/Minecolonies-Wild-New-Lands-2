package com.ultimatevibes.mccache;

import net.neoforged.fml.common.Mod;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;

/**
 * Tiny host mod for the MineColonies discovery-cache mixin. Delete this jar to
 * remove the feature. Bump SALT to force a one-time cache rebuild.
 */
@Mod("uvmccache")
public class MineColoniesCache {
    public static final Logger LOGGER = LogManager.getLogger("uvmccache");
    public static final int SALT = 0;

    public MineColoniesCache() {
        LOGGER.info("[uvmccache] loaded — MineColonies discoverAllItems disk cache");
    }
}
