package dev.uvfixes;

import cpw.mods.modlauncher.api.ITransformer;
import net.neoforged.neoforgespi.coremod.ICoreMod;

import java.util.List;

public class UVFixesCoreMod implements ICoreMod {
    @Override
    public Iterable<? extends ITransformer<?>> getTransformers() {
        System.out.println("[uvfixes] coremod active - registering pack-fix transformers");
        return List.of(new UVFixesTransformer());
    }
}
