"""Build a reference-client patch tree with High Elf records in client slot 12."""

from __future__ import annotations

import os
import shutil
import struct
import sys
from pathlib import Path


AVAILABLE_CLIENT_ASSETS: set[str] = set()


def read_wdbc(path: Path):
    data = path.read_bytes()
    magic, count, fields, record_size, string_size = struct.unpack_from("<4sIIII", data)
    if magic != b"WDBC" or record_size % 4:
        raise ValueError(f"Unsupported DBC: {path}")
    records_end = 20 + count * record_size
    if records_end + string_size != len(data):
        raise ValueError(f"Invalid DBC length: {path}")
    records = [list(struct.unpack_from(f"<{record_size // 4}I", data, 20 + i * record_size)) for i in range(count)]
    return fields, record_size, records, data[records_end:]


def write_wdbc(path: Path, fields: int, record_size: int, records, strings: bytes):
    header = struct.pack("<4sIIII", b"WDBC", len(records), fields, record_size, len(strings))
    body = b"".join(struct.pack(f"<{fields}I", *record) for record in records)
    path.write_bytes(header + body + strings)


def append_strings(strings: bytearray, text: bytes) -> int:
    if not text:
        return 0
    existing = bytes(strings).find(text + b"\0")
    if existing >= 0:
        return existing
    offset = len(strings)
    strings.extend(text + b"\0")
    return offset


def remap_string_refs(record, old_strings: bytes, new_strings: bytearray, fields):
    record = record[:]
    for field in fields:
        offset = record[field]
        if offset == 0:
            continue
        end = old_strings.find(b"\0", offset)
        if offset >= len(old_strings) or end < 0:
            raise ValueError(f"Invalid string offset {offset} in field {field}")
        record[field] = append_strings(new_strings, old_strings[offset:end])
    return record


def merge_append(dst: Path, src: Path, predicate, string_fields=()):
    d_fields, d_size, d_records, d_strings = read_wdbc(dst)
    s_fields, s_size, s_records, s_strings = read_wdbc(src)
    if (d_fields, d_size) != (s_fields, s_size):
        raise ValueError(f"DBC shape mismatch: {dst} vs {src}")
    strings = bytearray(d_strings)
    for record in s_records:
        if predicate(record):
            d_records.append(remap_string_refs(record, s_strings, strings, string_fields))
    write_wdbc(dst, d_fields, d_size, d_records, bytes(strings))


def append_packed_records(dst: Path, src: Path, predicate):
    """Append records from a DBC whose on-disk row is not fields*4 bytes."""
    d_data = dst.read_bytes()
    s_data = src.read_bytes()
    d_magic, d_count, d_fields, d_size, d_strings_size = struct.unpack_from("<4sIIII", d_data)
    s_magic, s_count, s_fields, s_size, s_strings_size = struct.unpack_from("<4sIIII", s_data)
    if d_magic != b"WDBC" or s_magic != b"WDBC" or (d_size, d_fields) != (s_size, s_fields):
        raise ValueError(f"Packed DBC shape mismatch: {dst} vs {src}")
    d_records_end = 20 + d_count * d_size
    s_records_end = 20 + s_count * s_size
    records = [s_data[20 + i * s_size:20 + (i + 1) * s_size] for i in range(s_count)]
    selected = [record for record in records if predicate(record)]
    output = bytearray(d_data[:d_records_end])
    output[4:8] = struct.pack("<I", d_count + len(selected))
    for record in selected:
        output.extend(record)
    output.extend(d_data[d_records_end:d_records_end + d_strings_size])
    dst.write_bytes(bytes(output))


def append_packed_remapped_records(dst: Path, src: Path, predicate, offsets):
    """Append packed records after replacing selected one-byte race fields."""
    d_data = dst.read_bytes()
    s_data = src.read_bytes()
    d_magic, d_count, d_fields, d_size, d_strings_size = struct.unpack_from("<4sIIII", d_data)
    s_magic, s_count, s_fields, s_size, _ = struct.unpack_from("<4sIIII", s_data)
    if d_magic != b"WDBC" or s_magic != b"WDBC" or (d_size, d_fields) != (s_size, s_fields):
        raise ValueError(f"Packed DBC shape mismatch: {dst} vs {src}")
    selected = []
    for i in range(s_count):
        record = bytearray(s_data[20 + i * s_size:20 + (i + 1) * s_size])
        if predicate(record):
            for offset in offsets:
                record[offset] = 12
            selected.append(record)
    records_end = 20 + d_count * d_size
    output = bytearray(d_data[:records_end])
    output[4:8] = struct.pack("<I", d_count + len(selected))
    for record in selected:
        output.extend(record)
    output.extend(d_data[records_end:records_end + d_strings_size])
    dst.write_bytes(bytes(output))


def remove_packed_records(dst: Path, predicate):
    """Remove packed rows matching predicate while preserving the DBC shape."""
    data = dst.read_bytes()
    magic, count, fields, size, strings_size = struct.unpack_from("<4sIIII", data)
    records_end = 20 + count * size
    records = [data[20 + i * size:20 + (i + 1) * size] for i in range(count)]
    records = [record for record in records if not predicate(record)]
    output = bytearray(struct.pack("<4sIIII", magic, len(records), fields, size, strings_size))
    output.extend(b"".join(records))
    output.extend(data[records_end:records_end + strings_size])
    dst.write_bytes(bytes(output))


def clone_wdbc_row(dst: Path, source_id, new_id, replacements, string_replacements=None):
    """Clone one ordinary WDBC row, remapping selected integer/string fields."""
    fields, size, records, strings = read_wdbc(dst)
    source = next((r[:] for r in records if r[0] == source_id), None)
    if source is None:
        raise ValueError(f"DBC row {source_id} not found in {dst}")
    source[0] = new_id
    for field, value in replacements.items():
        source[field] = value
    strings = bytearray(strings)
    for field, value in (string_replacements or {}).items():
        source[field] = append_strings(strings, value.encode("ascii"))
    records.append(source)
    write_wdbc(dst, fields, size, records, bytes(strings))


def append_packed_clones(dst: Path, predicate, replacements):
    """Clone matching packed rows and replace selected byte offsets."""
    data = dst.read_bytes()
    magic, count, fields, size, strings_size = struct.unpack_from("<4sIIII", data)
    records_end = 20 + count * size
    records = [bytearray(data[20 + i * size:20 + (i + 1) * size]) for i in range(count)]
    for record in list(records):
        if predicate(record):
            clone = bytearray(record)
            for offset, value in replacements.items():
                clone[offset] = value
            records.append(clone)
    output = bytearray(struct.pack("<4sIIII", magic, len(records), fields, size, strings_size))
    output.extend(b"".join(records))
    output.extend(data[records_end:records_end + strings_size])
    dst.write_bytes(bytes(output))


def append_packed_clones_from_same_file(dst: Path, predicate, replacements):
    """Clone matching packed rows already present in a DBC and rewrite bytes."""
    data = dst.read_bytes()
    magic, count, fields, size, strings_size = struct.unpack_from("<4sIIII", data)
    records_end = 20 + count * size
    records = [bytearray(data[20 + i * size:20 + (i + 1) * size]) for i in range(count)]
    clones = []
    for record in records:
        if predicate(record):
            clone = bytearray(record)
            for offset, value in replacements.items():
                clone[offset] = value
            clones.append(clone)
    output = bytearray(struct.pack("<4sIIII", magic, count + len(clones), fields, size, strings_size))
    output.extend(b"".join(records))
    output.extend(b"".join(clones))
    output.extend(data[records_end:records_end + strings_size])
    dst.write_bytes(bytes(output))


def remap_path(value: bytes) -> bytes:
    """Rename Blood Elf asset paths to the custom High Elf asset paths."""
    candidate = value.replace(b"Character\\BloodElf\\", b"Character\\HighElf\\").replace(b"BloodElf", b"HighElf")
    # The recolor package does not contain every Blood Elf customization
    # variant. Keep the stock path for variants it does not provide instead
    # of writing a DBC reference to a nonexistent file.
    if candidate.decode("latin1").lower() in AVAILABLE_CLIENT_ASSETS:
        return candidate
    return value


def append_packed_path_remapped_records(dst: Path, src: Path, predicate, race_offset, string_fields):
    """Append packed rows, changing race and remapping selected asset paths."""
    d_data = dst.read_bytes()
    s_data = src.read_bytes()
    d_magic, d_count, d_fields, d_size, d_strings_size = struct.unpack_from("<4sIIII", d_data)
    s_magic, s_count, s_fields, s_size, s_strings_size = struct.unpack_from("<4sIIII", s_data)
    if d_magic != b"WDBC" or s_magic != b"WDBC" or (d_size, d_fields) != (s_size, s_fields):
        raise ValueError(f"Packed DBC shape mismatch: {dst} vs {src}")
    source_strings = s_data[20 + s_count * s_size:20 + s_count * s_size + s_strings_size]
    target_strings = bytearray(d_data[20 + d_count * d_size:20 + d_count * d_size + d_strings_size])
    selected = []
    for i in range(s_count):
        record = bytearray(s_data[20 + i * s_size:20 + (i + 1) * s_size])
        if predicate(record):
            record[race_offset] = 12
            for field in string_fields:
                offset = struct.unpack_from("<I", record, field)[0]
                if offset == 0:
                    continue
                end = source_strings.find(b"\0", offset)
                if end < 0:
                    raise ValueError(f"Invalid string offset {offset} in field {field}")
                record[field:field + 4] = struct.pack("<I", append_strings(target_strings, remap_path(source_strings[offset:end])))
            selected.append(record)
    records_end = 20 + d_count * d_size
    output = bytearray(d_data[:records_end])
    output[4:8] = struct.pack("<I", d_count + len(selected))
    output[16:20] = struct.pack("<I", len(target_strings))
    output.extend(b"".join(selected))
    output.extend(target_strings)
    dst.write_bytes(bytes(output))


def duplicate_rows_with_path_remap(dst: Path, race_field, source_race, target_race):
    """Duplicate ordinary DBC rows while remapping Blood Elf asset paths."""
    fields, size, records, strings = read_wdbc(dst)
    strings = bytearray(strings)
    next_id = max(r[0] for r in records) + 1
    clones = []
    for record in records[:]:
        if record[race_field] != source_race:
            continue
        clone = record[:]
        clone[0] = next_id + len(clones)
        clone[race_field] = target_race
        for field, offset in enumerate(clone):
            if field == 0 or offset == 0 or offset >= len(strings):
                continue
            end = strings.find(b"\0", offset)
            if end < 0:
                continue
            value = bytes(strings[offset:end])
            if b"Character\\BloodElf\\" in value:
                clone[field] = append_strings(strings, remap_path(value))
        clones.append(clone)
    records.extend(clones)
    write_wdbc(dst, fields, size, records, bytes(strings))


def main():
    repo = Path(__file__).resolve().parents[3]
    reference = Path(os.environ.get("WORGOBLIN_REFERENCE", Path(os.environ["TEMP"]) / "mod-worgoblin-reference"))
    reference_patch = reference / "data" / "patch"
    current_client = repo / "modules" / "mod-custom-races" / "client"
    global AVAILABLE_CLIENT_ASSETS
    AVAILABLE_CLIENT_ASSETS = {
        str(path.relative_to(current_client)).replace(os.sep, "\\").lower()
        for path in current_client.rglob("*")
        if path.is_file()
    }
    output = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(os.environ["TEMP"]) / "ashbringer-reference-races"
    if not reference_patch.is_dir():
        raise SystemExit(f"Reference patch tree not found: {reference_patch}")
    if output.exists():
        shutil.rmtree(output)
    shutil.copytree(reference_patch, output)

    # Preserve the reference patch's complete Goblin/client dependency tree.
    for relative in [
        "Character/HighElf",
        "Interface/Glues/CharacterCreate/UI-CharacterCreate-HighElf-Female.blp",
        "Interface/Glues/CharacterCreate/UI-CharacterCreate-HighElf-Male.blp",
        "Interface/Glues/CharacterCreate/UI-CharacterCreate-Goblin-Female.blp",
        "Interface/Glues/CharacterCreate/UI-CharacterCreate-Goblin-Male.blp",
        "Interface/GlueXML/CharacterCreate.lua",
        "Interface/GlueXML/CharacterCreate.xml",
    ]:
        source = current_client / relative
        target = output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            shutil.copytree(source, target)
        else:
            shutil.copy2(source, target)

    # Custom race names do not have stock Glue ambience tracks. Avoid the
    # non-fatal Lua usage popup by using the reference screen ambience when a
    # race-specific track is absent.
    glue_parent = output / "Interface" / "GlueXML" / "GlueParent.lua"
    text = glue_parent.read_text(encoding="utf-8")
    text = text.replace(
        "PlayGlueAmbience(GlueAmbienceTracks[nameupper], 4.0);",
        "PlayGlueAmbience(GlueAmbienceTracks[nameupper] or GlueAmbienceTracks[\"DARKPORTAL\"], 4.0);",
    )
    text = text.replace(
        "GlueAmbienceTracks = { };\n",
        "GlueAmbienceTracks = { };\n"
        "-- CharacterSelect.lua calls PlayGlueAmbience directly with the race key.\n"
        "-- Guard the native function so a custom race without its own sound kit\n"
        "-- cannot produce a Glue Lua error popup.\n"
        "local NativePlayGlueAmbience = PlayGlueAmbience;\n"
        "function PlayGlueAmbience(track, fade)\n"
        "    if ( not track ) then track = GlueAmbienceTracks[\"DARKPORTAL\"]; end\n"
        "    if ( track ) then NativePlayGlueAmbience(track, fade); end\n"
        "end\n",
    )
    text = text.replace(
        '    local path = "Interface\\\\Glues\\\\Models\\\\UI_"..name.."\\\\UI_"..name..".m2";\n',
        '    -- Custom races do not have stock character-select scene folders.\n'
        '    -- Reuse the requested faction starter-zone backdrop instead.\n'
        '    local backgroundName = name;\n'
        '    if ( nameupper == "HIGHELF" ) then backgroundName = "Human"; end\n'
        '    if ( nameupper == "GOBLIN" ) then backgroundName = "Orc"; end\n'
        '    local path = "Interface\\\\Glues\\\\Models\\\\UI_"..backgroundName.."\\\\UI_"..backgroundName..".m2";\n',
    )
    text = text.replace(
        '\tSetLighting(model, nameupper)\n',
        '\tlocal lightingName = nameupper;\n'
        '\tif ( nameupper == "HIGHELF" ) then lightingName = "HUMAN"; end\n'
        '\tif ( nameupper == "GOBLIN" ) then lightingName = "ORC"; end\n'
        '\tSetLighting(model, lightingName)\n',
    )
    glue_parent.write_text(text, encoding="utf-8", newline="\n")

    ref_dbc = output / "DBFilesClient"
    current_dbc = current_client / "DBFilesClient"

    # Client race slot 12 is the unused custom-race slot used by the working
    # worgoblin patch. Replace its Worgen row with High Elf below.
    fields, size, records, strings = read_wdbc(ref_dbc / "ChrRaces.dbc")
    for record in records:
        if record[0] == 12:
            record[1] = 5
            record[13] = 2
    write_wdbc(ref_dbc / "ChrRaces.dbc", fields, size, records, strings)

    # Replace slot 12 with the current High Elf row, changing only its ID.
    fields, size, records, strings = read_wdbc(ref_dbc / "ChrRaces.dbc")
    records = [r for r in records if r[0] != 12]
    write_wdbc(ref_dbc / "ChrRaces.dbc", fields, size, records, strings)
    high_elf = []
    _, _, source_records, source_strings = read_wdbc(current_dbc / "ChrRaces.dbc")
    for record in source_records:
        if record[0] == 22:
            record[0] = 12
            high_elf.append(record)
    if len(high_elf) != 1:
        raise ValueError("Expected exactly one High Elf ChrRaces row")
    fields, size, records, strings = read_wdbc(ref_dbc / "ChrRaces.dbc")
    strings = bytearray(strings)
    high_elf[0] = remap_string_refs(high_elf[0], source_strings, strings, (6, 11, 14))
    high_elf[0][1] = 12

    # Give High Elf its own display and model-data IDs. The High Elf assets
    # are in a separate Character/HighElf namespace, so the stock Blood Elf
    # CreatureModelData rows cannot be reused: they point at BloodElf*.mdx.
    # Reusing them makes the client look for files absent from the patch,
    # producing a black screen or a missing-model cube.
    clone_wdbc_row(
        ref_dbc / "CreatureModelData.dbc", 2208, 40076, {},
        {2: "Character\\HighElf\\Male\\HighElfMale.mdx"},
    )
    clone_wdbc_row(
        ref_dbc / "CreatureModelData.dbc", 2209, 40075, {},
        {2: "Character\\HighElf\\Female\\HighElfFemale.mdx"},
    )
    clone_wdbc_row(ref_dbc / "CreatureDisplayInfo.dbc", 15476, 40076, {1: 40076})
    clone_wdbc_row(ref_dbc / "CreatureDisplayInfo.dbc", 15475, 40075, {1: 40075})
    high_elf[0][4] = 40076
    high_elf[0][5] = 40075
    records.append(high_elf[0])
    write_wdbc(ref_dbc / "ChrRaces.dbc", fields, size, records, bytes(strings))

    # Add the existing High Elf appearance and starting-kit rows.
    # CharSections stores the row ID first and race ID second.
    remove_packed_records(
        ref_dbc / "CharSections.dbc",
        lambda record: struct.unpack_from("<I", record, 4)[0] == 12,
    )
    append_packed_path_remapped_records(
        ref_dbc / "CharSections.dbc", current_dbc / "CharSections.dbc",
        lambda record: struct.unpack_from("<I", record, 4)[0] == 22, 4, (16, 20, 24)
    )
    remove_packed_records(
        ref_dbc / "CharBaseInfo.dbc",
        lambda record: (struct.unpack_from("<H", record)[0] & 0xFF) == 12,
    )
    append_packed_remapped_records(
        ref_dbc / "CharBaseInfo.dbc",
        current_dbc / "CharBaseInfo.dbc",
        lambda record: (struct.unpack_from("<H", record)[0] & 0xFF) == 22,
        (0,)
    )
    # Keep Goblin ARAC-compatible with the fork's all-races/all-classes
    # setup. The reference patch supplies the normal eight Goblin classes;
    # clone a compatible Alliance Paladin row and Night Elf Druid row into
    # the Goblin race slot as well.
    append_packed_clones(
        ref_dbc / "CharBaseInfo.dbc",
        lambda record: record[0] == 1 and record[1] == 2,
        {0: 9},
    )
    append_packed_clones(
        ref_dbc / "CharBaseInfo.dbc",
        lambda record: record[0] == 4 and record[1] == 11,
        {0: 9},
    )
    remove_packed_records(
        ref_dbc / "CharStartOutfit.dbc",
        lambda record: (struct.unpack_from("<I", record, 4)[0] & 0xFF) == 12,
    )
    append_packed_remapped_records(
        ref_dbc / "CharStartOutfit.dbc",
        current_dbc / "CharStartOutfit.dbc",
        lambda record: (struct.unpack_from("<I", record, 4)[0] & 0xFF) == 22,
        (4,)
    )
    # The reference Goblin outfit table omits the Paladin row. Goblin is
    # ARAC-enabled in this fork, so clone Orc's Paladin starting kit and only
    # change the packed race byte (offset 4); class and gender stay intact.
    append_packed_clones_from_same_file(
        ref_dbc / "CharStartOutfit.dbc",
        lambda record: (struct.unpack_from("<I", record, 4)[0] & 0xFF) == 2
        and ((struct.unpack_from("<I", record, 4)[0] >> 8) & 0xFF) == 2,
        {4: 9},
    )

    # High Elf reuses Blood Elf customization definitions. Duplicate only the
    # race-keyed rows; leave the reference Goblin/Worgen rows untouched.
    path = ref_dbc / "CharHairGeosets.dbc"
    fields, size, records, strings = read_wdbc(path)
    records = [r for r in records if r[1] != 12]
    next_id = max(r[0] for r in records) + 1
    records += [[next_id + i, 12, *r[2:]] for i, r in enumerate(records[:]) if r[1] == 10]
    write_wdbc(path, fields, size, records, strings)

    path = ref_dbc / "CharHairTextures.dbc"
    fields, size, records, strings = read_wdbc(path)
    records = [r for r in records if r[1] != 12]
    write_wdbc(path, fields, size, records, strings)
    duplicate_rows_with_path_remap(path, 1, 10, 12)

    path = ref_dbc / "CharacterFacialHairStyles.dbc"
    fields, size, records, strings = read_wdbc(path)
    records = [r for r in records if r[0] != 12]
    records += [[12, *r[1:]] for r in records[:] if r[0] == 10]
    write_wdbc(path, fields, size, records, strings)

    print(f"Created merged client tree: {output}")


if __name__ == "__main__":
    main()
