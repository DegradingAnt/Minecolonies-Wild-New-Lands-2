# UltimateVibes — Custom Pack Work

Backup + source for the **custom** parts of the *Ultimate Vibes (Distant Horizons)* NeoForge 1.21.1 modpack.
No third-party mod jars are included (licensing); no secrets/tokens are included.

## Layout
- **`mods/`** — built custom add-on jars (drop-in for the instance's `mods/`):
  - `UltimateVibes-PackFixes` — runtime bytecode-fix coremod (Nashorn ASM), ~43 class-load-time guards so original mod jars stay untouched.
  - `UltimateVibes-DHSmooth` — client mixin that smooths Distant Horizons LOD draw-batch spikes (instant-return for re-shown terrain; adaptive ramp for new).
  - `UltimateVibes-MineColoniesCache` — MineColonies discovery-cache speedup + the "World mismatch" build-preview crash fix (client mixins).
  - `UltimateVibes-JEIBoost`, `-ArchersAttrFix`, `-FTBChunksOffload` — smaller targeted add-ons.
- **`src/`** — source for each custom mod (coremod JS / Java mixins + `neoforge.mods.toml` + mixin configs). `build/` outputs and `*.class` are git-ignored.
- **`datapacks/UltimateVibes-Compat/`** — the consolidated Paxi compat datapack (loot/recipe/tag/worldgen overrides + ore dupe-suppression + the entity loot-table fixes).
- **`configs/`** — the deliberately-tuned config files (DH, dynamic difficulty, EMF, logbegone, modernfix, DHSmooth, CalmTheLeaks).
- **`tools/`** — the `.uvrun` Python tooling (mod scanning, log harvesting, loot building, JFR/heap analysis, the pack export, datapack cleaner). Build/launch args and logs are intentionally excluded (they hold the MC access token).

## Building the coremod / mods
- **PackFixes**: zip the 3 files in `src/uvfixes/` (`META-INF/neoforge.mods.toml`, `META-INF/coremods.json`, `coremods/uvfixes.js`); bump the version in the toml.
- **Mixin mods (DHSmooth / MineColoniesCache / …)**: `javac --release 21` against the instance's runtime jars (sponge-mixin, mixinextras, neoforge universal+client, the target mod jars, fancymodloader `loader` for `@Mod`), then zip the classes + `META-INF/neoforge.mods.toml` + `*.mixins.json`.

_Generated as a backup of the custom work; the full playable pack lives in the CurseForge instance._
