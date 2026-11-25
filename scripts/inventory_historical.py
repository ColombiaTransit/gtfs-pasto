"""Recover static transit records from the 2023 Ruti APK without executing it."""
import ast
import collections as c
import json
import pathlib
import re
import sys
from hermes_dec.parsers.hbc_file_parser import HBCReader
from hermes_dec.parsers.hbc_bytecode_parser import parse_hbc_bytecode
from hermes_dec.parsers.serialized_literal_parser import unpack_slp_array

bundle, source, out = map(pathlib.Path, sys.argv[1:4])
out.mkdir(parents=True, exist_ok=True)
records = c.defaultdict(list)
schemas = c.Counter()
errors = c.Counter()
terms = re.compile(r"frecuen|headway|intervalo|despacho|departure|arrival|hora.?salida|hora.?llegada|tiempo.?recorrido|programaci[oó]n|trip.?id|stop.?times|timetable|paraderosAndRutas", re.I)
def decode(buf, offset, count, reader):
    return unpack_slp_array(buf[offset:], count).to_strings(reader.strings)
def literal(p):
    if p in ("null", "undefined", "nan", "inf", "-inf"): return None
    if p == "true": return True
    if p == "false": return False
    return ast.literal_eval(p)
with bundle.open("rb") as fp:
    reader = HBCReader()
    reader.read_whole_file(fp)
    for fid, header in enumerate(reader.function_headers):
        for ins in parse_hbc_bytecode(header, reader):
            if ins.inst.name not in ("NewObjectWithBuffer", "NewObjectWithBufferLong"):
                continue
            try:
                count = ins.arg3
                keys = [literal(p) for p in decode(reader.object_keys, ins.arg4, count, reader)]
                ks = set(keys)
                schema = tuple(sorted(map(str, keys)))
                schemas[schema] += 1
                if {"JRNYPATTRN_ID", "ROUT_NM", "DISP_STOPPOINT_ID"} <= ks:
                    group = "rutas"
                elif {"Nombre", "Descripcion", "Horario1"} <= ks and ("ID" in ks or "idBus" in ks):
                    group = "horariosTwo" if "Desde1" in ks else "horarios"
                elif {"IDPARADERO", "NOMBRE", "RUTA"} <= ks:
                    group = "paraderosAndRutas"
                elif any(terms.search(str(k)) for k in ks):
                    group = "timing_candidates"
                else:
                    continue
                vals = [literal(p) for p in decode(reader.object_values, ins.arg5, count, reader)]
                records[group].append({"function_id":fid,"record":dict(zip(keys,vals))})
            except Exception as exc:
                errors[type(exc).__name__] += 1
    string_hits = [{"id":i,"text":s[:180]} for i,s in enumerate(reader.strings) if terms.search(s)]
for group, rows in records.items():
    (out/(group+".json")).write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding="utf-8")
lines = source.read_text(encoding="utf-8",errors="replace").splitlines()
hits = [{"line":i+1,"text":line.strip()[:250]} for i,line in enumerate(lines) if terms.search(line)]
report = {"counts":{k:len(v) for k,v in records.items()},"schema_count":len(schemas),"decode_errors":dict(errors),"top_schemas":[{"keys":list(k),"count":n} for k,n in schemas.most_common(35)],"samples":{k:[r["record"] for r in v[:3]] for k,v in records.items()},"string_hits":string_hits,"source_hits":hits,"limitations":"Literal object candidates only; dynamic assignments and actual frequency semantics not verified."}
(out/"historical-report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
print("HISTORICAL",json.dumps({k:v for k,v in report.items() if k not in ("source_hits",)},ensure_ascii=False))
for h in hits[:80]:
    print("HISTORICAL_REFERENCE",json.dumps(h,ensure_ascii=False))
