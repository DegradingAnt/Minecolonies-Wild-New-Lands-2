package com.ultimatevibes.jeiboost.mixin;

import com.ultimatevibes.jeiboost.Cfg;
import com.ultimatevibes.jeiboost.JEIBoost;
import com.ultimatevibes.jeiboost.WorkerPool;
import mezz.jei.common.Internal;
import mezz.jei.common.config.IJeiClientConfigs;
import mezz.jei.common.util.StackHelper;
import mezz.jei.core.search.SearchMode;
import mezz.jei.library.plugins.vanilla.ingredients.ItemStackHelper;
import mezz.jei.library.plugins.vanilla.ingredients.ItemStackListFactory;
import net.minecraft.client.Minecraft;
import net.minecraft.core.Registry;
import net.minecraft.core.RegistryAccess;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.core.registries.Registries;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.ListTag;
import net.minecraft.nbt.NbtAccounter;
import net.minecraft.nbt.NbtIo;
import net.minecraft.nbt.Tag;
import net.minecraft.resources.ResourceKey;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.item.ItemStack;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

import java.io.IOException;
import java.lang.ref.SoftReference;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.security.MessageDigest;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Optional;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.stream.IntStream;
import java.util.stream.Stream;

/**
 * Caches JEI's "Registering ingredients" creative-tab scan to disk.
 *
 * ItemStackListFactory.create loops every CATEGORY creative tab and calls
 * CreativeModeTab.buildContents, which fires BuildCreativeModeTabContentsEvent
 * across all ~650 mod buses and hashes every stack's full component map several
 * times — ~12 s on the render thread at every world join. The result (a flat,
 * ordered List&lt;ItemStack&gt;) depends only on the installed mods + the
 * datapack-driven registries that feed tab stacks + a few client options, not
 * on world state, so it is disk-cacheable keyed on that state.
 *
 * On a cache hit we return the stored list (parsed in parallel) and skip the
 * whole scan. On a miss we let vanilla run and write the result back on a
 * background daemon thread. The cache self-heals: any key mismatch, parse
 * failure, or IO error deletes the file and falls back to the live scan, so a
 * stale or corrupt cache can never produce wrong data — only a one-time rescan.
 *
 * Guarded off automatically when JEI's "show creative tab names" or creative-tab
 * search mode are enabled — those features need the tabs' displayItems populated
 * by the live scan, which the cache path skips.
 */
@Mixin(value = ItemStackListFactory.class, remap = false)
public abstract class ItemStackListFactoryMixin {

    private static final int CACHE_FORMAT = 1;

    /** Single-slot in-memory cache: serves repeated joins in one game session without a disk read. */
    private static volatile String jeiboost$memKey;
    private static volatile SoftReference<List<ItemStack>> jeiboost$memList;

    /** Set at HEAD on a miss so RETURN knows to write (and with which key); null = do not write. */
    private static volatile String jeiboost$pendingKey;

    @Inject(method = "create", at = @At("HEAD"), cancellable = true, remap = false)
    private static void jeiboost$loadCachedTabItems(StackHelper stackHelper, ItemStackHelper itemStackHelper,
                                                    CallbackInfoReturnable<List<ItemStack>> cir) {
        jeiboost$pendingKey = null;
        if (!Cfg.creativeTabCache()) {
            return;
        }
        IJeiClientConfigs cfgs = Internal.getJeiClientConfigs();
        if (cfgs == null || !jeiboost$guardOk(cfgs)) {
            return;
        }
        Minecraft mc = Minecraft.getInstance();
        if (mc == null || mc.level == null) {
            return; // let vanilla run (and throw its own NPE if level is genuinely null)
        }
        RegistryAccess registryAccess = mc.level.registryAccess();

        String key;
        try {
            key = jeiboost$cacheKey(registryAccess, cfgs, mc);
        } catch (Throwable t) {
            JEIBoost.LOGGER.warn("[JEIBoost] creative-tab cache key failed, using live scan: {}", t.toString());
            return;
        }

        // in-memory first
        String mk = jeiboost$memKey;
        SoftReference<List<ItemStack>> ref = jeiboost$memList;
        if (mk != null && mk.equals(key) && ref != null) {
            List<ItemStack> cached = ref.get();
            if (cached != null) {
                JEIBoost.LOGGER.info("[JEIBoost] creative-tab cache hit (memory): {} items", cached.size());
                cir.setReturnValue(new ArrayList<>(cached)); // pristine copy stays in mem
                return;
            }
        }

        // disk
        long t0 = System.nanoTime();
        List<ItemStack> disk = jeiboost$readDisk(key, registryAccess);
        if (disk != null) {
            jeiboost$memKey = key;
            jeiboost$memList = new SoftReference<>(disk); // pristine copy stays in mem
            JEIBoost.LOGGER.info("[JEIBoost] creative-tab cache hit (disk): {} items decoded in {} ms",
                    disk.size(), (System.nanoTime() - t0) / 1_000_000L);
            cir.setReturnValue(new ArrayList<>(disk));
            return;
        }

        // miss: let vanilla build, RETURN writes it
        jeiboost$pendingKey = key;
    }

    @Inject(method = "create", at = @At("RETURN"), remap = false)
    private static void jeiboost$saveTabItems(StackHelper stackHelper, ItemStackHelper itemStackHelper,
                                              CallbackInfoReturnable<List<ItemStack>> cir) {
        final String key = jeiboost$pendingKey;
        jeiboost$pendingKey = null;
        if (key == null) {
            return; // cache disabled, guarded out, or a hit already returned at HEAD
        }
        List<ItemStack> result = cir.getReturnValue();
        if (result == null) {
            return;
        }
        final List<ItemStack> snapshot = new ArrayList<>(result);

        Minecraft mc = Minecraft.getInstance();
        if (mc == null || mc.level == null) {
            return;
        }
        final RegistryAccess registryAccess = mc.level.registryAccess();

        // serve later joins this session straight away
        jeiboost$memKey = key;
        jeiboost$memList = new SoftReference<>(new ArrayList<>(snapshot));

        Thread writer = new Thread(() -> {
            try {
                ListTag items = new ListTag();
                for (ItemStack stack : snapshot) {
                    items.add(stack.save(registryAccess)); // name-based NBT, registry-order independent
                }
                CompoundTag root = new CompoundTag();
                root.putInt("v", CACHE_FORMAT);
                root.putString("key", key);
                root.putInt("count", snapshot.size());
                root.put("items", items);

                Path file = jeiboost$cacheFile();
                Files.createDirectories(file.getParent());
                Path tmp = file.resolveSibling(file.getFileName() + ".tmp");
                NbtIo.writeCompressed(root, tmp);
                try {
                    Files.move(tmp, file, StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.ATOMIC_MOVE);
                } catch (IOException atomicFailed) {
                    Files.move(tmp, file, StandardCopyOption.REPLACE_EXISTING);
                }
                JEIBoost.LOGGER.info("[JEIBoost] creative-tab cache written: {} items", snapshot.size());
            } catch (Throwable t) {
                JEIBoost.LOGGER.warn("[JEIBoost] creative-tab cache write failed (live scan next join): {}", t.toString());
            }
        }, "JEIBoost-TabCacheWrite");
        writer.setDaemon(true);
        writer.setPriority(Thread.MIN_PRIORITY);
        writer.start();
    }

    /** These JEI features read each tab's displayItems during the scan; the cache path skips building them. */
    private static boolean jeiboost$guardOk(IJeiClientConfigs cfgs) {
        try {
            if (cfgs.getClientConfig().isShowCreativeTabNamesEnabled()) {
                return false;
            }
            return cfgs.getIngredientFilterConfig().getCreativeTabSearchMode() == SearchMode.DISABLED;
        } catch (Throwable t) {
            return false;
        }
    }

    private static Path jeiboost$cacheFile() {
        return Path.of("local", "jeiboost", "creative-items.nbt");
    }

    private static List<ItemStack> jeiboost$readDisk(String key, RegistryAccess registryAccess) {
        Path file = jeiboost$cacheFile();
        if (!Files.isRegularFile(file)) {
            return null;
        }
        try {
            CompoundTag root = NbtIo.readCompressed(file, NbtAccounter.unlimitedHeap());
            if (root.getInt("v") != CACHE_FORMAT || !key.equals(root.getString("key"))) {
                jeiboost$deleteQuietly(file);
                return null;
            }
            ListTag items = root.getList("items", Tag.TAG_COMPOUND);
            final int n = items.size();
            final ItemStack[] arr = new ItemStack[n];
            final AtomicBoolean failed = new AtomicBoolean(false);
            WorkerPool.get().submit(() ->
                    IntStream.range(0, n).parallel().forEach(i -> {
                        if (failed.get()) {
                            return;
                        }
                        try {
                            Optional<ItemStack> parsed = ItemStack.parse(registryAccess, items.getCompound(i));
                            if (parsed.isPresent()) {
                                arr[i] = parsed.get();
                            } else {
                                failed.set(true);
                            }
                        } catch (Throwable t) {
                            failed.set(true);
                        }
                    })
            ).get();
            if (failed.get()) {
                jeiboost$deleteQuietly(file);
                return null;
            }
            List<ItemStack> out = new ArrayList<>(n);
            for (ItemStack stack : arr) {
                if (stack != null) {
                    out.add(stack);
                }
            }
            return out;
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            return null;
        } catch (ExecutionException e) {
            jeiboost$deleteQuietly(file);
            return null;
        } catch (Throwable t) {
            JEIBoost.LOGGER.warn("[JEIBoost] creative-tab cache read failed, rebuilding: {}", t.toString());
            jeiboost$deleteQuietly(file);
            return null;
        }
    }

    private static void jeiboost$deleteQuietly(Path file) {
        try {
            Files.deleteIfExists(file);
        } catch (IOException ignored) {
        }
    }

    private static String jeiboost$cacheKey(RegistryAccess registryAccess, IJeiClientConfigs cfgs, Minecraft mc)
            throws Exception {
        StringBuilder sb = new StringBuilder(8192);
        sb.append("fmt=").append(CACHE_FORMAT);
        sb.append("|salt=").append(Cfg.creativeTabCacheSalt());
        if (Cfg.creativeTabCacheDailyInvalidate()) {
            LocalDate today = LocalDate.now();
            sb.append("|day=").append(today.getYear()).append('-').append(today.getDayOfYear());
        }

        // client options that change which stacks create() emits
        sb.append("|hidden=").append(cfgs.getClientConfig().getShowHiddenIngredients());
        try {
            sb.append("|opTab=").append(Boolean.TRUE.equals(mc.options.operatorItemsTab().get()));
        } catch (Throwable t) {
            sb.append("|opTab=?");
        }
        sb.append("|gm=").append(mc.player != null && mc.player.canUseGameMasterBlocks());

        // installed mod set: filename + size of every jar in mods/
        List<String> jars = new ArrayList<>();
        Path modsDir = Path.of("mods");
        if (Files.isDirectory(modsDir)) {
            try (Stream<Path> s = Files.list(modsDir)) {
                s.filter(Files::isRegularFile).forEach(p -> {
                    long sz;
                    try {
                        sz = Files.size(p);
                    } catch (IOException e) {
                        sz = -1L;
                    }
                    jars.add(p.getFileName().toString() + ":" + sz);
                });
            }
        }
        Collections.sort(jars);
        sb.append("|mods=").append(jars.size());
        for (String j : jars) {
            sb.append(',').append(j);
        }

        // registry sizes
        sb.append("|item=").append(BuiltInRegistries.ITEM.size());
        sb.append("|tab=").append(BuiltInRegistries.CREATIVE_MODE_TAB.size());

        // datapack-driven registries that feed creative-tab stacks
        jeiboost$appendRegistry(sb, registryAccess, Registries.ENCHANTMENT, "ench");
        jeiboost$appendRegistry(sb, registryAccess, Registries.POTION, "potion");
        jeiboost$appendRegistry(sb, registryAccess, Registries.PAINTING_VARIANT, "paint");
        jeiboost$appendRegistry(sb, registryAccess, Registries.INSTRUMENT, "instr");
        jeiboost$appendRegistry(sb, registryAccess, Registries.TRIM_PATTERN, "trimP");
        jeiboost$appendRegistry(sb, registryAccess, Registries.TRIM_MATERIAL, "trimM");
        jeiboost$appendRegistry(sb, registryAccess, Registries.BANNER_PATTERN, "banner");

        MessageDigest md = MessageDigest.getInstance("SHA-256");
        byte[] hash = md.digest(sb.toString().getBytes(StandardCharsets.UTF_8));
        StringBuilder hex = new StringBuilder(hash.length * 2);
        for (byte b : hash) {
            hex.append(Character.forDigit((b >> 4) & 0xF, 16));
            hex.append(Character.forDigit(b & 0xF, 16));
        }
        return hex.toString();
    }

    @SuppressWarnings({"unchecked", "rawtypes"})
    private static void jeiboost$appendRegistry(StringBuilder sb, RegistryAccess registryAccess,
                                                ResourceKey key, String label) {
        sb.append('|').append(label).append('=');
        try {
            Registry reg = registryAccess.registryOrThrow(key);
            List<String> ids = new ArrayList<>();
            for (Object id : reg.keySet()) {
                ids.add(((ResourceLocation) id).toString());
            }
            Collections.sort(ids);
            sb.append(ids.size());
            for (String id : ids) {
                sb.append(',').append(id);
            }
        } catch (Throwable t) {
            sb.append("absent");
        }
    }
}
