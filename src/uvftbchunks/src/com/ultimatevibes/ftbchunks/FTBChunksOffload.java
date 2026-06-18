package com.ultimatevibes.ftbchunks;

import net.neoforged.fml.common.Mod;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;

/** Host mod for the FTB Chunks map-save offload mixin. Delete this jar to remove the feature. */
@Mod("uvftbchunks")
public class FTBChunksOffload {
    public static final Logger LOGGER = LogManager.getLogger("uvftbchunks");
    public static final boolean ENABLED = true;

    public FTBChunksOffload() {
        LOGGER.info("[uvftbchunks] loaded — map-save snapshot offloaded to MAP_EXECUTOR");
    }
}
