package com.ultimatevibes.mccache.mixin;

import com.llamalad7.mixinextras.injector.wrapmethod.WrapMethod;
import com.llamalad7.mixinextras.injector.wrapoperation.Operation;
import com.minecolonies.api.util.CraftingUtils;
import com.ultimatevibes.mccache.MineColoniesCache;
import net.minecraft.core.HolderLookup;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.core.registries.Registries;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.ListTag;
import net.minecraft.nbt.NbtAccounter;
import net.minecraft.nbt.NbtIo;
import net.minecraft.nbt.Tag;
import net.minecraft.resources.ResourceKey;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.item.CreativeModeTab;
import net.minecraft.world.item.ItemStack;
import org.spongepowered.asm.mixin.Mixin;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Collections;
import java.util.List;
import java.util.Optional;
import java.util.function.BiConsumer;
import java.util.stream.Stream;

/**
 * Caches CraftingUtils.forEachCreativeTabItems — the ~6.7s creative-tab scan
 * MineColonies' CompatibilityManager.discoverAllItems runs on the Server thread
 * at every world join. On a cache HIT we replay the recorded (tab -> items)
 * calls and skip the rebuild; on a MISS we record the calls, let the original
 * run, and write the result to disk on a background thread. Result depends only
 * on the installed mods + datapack registries that feed tab stacks, so it is
 * keyed on that state and self-heals on any mismatch (full rescan).
 */
@Mixin(value = CraftingUtils.class, remap = false)
public abstract class CraftingUtilsMixin {

    private static final int FMT = 1;
    /** single-slot in-memory cache: serves the client deserialize pass in the same SP JVM */
    private static volatile String uvmc$memKey;
    private static volatile List<Object[]> uvmc$memCalls; // each = {ResourceLocation tabId, List<ItemStack> stacks}

    @WrapMethod(method = "forEachCreativeTabItems")
    private static void uvmc$cache(CreativeModeTab.ItemDisplayParameters params,
                                   BiConsumer<CreativeModeTab, Collection<ItemStack>> consumer,
                                   Operation<Void> original) {
        HolderLookup.Provider provider = params.holders();
        String key;
        try {
            key = uvmc$key(provider);
        } catch (Throwable t) {
            original.call(params, consumer);
            return;
        }

        List<Object[]> cached = key.equals(uvmc$memKey) ? uvmc$memCalls : null;
        if (cached == null) {
            cached = uvmc$readDisk(key, provider);
        }
        if (cached != null && uvmc$replay(cached, consumer)) {
            uvmc$memKey = key;
            uvmc$memCalls = cached;
            MineColoniesCache.LOGGER.info("[uvmccache] discovery cache HIT: {} tab-calls replayed", cached.size());
            return;
        }

        // miss: record each (tab, stacks) call, run original, write to disk
        final List<Object[]> rec = new ArrayList<>();
        long t0 = System.nanoTime();
        original.call(params, (BiConsumer<CreativeModeTab, Collection<ItemStack>>) (tab, stacks) -> {
            ResourceLocation id = BuiltInRegistries.CREATIVE_MODE_TAB.getKey(tab);
            if (id != null) {
                rec.add(new Object[]{id, new ArrayList<>(stacks)});
            }
            consumer.accept(tab, stacks);
        });
        uvmc$memKey = key;
        uvmc$memCalls = rec;
        uvmc$writeDiskAsync(key, rec, provider);
        MineColoniesCache.LOGGER.info("[uvmccache] discovery cache MISS: recorded {} tab-calls in {} ms (writing)",
                rec.size(), (System.nanoTime() - t0) / 1_000_000L);
    }

    private static boolean uvmc$replay(List<Object[]> calls, BiConsumer<CreativeModeTab, Collection<ItemStack>> consumer) {
        // resolve all tabs first; any unresolvable => treat as miss (return false)
        for (Object[] c : calls) {
            if (BuiltInRegistries.CREATIVE_MODE_TAB.getOptional((ResourceLocation) c[0]).isEmpty()) {
                return false;
            }
        }
        for (Object[] c : calls) {
            CreativeModeTab tab = BuiltInRegistries.CREATIVE_MODE_TAB.getOptional((ResourceLocation) c[0]).orElse(null);
            if (tab == null) {
                return false;
            }
            @SuppressWarnings("unchecked")
            List<ItemStack> stacks = (List<ItemStack>) c[1];
            consumer.accept(tab, stacks);
        }
        return true;
    }

    private static Path uvmc$file() {
        return Path.of("local", "uvmccache", "discovery.nbt");
    }

    private static List<Object[]> uvmc$readDisk(String key, HolderLookup.Provider provider) {
        Path f = uvmc$file();
        if (!Files.isRegularFile(f)) {
            return null;
        }
        try {
            CompoundTag root = NbtIo.readCompressed(f, NbtAccounter.unlimitedHeap());
            if (root.getInt("v") != FMT || !key.equals(root.getString("key"))) {
                Files.deleteIfExists(f);
                return null;
            }
            ListTag callsTag = root.getList("calls", Tag.TAG_COMPOUND);
            List<Object[]> out = new ArrayList<>(callsTag.size());
            for (int i = 0; i < callsTag.size(); i++) {
                CompoundTag ct = callsTag.getCompound(i);
                ResourceLocation id = ResourceLocation.parse(ct.getString("tab"));
                ListTag items = ct.getList("items", Tag.TAG_COMPOUND);
                List<ItemStack> stacks = new ArrayList<>(items.size());
                for (int j = 0; j < items.size(); j++) {
                    Optional<ItemStack> s = ItemStack.parse(provider, items.getCompound(j));
                    if (s.isEmpty()) {
                        Files.deleteIfExists(f);
                        return null;
                    }
                    stacks.add(s.get());
                }
                out.add(new Object[]{id, stacks});
            }
            return out;
        } catch (Throwable t) {
            try {
                Files.deleteIfExists(f);
            } catch (IOException ignored) {
            }
            MineColoniesCache.LOGGER.warn("[uvmccache] cache read failed, rebuilding: {}", t.toString());
            return null;
        }
    }

    private static void uvmc$writeDiskAsync(String key, List<Object[]> calls, HolderLookup.Provider provider) {
        Thread w = new Thread(() -> {
            try {
                ListTag callsTag = new ListTag();
                for (Object[] c : calls) {
                    CompoundTag ct = new CompoundTag();
                    ct.putString("tab", c[0].toString());
                    ListTag items = new ListTag();
                    @SuppressWarnings("unchecked")
                    List<ItemStack> stacks = (List<ItemStack>) c[1];
                    for (ItemStack s : stacks) {
                        if (!s.isEmpty()) {
                            items.add(s.save(provider));
                        }
                    }
                    ct.put("items", items);
                    callsTag.add(ct);
                }
                CompoundTag root = new CompoundTag();
                root.putInt("v", FMT);
                root.putString("key", key);
                root.put("calls", callsTag);

                Path f = uvmc$file();
                Files.createDirectories(f.getParent());
                Path tmp = f.resolveSibling("discovery.nbt.tmp");
                NbtIo.writeCompressed(root, tmp);
                try {
                    Files.move(tmp, f, StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.ATOMIC_MOVE);
                } catch (IOException atomicFailed) {
                    Files.move(tmp, f, StandardCopyOption.REPLACE_EXISTING);
                }
                MineColoniesCache.LOGGER.info("[uvmccache] discovery cache written ({} tab-calls)", calls.size());
            } catch (Throwable t) {
                MineColoniesCache.LOGGER.warn("[uvmccache] cache write failed (live scan next join): {}", t.toString());
            }
        }, "uvmccache-write");
        w.setDaemon(true);
        w.setPriority(Thread.MIN_PRIORITY);
        w.start();
    }

    private static String uvmc$key(HolderLookup.Provider provider) throws Exception {
        StringBuilder sb = new StringBuilder(8192);
        sb.append("fmt=").append(FMT).append("|salt=").append(MineColoniesCache.SALT);

        List<String> jars = new ArrayList<>();
        Path mods = Path.of("mods");
        if (Files.isDirectory(mods)) {
            try (Stream<Path> s = Files.list(mods)) {
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
        sb.append("|item=").append(BuiltInRegistries.ITEM.size());
        sb.append("|tab=").append(BuiltInRegistries.CREATIVE_MODE_TAB.size());
        uvmc$reg(sb, provider, Registries.ENCHANTMENT, "ench");
        uvmc$reg(sb, provider, Registries.POTION, "pot");
        uvmc$reg(sb, provider, Registries.PAINTING_VARIANT, "paint");
        uvmc$reg(sb, provider, Registries.INSTRUMENT, "instr");
        uvmc$reg(sb, provider, Registries.TRIM_PATTERN, "trimP");
        uvmc$reg(sb, provider, Registries.TRIM_MATERIAL, "trimM");
        uvmc$reg(sb, provider, Registries.BANNER_PATTERN, "banner");

        MessageDigest md = MessageDigest.getInstance("SHA-256");
        byte[] h = md.digest(sb.toString().getBytes(StandardCharsets.UTF_8));
        StringBuilder hex = new StringBuilder(h.length * 2);
        for (byte b : h) {
            hex.append(Character.forDigit((b >> 4) & 0xF, 16));
            hex.append(Character.forDigit(b & 0xF, 16));
        }
        return hex.toString();
    }

    @SuppressWarnings({"unchecked", "rawtypes"})
    private static void uvmc$reg(StringBuilder sb, HolderLookup.Provider provider, ResourceKey key, String label) {
        sb.append('|').append(label).append('=');
        try {
            Optional<? extends HolderLookup.RegistryLookup<?>> lo = provider.lookup(key);
            if (lo.isEmpty()) {
                sb.append("absent");
                return;
            }
            List<String> ids = new ArrayList<>();
            lo.get().listElementIds().forEach(rk -> ids.add(((ResourceKey) rk).location().toString()));
            Collections.sort(ids);
            sb.append(ids.size());
            for (String id : ids) {
                sb.append(',').append(id);
            }
        } catch (Throwable t) {
            sb.append("err");
        }
    }
}
