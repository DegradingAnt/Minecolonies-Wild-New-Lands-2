package com.ultimatevibes.archersattr;

import net.neoforged.bus.api.IEventBus;
import net.neoforged.fml.common.Mod;
import net.neoforged.neoforge.event.entity.EntityAttributeCreationEvent;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.ai.attributes.AttributeSupplier;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;

/**
 * archers_expansion's NeoForge entrypoint registers its summon entities
 * (archers_expansion:alter_ego, archers_expansion:spell_polar_bear) but never
 * wires EntityAttributeCreationEvent, so those LivingEntities have no
 * AttributeSupplier and the server crashes the moment the summon spell resolves
 * ("Can't find attribute supplier for entity ...").
 *
 * This tiny addon registers the attributes the author forgot, reusing the mod's
 * OWN builder methods (createAlterEgoAttributes / createPolarBearAttributes) via
 * reflection — so there is no hard compile/runtime dependency on archers_expansion
 * and the whole thing no-ops cleanly if the mod is absent or updates its classes.
 * Delete this jar to remove the fix. Addon to UltimateVibes-PackFixes.
 */
@Mod("uvarchersattr")
public class ArchersAttrFix {
    public static final Logger LOGGER = LogManager.getLogger("uvarchersattr");

    public ArchersAttrFix(IEventBus modBus) {
        modBus.addListener(EntityAttributeCreationEvent.class, this::onAttributes);
        LOGGER.info("[uvarchersattr] loaded — will register missing attributes for archers_expansion summons");
    }

    private void onAttributes(EntityAttributeCreationEvent event) {
        int n = 0;
        n += register(event, "com.archers_expansion.entity.AlterEgoEntity", "createAlterEgoAttributes");
        n += register(event, "com.archers_expansion.entity.PolarBearEntity", "createPolarBearAttributes");
        if (n > 0) LOGGER.info("[uvarchersattr] registered attributes for {} archers_expansion summon(s)", n);
    }

    @SuppressWarnings("unchecked")
    private int register(EntityAttributeCreationEvent event, String className, String builderMethod) {
        try {
            Class<?> c = Class.forName(className);
            EntityType<? extends LivingEntity> type =
                (EntityType<? extends LivingEntity>) c.getField("ENTITY_TYPE").get(null);
            Object builder = c.getMethod(builderMethod).invoke(null);
            AttributeSupplier supplier =
                (AttributeSupplier) builder.getClass().getMethod("build").invoke(builder);
            event.put(type, supplier);
            return 1;
        } catch (ClassNotFoundException absent) {
            return 0; // archers_expansion not installed — nothing to do
        } catch (Throwable t) {
            LOGGER.warn("[uvarchersattr] could not register attributes for {} ({}): {}",
                className, builderMethod, t.toString());
            return 0;
        }
    }
}
