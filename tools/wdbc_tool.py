"""
Minimal WDBC (WotLK 3.3.5a) reader/writer for fixed-width, all-uint32-field
DBC files (ChrRaces, CharBaseInfo, CharSections, CharStartOutfit, etc. are all
this shape -- no floats in the fields this module touches for race work).

Record layout: recordCount x recordSize bytes, where recordSize = fieldCount*4.
Every field is either a raw uint32/int32, or a "string ref": an int32 byte
offset into the trailing string block (0 = empty string "").

This intentionally does NOT try to be a general DBC library -- just enough to
read a file into a list of int32 tuples, resolve/rewrite string-ref fields by
name, and write a new file back out with the string block correctly rebuilt.

Field positions for any given DBC come from the real struct layout the server
itself parses (src/server/shared/DataStores/DBCStructure.h) -- always
cross-check against that file before trusting a field index, not from a
third-party dump tool's own (often re-ordered or incomplete) field naming.

Verified round-trip byte-identical against the server's own ChrRaces.dbc
before this tool was trusted for any real edit.

Usage as a script: `python wdbc_tool.py <file.dbc>` reads the file, writes it
back out unmodified to a temp path, and reports whether the two are
byte-identical -- a sanity check to run against any new DBC file shape before
trusting this tool to edit it.
"""
import struct
import sys
import tempfile


class WdbcFile:
    def __init__(self, path):
        with open(path, 'rb') as f:
            data = f.read()
        magic, record_count, field_count, record_size, string_block_size = struct.unpack_from('<4sIIII', data, 0)
        if magic != b'WDBC':
            raise ValueError(f"{path}: not a WDBC file (magic={magic!r})")
        assert record_size == field_count * 4, f"record_size {record_size} != field_count*4 {field_count*4}"

        self.field_count = field_count
        header_size = 20
        records_start = header_size
        records_end = records_start + record_count * record_size
        string_block = data[records_end:records_end + string_block_size]
        assert len(string_block) == string_block_size

        self.records = []
        for r in range(record_count):
            off = records_start + r * record_size
            fields = list(struct.unpack_from(f'<{field_count}i', data, off))
            self.records.append(fields)

        self.string_block = string_block

    def get_string(self, offset):
        if offset == 0:
            return ""
        end = self.string_block.index(b'\x00', offset)
        return self.string_block[offset:end].decode('utf-8')

    def find_record(self, id_field_index, id_value):
        for rec in self.records:
            if rec[id_field_index] == id_value:
                return rec
        return None

    def add_string(self, new_strings_pool, text):
        """Append text (if not already present) to a pool dict {text: offset},
        tracking a running byte offset starting after the existing string
        block. Returns the offset to use for this string."""
        if text == "":
            return 0
        if text in new_strings_pool:
            return new_strings_pool[text]
        offset = new_strings_pool['__next__']
        new_strings_pool[text] = offset
        new_strings_pool['__bytes__'].append(text.encode('utf-8') + b'\x00')
        new_strings_pool['__next__'] += len(text.encode('utf-8')) + 1
        return offset

    def write(self, path, records):
        """records: list of field-tuples (ints), where string-ref fields
        already hold correct offsets into self.string_block (i.e. caller
        reused existing offsets -- no new strings). Use write_with_new_strings
        instead if you added brand-new string content."""
        record_count = len(records)
        field_count = self.field_count
        record_size = field_count * 4
        string_block_size = len(self.string_block)
        header = struct.pack('<4sIIII', b'WDBC', record_count, field_count, record_size, string_block_size)
        body = b''.join(struct.pack(f'<{field_count}i', *rec) for rec in records)
        with open(path, 'wb') as f:
            f.write(header)
            f.write(body)
            f.write(self.string_block)

    def write_with_new_strings(self, path, records, new_strings_pool):
        """string_block starts with the ORIGINAL string block content
        (offsets 0..len(self.string_block)-1 stay valid), then appends any
        newly-added strings after it (their offsets were assigned starting
        at len(self.string_block) by add_string)."""
        record_count = len(records)
        field_count = self.field_count
        record_size = field_count * 4
        new_block = self.string_block + b''.join(new_strings_pool['__bytes__'])
        string_block_size = len(new_block)
        header = struct.pack('<4sIIII', b'WDBC', record_count, field_count, record_size, string_block_size)
        body = b''.join(struct.pack(f'<{field_count}i', *rec) for rec in records)
        with open(path, 'wb') as f:
            f.write(header)
            f.write(body)
            f.write(new_block)


def new_string_pool(existing_block_len):
    return {'__next__': existing_block_len, '__bytes__': []}


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python wdbc_tool.py <file.dbc>")
        sys.exit(1)

    # Self-test / round-trip check: read a file, write it back unmodified,
    # confirm byte-identical output. Run this against any new DBC file shape
    # before trusting the tool to actually edit it.
    path = sys.argv[1]
    wdbc = WdbcFile(path)
    print(f"{path}: {len(wdbc.records)} records, {wdbc.field_count} fields, "
          f"{len(wdbc.string_block)} string-block bytes")
    with open(path, 'rb') as f:
        original = f.read()
    with tempfile.NamedTemporaryFile(suffix='.dbc', delete=False) as tmp:
        tmp_path = tmp.name
    wdbc.write(tmp_path, wdbc.records)
    with open(tmp_path, 'rb') as f:
        rewritten = f.read()
    print("Round-trip identical:", original == rewritten)
