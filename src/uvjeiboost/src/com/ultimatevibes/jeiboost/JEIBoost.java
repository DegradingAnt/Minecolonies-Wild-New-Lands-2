package com.ultimatevibes.jeiboost;

import net.neoforged.fml.common.Mod;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;

@Mod("jeiboost")
public class JEIBoost {
    public static final Logger LOGGER = LogManager.getLogger("JEIBoost");

    public JEIBoost() {
        Cfg.load();
        LOGGER.info("[JEIBoost] loaded — parallelRecipes={} workers={}",
                Cfg.parallelRecipes(), Cfg.workers() == 0 ? "auto" : Cfg.workers());
    }
}
