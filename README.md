# mod-custom-races

Adds custom playable races to an AzerothCore 3.3.5a server, keeping every stock race
and item intact (additive only, per `AGENTS.md`'s progressive-server philosophy).

## Status: Goblin (race 9, Horde)

Not a new race -- the stock 3.3.5a client already ships this as a real, named race
slot (Goblin NPCs use it), just NPC-only (`Flags=1`, `Alliance=2` "not available").
Making it playable is a field flip, not new data invention. Model/texture/sound
assets and reference field values ported from
[mod-worgoblin](https://github.com/heyitsbench/mod-worgoblin) (verified byte-for-byte
against its actual shipped client DBC, not its own draft SQL notes, which had a stale
value in at least one field).

| Piece | Status |
|---|---|
| `chrraces_dbc` (server-side override, world DB) | Done — see `data/sql/db-world/mod_custom_races.sql` |
| `client/DBFilesClient/ChrRaces.dbc` (client copy) | Done |
| `player_race_stats`, `player_totem_model` | Done |
| `playercreateinfo` / `playercreateinfo_action` / `playercreateinfo_skills` | Done — Valley of Trials (Durotar) spawn, matches Orc/Troll; classes 1,3,4,5,6,7,8,9 (no Paladin, no Druid) |
| `item_template.allowablerace` (existing Horde gear wearable) | Done |
| `CharBaseInfo.dbc` | Done — binary edit (2-byte-per-record format, no SQL overlay support at all for this file); added Goblin rows for all ten class slots (including Paladin and Druid for ARAC) |
| `CharSections.dbc` | Done — binary edit (no `charsections_dbc` SQL-overlay table exists in this environment's base SQL, unlike `chrraces_dbc`; replaced the 6 stock NPC-only rows with worgoblin's full 1028-row player-creation set, IDs 23000-24027, no collision with existing IDs) |
| `CharHairGeosets.dbc` / `CharHairTextures.dbc` / `CharacterFacialHairStyles.dbc` | Done — binary edit, Goblin-only rows extracted from worgoblin's DBC (which also carries Worgen data — filtered strictly to `Race==9` so no Worgen rows leaked in) |
| `HelmetGeosetVisData.dbc` | **Not needed** — worgoblin's copy has the same 21 rows as ours (no Goblin-specific entries added upstream either) |
| `CharStartOutfit.dbc` | Done — binary edit, **not** worgoblin's own custom Goblin-flavored gear (that requires importing ~23 new `item_template` rows + `itemdisplayinfo_dbc` client data, out of scope for "additive only"); instead reused Orc's existing starting-kit item IDs per class (same items already in this DB), matching the "matches Orc/Troll" convention already used for Goblin's spawn point. The `charstartoutfit_dbc` SQL-overlay table exists but ships empty for every race in this environment (no race currently uses it), so the binary DBC is the only thing actually read at server startup here — went binary-only to match that existing convention rather than introduce a first user of the SQL path for zero behavioral gain. |
| Client Glue patch (`client/Interface/GlueXML/`) | Done — `MAX_RACES` 11->12; new `CharacterCreateRaceButton12` (XML) anchored as Horde's 6th slot; Goblin gets a dedicated male/female portrait (`UI-CharacterCreate-Goblin-{Male,Female}.blp`, cropped from worgoblin's edited shared atlas at column 5 rows 1/3 via `BLPConverter.exe`, since Goblin has no slot on the stock atlas at all) instead of atlas coordinates, same pattern as High Elf; missing Goblin lore text falls back to Orc's |
| Character/Sound assets | Done — copied from mod-worgoblin (`client/Character/Goblin/`, `client/Sound/character/PCGoblin*`) |
| Goblin racial mount items (Trike/Turbo-Trike) | Skipped — optional flavor content, needs spell data not yet ported |
| Goblin racial spells/abilities | Deliberately skipped — Goblin has no existing Blizzard racial-ability skill line to reuse (unlike High Elf/Blood Elf). mod-worgoblin ships one via a brand-new custom skill line + custom `Spell.dbc`/`SpellIcon.dbc` entries, which is new content creation (spell design, balance, icons), not the "port/reuse existing data" pattern used everywhere else in this module. Goblin's Orcish language grant *is* fixed (see the new `skillraceclassinfo_dbc` row below) — that was a real gap since the stock DBC has no Goblin RaceMask entry for skill 109 at all. |
| Combined MPQ packaging with High Elf | See "Deploying to a test client" below |

## Status: High Elf (race 12 client slot, Alliance)

Reskin of Blood Elf (model/skeleton/animations reused as-is), added as a new race ID
rather than reflagging Blood Elf, so Blood Elf stays Horde unchanged.

| Piece | Status |
|---|---|
| `ChrRaces.dbc` row (race 12 client slot) | Done — internal client file string is `HighElf` |
| `CharBaseInfo.dbc` (race 12 x all classes, ARAC) | Done |
| `CharSections.dbc` (appearance options) | Done, verified against renamed client textures |
| `CharStartOutfit.dbc` (starting gear) | Done, matches Human's kit per class |
| `CharacterCreateCameras.dbc` | **Missing** — not present anywhere in this environment in WotLK format; creation-screen camera will be wrong/default until supplied |
| `data/sql/db-world/mod_custom_races.sql` (playercreateinfo/action/skills) | Done — Northshire Abbey spawn, matches Human |
| Client Glue patch (`client/Interface/GlueXML/`) | Done — `MAX_RACES` 10->11; button 11 gets the generated male/female High Elf portrait directly, and missing High Elf lore text falls back to Blood Elf text |
| Core C++ race-mask patch | **Not needed** — this fork's `RaceMgr`/`Player::TeamIdForRace()` read `ChrRaces.dbc` dynamically, no hardcoded race tables to patch |
| High Elf racial spells | Done — reuses Blood Elf's real "Blood Elf Racial Traits" skill line (756: Arcane Torrent, Arcane Affinity, Magic Resistance) via `playercreateinfo_skills` + a new `skillraceclassinfo_dbc` override row, exactly like the language skills. Straight reuse, no new spell content, and thematically apt since High Elf already shares Blood Elf's whole model/kit. **Correction:** an earlier pass here had the language skill IDs wrong (754/126/756 instead of the real 98/113/137) — 756 in particular is not Thalassian at all, it's this same Blood Elf racial line; fixed in `mod_custom_races.sql`. |
| `skillraceclassinfo_dbc` override (languages + racial) | Done — without this, `Player::LearnDefaultSkill()` silently grants nothing for any race not in the stock binary DBC's RaceMask data, regardless of what `playercreateinfo_skills` says (confirmed by reading `Player.cpp`'s `GetSkillRaceClassInfo` early-return) |

## Layout

- `client/` — files that ship to the player's game client (never touched by the server):
  - `client/Character/HighElf/` — renamed Blood Elf model/texture assets
  - `client/Interface/GlueXML/` — patched character-creation screen
  - `client/DBFilesClient/` — client-side copies of the modified DBC files
- `data/sql/db-world/` — server-side world DB SQL (AzerothCore module convention)

**Two separate things, don't conflate them:**

- **What the server validates against** — for `ChrRaces`/`CharSections`/`CharStartOutfit`/
  `BarberShopStyle` specifically, this fork's `DBCStores.cpp` merges a world-DB SQL
  table (`chrraces_dbc`, etc.) on top of the raw `.dbc` at startup
  (`DBCDatabaseLoader.cpp`/`.h`). Prefer editing the SQL table (`data/sql/db-world/
  mod_custom_races.sql`) over touching `mod-azeroth-eras/build/expac/wotlk/dbc/`
  directly — reviewable, no binary tool needed. **Caveat:** confirm the override table
  actually exists in this environment's base SQL before relying on it —
  `charsections_dbc` is referenced by `DBCStores.cpp`'s `LOAD_DBC` call but the table
  itself doesn't exist anywhere under `data/sql/` here, unlike `chrraces_dbc`/
  `charstartoutfit_dbc`/`barbershopstyle_dbc`, which do. Don't `CREATE TABLE` one
  blind to work around this — `DBCDatabaseLoader::Load()` hard-`ASSERT`s the column
  count against the format string AzerothCore registers for that store, so a
  mismatched schema crashes the server on every startup. When the table is missing,
  fall back to the binary path below instead. For everything else the server never
  loads at all (`CharBaseInfo`, `CharHairGeosets`, `CharHairTextures`,
  `CharacterFacialHairStyles`, `HelmetGeosetVisData`) there's no SQL option either;
  edit the binary DBC directly with `tools/wdbc_tool.py` (a small, round-trip-verified
  WDBC reader/writer — always run it standalone against a new DBC file first,
  `python tools/wdbc_tool.py <file.dbc>`, to confirm byte-identical round-trip
  before trusting it to edit that file's shape).
- **What the client displays** — always the binary `.dbc` in `client/DBFilesClient/`,
  regardless of whether the server-side piece above was SQL or binary. The client never
  queries the world DB; there is no way around shipping it a real `.dbc` via MPQ.

## Deploying to a test client

`Patch-AA.MPQ` in this module's root is a pre-built combined archive containing the
**entire current contents of `client/`** (both High Elf and Goblin — 2710 files, ~108 MiB),
ready to drop into `Data/Patch-AA.MPQ` on a test client. Rebuild it after any change under
`client/` with:

```powershell
.\modules\mod-item-affixes\tools\mpqcreate-multi.ps1 -SourceDir .\modules\mod-custom-races\client -OutputMpq .\modules\mod-custom-races\Patch-AA.MPQ -Exclude @('*.bak','*.mpq','*.MPQ')
```

`mpqcreate-multi.ps1` is a generalization of the existing single-file `mpqcreate.ps1` to
pack a whole directory tree, preserving relative paths as internal MPQ paths (so the
folder layout under `client/` **is** the archive layout — no separate manifest to keep in
sync). Both scripts had a real bug in their MPQ block-encryption routine (the keystream's
seed accumulation was using the post-XOR ciphertext instead of the pre-XOR plaintext,
which doesn't match the real MPQ `DecryptMpqBlock` algorithm and produces a hash/block
table that looks encrypted but won't actually decrypt correctly for the client); both are
now fixed, and `Patch-AA.MPQ` was round-trip-verified by independently re-implementing the
real decrypt algorithm and extracting several files back out byte-identical to their
source (`ChrRaces.dbc`, `CharacterCreate.lua`, `GoblinMale.M2`, `CharSections.dbc`, the
Goblin portrait).

The archive retains paths like:

```text
Character/HighElf/...
Character/Goblin/...
Sound/character/PCGoblinMale/...
DBFilesClient/ChrRaces.dbc
DBFilesClient/CharBaseInfo.dbc
DBFilesClient/CharSections.dbc
DBFilesClient/CharStartOutfit.dbc
DBFilesClient/CharHairGeosets.dbc
DBFilesClient/CharHairTextures.dbc
DBFilesClient/CharacterFacialHairStyles.dbc
Interface/GlueXML/CharacterCreate.lua
Interface/GlueXML/CharacterCreate.xml
Interface/Glues/CharacterCreate/UI-CharacterCreate-HighElf-{Male,Female}.blp
Interface/Glues/CharacterCreate/UI-CharacterCreate-Goblin-{Male,Female}.blp
```

Do not depend on a loose `Data/Patch-C/` directory for GlueXML overrides. The client
must load the changed Lua/XML from the MPQ layer.

**Note:** there's a stray `Character/HighElf/Male/HighElf.mpq` (16 MiB) sitting inside
`client/` itself — an old build artifact that doesn't belong there (an MPQ isn't valid
content at that internal path). It's excluded from packaging above but hasn't been
deleted; there's also an untracked `HighElf.mpq` at the repo root that looks like an
earlier manual build of just the High Elf assets. Worth cleaning up, but left alone here
since neither was created by this session.
