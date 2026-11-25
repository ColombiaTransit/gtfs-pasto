"""Static extraction of transport objects; never execute application code."""
import ast
import math
import collections
import json
import pathlib
import sys

from hermes_dec.parsers.hbc_file_parser import HBCReader
from hermes_dec.parsers.hbc_bytecode_parser import parse_hbc_bytecode
from hermes_dec.parsers.serialized_literal_parser import unpack_slp_array

ROUTE = set("item JRNYPATTRN_ID ROUT_NM JRNYPATTRN_NM DISP_STOPPOINT_ID STOPPOINT_NM STOPPOINT_ID POINT_ID ADDR X_COORD Y_COORD VEH_VIA_SEQ".split())
SCHEDULE = set("idBus Nombre Descripcion Orden Horario1 Desde1 Hasta1 Horario2 Desde2 Hasta2 Horario3 Desde3 Hasta3".split())
bundle, output = map(pathlib.Path, sys.argv[1:3])
output.mkdir(parents=True, exist_ok=True)
records = collections.defaultdict(list)
schemas = collections.Counter()
seen = set()

def decode(buffer, offset, count, reader):
    parts = unpack_slp_array(buffer[offset:], count).to_strings(reader.strings)
    return [None if p in ("null", "undefined", "nan", "inf", "-inf") else True if p == "true" else False if p == "false" else ast.literal_eval(p) for p in parts]

with bundle.open("rb") as handle:
    reader = HBCReader()
    reader.read_whole_file(handle)
    for fid, header in enumerate(reader.function_headers):
        for ins in parse_hbc_bytecode(header, reader):
            if ins.inst.name not in ("NewObjectWithBuffer", "NewObjectWithBufferLong"):
                continue
            count = ins.arg3
            if count < 3:
                continue
            keys = decode(reader.object_keys, ins.arg4, count, reader)
            keyset = set(keys)
            if not (keyset & {"JRNYPATTRN_ID", "ROUT_NM", "idBus", "Horario1", "Desde1"}):
                continue
            schema = tuple(sorted(map(str, keys)))
            schemas[schema] += 1
            if len(keys) != len(keyset):
                continue
            values = decode(reader.object_values, ins.arg5, count, reader)
            obj = dict(zip(keys, values))
            if ROUTE <= keyset:
                group = "rutas"
            elif SCHEDULE <= keyset:
                group = "horarios_candidates"
            else:
                group = "partial_candidates"
            signature = (group, fid, ins.arg4, ins.arg5, count)
            if signature in seen:
                continue
            seen.add(signature)
            records[group].append({"function_id": fid, "key_offset": ins.arg4, "value_offset": ins.arg5, "record": obj})

for group in ("rutas", "horarios_candidates", "partial_candidates"):
    (output / (group + ".json")).write_text(json.dumps(records[group], ensure_ascii=False, indent=2), encoding="utf-8")
report = {
    "counts": {group: len(rows) for group, rows in records.items()},
    "schemas": [{"keys": list(k), "occurrences": n} for k, n in schemas.most_common()],
    "route_ids": sorted({str(row["record"]["JRNYPATTRN_ID"]) for row in records["rutas"]}),
    "public_route_names": sorted({str(row["record"]["ROUT_NM"]) for row in records["rutas"]}),
    "stop_ids": len({str(row["record"]["DISP_STOPPOINT_ID"]) for row in records["rutas"]}),
    "schedule_function_ids": sorted({row["function_id"] for row in records["horarios_candidates"]}),
    "limitations": "Literal objects only; dynamic property assignments, array membership and horarios versus horariosTwo still require verification."
}
(output / "dataset-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(report, ensure_ascii=False, indent=2))
if not records["rutas"] or not records["horarios_candidates"]:
    raise SystemExit("Incomplete extraction: inspect schemas and partial candidates")
