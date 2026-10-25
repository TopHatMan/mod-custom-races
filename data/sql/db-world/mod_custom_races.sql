-- Goblin (race 9): the stock 3.3.5a client already ships this as a real, named
-- race slot (used by Goblin NPCs) -- it's just NPC-only (Flags=1, Alliance=2
-- "not available", TeamID/BaseLanguage=7). Making it playable server-side is a
-- pure field flip, not a new race. This does NOT edit the server's own copy of
-- ChrRaces.dbc -- it writes to `chrraces_dbc`, the world-DB override table
-- AzerothCore's own DBC loader merges on top of the raw .dbc at startup
-- (DBCStores.cpp: `LOAD_DBC(sChrRacesStore, "ChrRaces.dbc", "chrraces_dbc")`,
-- mechanism in DBCDatabaseLoader.cpp/.h). This ONLY affects what the SERVER
-- validates (race/class checks, etc.) -- it has no effect on what the client
-- displays. The client needs its own binary-edited ChrRaces.dbc shipped via
-- MPQ regardless (see client/DBFilesClient/ChrRaces.dbc in this module).
-- Values below are read byte-for-byte from mod-worgoblin's actual shipped
-- client DBC (github.com/heyitsbench/mod-worgoblin), not guessed and not
-- taken from that repo's own draft SQL notes (which had a stale Flags value
-- that disagreed with what they actually shipped).
DELETE FROM `chrraces_dbc` WHERE `ID` = 9;
INSERT INTO `chrraces_dbc`
  (`ID`, `Flags`, `FactionID`, `ExplorationSoundID`, `MaleDisplayId`, `FemaleDisplayId`,
   `ClientPrefix`, `BaseLanguage`, `CreatureType`, `ResSicknessSpellID`, `SplashSoundID`,
   `ClientFilestring`, `CinematicSequenceID`, `Alliance`, `Name_Lang_enUS`)
VALUES
  (9, 4, 2, 4141, 6894, 6895, 'Go', 1, 7, 15007, 1096, 'Goblin', 141, 1, 'Goblin');

-- High Elf (race 12): Alliance race using the Blood Elf model family.
DELETE FROM `chrraces_dbc` WHERE `ID` = 12;
INSERT INTO `chrraces_dbc`
  (`ID`, `Flags`, `FactionID`, `ExplorationSoundID`, `MaleDisplayId`, `FemaleDisplayId`,
   `ClientPrefix`, `BaseLanguage`, `CreatureType`, `ResSicknessSpellID`, `SplashSoundID`,
   `ClientFilestring`, `CinematicSequenceID`, `Alliance`, `Name_Lang_enUS`)
VALUES
  (12, 12, 1, 4140, 15476, 15475, 'He', 7, 7, 15007, 1096, 'HighElf', 81, 0, 'High Elf');

-- Goblin racial stat modifiers. Not present in base data at all (stock Goblin
-- was NPC-only, so Blizzard never needed player stat mods for it). Values
-- verified against mod-worgoblin's shipped data (github.com/heyitsbench/mod-worgoblin).
DELETE FROM `player_race_stats` WHERE `Race` = 9;
INSERT INTO `player_race_stats` (`Race`, `Strength`, `Agility`, `Stamina`, `Intellect`, `Spirit`) VALUES
(9, -3, 2, 0, 3, -2);

-- Goblin-specific totem models (Goblin gets Shaman, class 7, below -- without
-- this, totems would render with a default/incorrect appearance for this race).
DELETE FROM `player_totem_model` WHERE `RaceID` = 9;
INSERT INTO `player_totem_model` (`TotemID`, `RaceID`, `ModelID`) VALUES
(1, 9, 4589),
(2, 9, 4588),
(3, 9, 4587),
(4, 9, 4590);

-- Goblin (race 9) starting position: shares the Orc/Troll spawn (Valley of
-- Trials, Durotar) for every class in the fork's ARAC setup. Death Knight (6)
-- keeps its own Ebon Hold start regardless of race, same convention as every
-- other race in this file. Position verified against mod-worgoblin's data.
DELETE FROM `playercreateinfo` WHERE `race` = 9;
INSERT INTO `playercreateinfo` (`race`, `class`, `map`, `zone`, `position_x`, `position_y`, `position_z`, `orientation`) VALUES
(9, 1, 1, 14, -618.518, -4251.67, 38.718, 0),
(9, 2, 1, 14, -618.518, -4251.67, 38.718, 0),
(9, 3, 1, 14, -618.518, -4251.67, 38.718, 0),
(9, 4, 1, 14, -618.518, -4251.67, 38.718, 0),
(9, 5, 1, 14, -618.518, -4251.67, 38.718, 0),
(9, 6, 609, 4298, 2358.44, -5666.9, 426.023, 3.65997),
(9, 7, 1, 14, -618.518, -4251.67, 38.718, 0),
(9, 8, 1, 14, -618.518, -4251.67, 38.718, 0),
(9, 9, 1, 14, -618.518, -4251.67, 38.718, 0),
(9, 11, 1, 14, -618.518, -4251.67, 38.718, 0);

-- Default action bar button 0 (class-bound ability). 6603 = Attack, the same
-- generic melee-start action already used for every other physical class in
-- this file; Priest/Mage/Warlock reuse their own real starting spells,
-- matching the High Elf block below exactly.
DELETE FROM `playercreateinfo_action` WHERE `race` = 9 AND `button` = 0;
INSERT INTO `playercreateinfo_action` (`race`, `class`, `button`, `action`, `type`) VALUES
(9, 1, 0, 6603, 0),
(9, 2, 0, 6603, 0),
(9, 3, 0, 6603, 0),
(9, 4, 0, 6603, 0),
(9, 5, 0, 585, 0),
(9, 6, 0, 6603, 0),
(9, 7, 0, 6603, 0),
(9, 8, 0, 133, 0),
(9, 9, 0, 686, 0),
(9, 11, 0, 5176, 0);

-- Languages and racial skill line. Goblins are Horde so they need Orcish (shared
-- Horde trade tongue). Skill 790 is the custom Goblin racial line used by the
-- reference client/server data; the spell definitions remain deliberately
-- separate from this race bootstrap so a missing optional racial spell cannot
-- prevent the race and language data from loading.
-- Skill ID 109 verified directly against mod-worgoblin's own shipped SQL
-- (its comment reads "-- Orcish language goblins" on the exact same update).
-- raceMask = 1 << (raceId - 1) = 1 << 8 = 256 for race 9.
DELETE FROM `playercreateinfo_skills` WHERE `raceMask` = 256 AND `classMask` = 0 AND `skill` IN (109, 790);
INSERT INTO `playercreateinfo_skills` (`raceMask`, `classMask`, `skill`, `rank`, `comment`) VALUES
(256, 0, 109, 0, 'Goblin - Orcish (Horde trade language)'),
(256, 0, 790, 0, 'Goblin - Racial Traits');

-- Goblin's custom racial skill line. These are the same IDs used by the
-- working mod-worgoblin client data. The corresponding custom Spell.dbc rows
-- are not part of the stock server DBC and must be installed alongside this
-- SQL before the active abilities are enabled.
DELETE FROM `skillline_dbc` WHERE `ID` = 790;
INSERT INTO `skillline_dbc`
  (`ID`, `CategoryID`, `SkillCostsID`, `DisplayName_Lang_enUS`, `DisplayName_Lang_enGB`,
   `DisplayName_Lang_Mask`, `Description_Lang_Mask`, `SpellIconID`, `CanLink`)
VALUES
  (790, 9, 0, 'Racial - Goblin', '', 16712190, 16712172, 133032, 0);

DELETE FROM `skillraceclassinfo_dbc` WHERE `ID` = 20007;
INSERT INTO `skillraceclassinfo_dbc`
  (`ID`, `SkillID`, `RaceMask`, `ClassMask`, `Flags`, `MinLevel`, `SkillTierID`, `SkillCostIndex`)
VALUES
  (20007, 790, 256, 1535, 1170, 0, 0, 0);

-- Let Goblin wear existing Orc-wearable gear. Race restrictions on items are
-- a bitmask (allowablerace); a brand-new race bit is unset on every existing
-- item, so without this Goblin could not equip most existing Horde gear at
-- all. This is deliberately broad (touches every item_template row matching
-- the condition) -- ported byte-for-byte from mod-worgoblin's own tested
-- statement rather than rewritten, specifically because it already excludes
-- the "already means every race" sentinel bitmask values (-1, and the
-- (1<<N)-1 values for each historical race count) so those aren't
-- needlessly rewritten.
UPDATE `item_template` SET `allowablerace` = `allowablerace`|256 WHERE `allowablerace` & 2 AND `allowablerace` != -1 AND `allowablerace` != 2147483647 AND `allowablerace` != 2047 AND `allowablerace` != 4095 AND `allowablerace` != 8191 AND `allowablerace` != 16383 AND `allowablerace` != 32767 AND `allowablerace` != 65535 AND `allowablerace` != 131071 AND `allowablerace` != 262143 AND `allowablerace` != 524287 AND `allowablerace` != 1048575 AND `allowablerace` != 2097151;

-- High Elf uses Blood Elf's racial stat modifiers and Human-compatible Alliance gear.
DELETE FROM `player_race_stats` WHERE `Race` = 12;
INSERT INTO `player_race_stats` (`Race`, `Strength`, `Agility`, `Stamina`, `Intellect`, `Spirit`) VALUES
(12, -3, 2, 0, 3, -2);

UPDATE `item_template`
SET `allowablerace` = `allowablerace` | 2048
WHERE (`allowablerace` & 1) != 0
  AND `allowablerace` NOT IN (-1, 2047, 4095, 8191, 16383, 32767, 65535,
                             131071, 262143, 524287, 1048575, 2097151,
                             4194303);

-- High Elf (race 12) starting position: shares Human's spawn (Northshire Abbey area,
-- Elwynn Forest) for every class Human natively supports. Death Knight (class 6) keeps
-- the class's own Ebon Hold start regardless of race, matching Human's own row.
DELETE FROM `playercreateinfo` WHERE `race` = 12;
INSERT INTO `playercreateinfo` (`race`, `class`, `map`, `zone`, `position_x`, `position_y`, `position_z`, `orientation`) VALUES
(12, 1, 0, 12, -8949.95, -132.493, 83.5312, 0),
(12, 2, 0, 12, -8949.95, -132.493, 83.5312, 0),
(12, 3, 0, 12, -8949.95, -132.493, 83.5312, 0),
(12, 4, 0, 12, -8949.95, -132.493, 83.5312, 0),
(12, 5, 0, 12, -8949.95, -132.493, 83.5312, 0),
(12, 6, 609, 4298, 2355.84, -5664.77, 426.028, 3.65997),
(12, 7, 0, 12, -8949.95, -132.493, 83.5312, 0),
(12, 8, 0, 12, -8949.95, -132.493, 83.5312, 0),
(12, 9, 0, 12, -8949.95, -132.493, 83.5312, 0),
(12, 11, 0, 12, -8949.95, -132.493, 83.5312, 0);

-- Default action bar button 0 (class-bound ability), copied from Human's rows.
DELETE FROM `playercreateinfo_action` WHERE `race` = 12 AND `button` = 0;
INSERT INTO `playercreateinfo_action` (`race`, `class`, `button`, `action`, `type`) VALUES
(12, 1, 0, 6603, 0),
(12, 2, 0, 6603, 0),
(12, 3, 0, 6603, 0),
(12, 4, 0, 6603, 0),
(12, 5, 0, 585, 0),
(12, 6, 0, 6603, 0),
(12, 7, 0, 6603, 0),
(12, 8, 0, 133, 0),
(12, 9, 0, 686, 0),
(12, 11, 0, 5176, 0);

-- Languages. High Elves are Alliance so they still need Common (shared Alliance trade
-- tongue, same skill Human uses), plus both Darnassian and Thalassian since High Elves
-- are kin to Night Elves and Blood Elves.
-- Common=98, Darnassian=113, and Thalassian=137. Skill 754 is the real Human
-- racial line, while 756 is the real Blood Elf racial line; both are reused
-- intentionally below. Confirmed directly against data/sql/base/db_world/
-- playercreateinfo_skills.sql's own comments this time: Common=98, Darnassian=113,
-- Thalassian=137. Also added 756 (Blood Elf Racial, grants Arcane Torrent / Arcane
-- Affinity / Magic Resistance via the stock SkillLineAbility.dbc auto-learn data) --
-- High Elf keeps the useful Blood Elf traits and also receives the Human racial
-- skill line for its Alliance identity in the Human starter zone.
-- raceMask = 1 << (raceId - 1) = 1 << 11 for race 12, confirmed against existing rows
-- (Human=1, Night Elf=8, Blood Elf=512, Draenei=1024, ...).
DELETE FROM `playercreateinfo_skills` WHERE `raceMask` = 2048 AND `classMask` = 0 AND `skill` IN (754, 126, 756, 98, 113, 137);
INSERT INTO `playercreateinfo_skills` (`raceMask`, `classMask`, `skill`, `rank`, `comment`) VALUES
(2048, 0, 98, 0, 'High Elf - Common (Alliance trade language)'),
(2048, 0, 754, 0, 'High Elf - Human Racial Traits (Diplomacy, Human Spirit, Perception, weapon specializations)'),
(2048, 0, 113, 0, 'High Elf - Darnassian (kin to Night Elves)'),
(2048, 0, 137, 0, 'High Elf - Thalassian (kin to Blood Elves)'),
(2048, 0, 756, 0, 'High Elf - Blood Elf Racial Traits (Arcane Torrent, Arcane Affinity, Magic Resistance)');

-- SkillRaceClassInfo.dbc override: LearnDefaultSkill() (Player.cpp) calls
-- GetSkillRaceClassInfo(skill, race, class) and returns early -- granting nothing --
-- if it comes back null. The stock binary SkillRaceClassInfo.dbc only has RaceMask
-- entries for real historical races, so without these rows NONE of the skills above
-- (for High Elf) or Orcish (for Goblin, below) actually get granted, even though the
-- playercreateinfo_skills rows exist -- a silent no-op, not a visible error. Verified
-- the stock per-skill "base" row shape directly from the raw binary DBC (wdbc_tool.py):
-- ClassMask=1535 (all classes), Flags=128, SkillTierID=0 for every existing language's
-- own base row (e.g. Blood Elf's Thalassian row is (43, 137, 512, 1535, 128, 0, 0, 0)),
-- and Blood Elf's own Racial-line row is (173, 756, 512, 1535, 146, 0, 0, 0) -- reused
-- that same Flags value (146) for the new race's copy of skill 756. IDs 20001+ are
-- fresh (existing binary data tops out at 186), so these are pure additions merged in
-- by DBCDatabaseLoader's SQL-overlay, nothing existing is touched or overridden.
DELETE FROM `skillraceclassinfo_dbc` WHERE `ID` BETWEEN 20001 AND 20010;
INSERT INTO `skillraceclassinfo_dbc` (`ID`, `SkillID`, `RaceMask`, `ClassMask`, `Flags`, `MinLevel`, `SkillTierID`, `SkillCostIndex`) VALUES
(20001, 98, 2048, 1535, 128, 0, 0, 0),
(20006, 754, 2048, 1535, 128, 0, 0, 0),
(20002, 113, 2048, 1535, 128, 0, 0, 0),
(20003, 137, 2048, 1535, 128, 0, 0, 0),
(20004, 756, 2048, 1535, 146, 0, 0, 0),
(20005, 109, 256, 1535, 128, 0, 0, 0);
