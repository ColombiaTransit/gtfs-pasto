"""Inventory static datasets and timetable-related references without executing the APK."""
import collections as c
import json
import pathlib
import re
import sys
from hermes_dec.parsers.hbc_file_parser import HBCReader
from hermes_dec.parsers.hbc_bytecode_parser import parse_hbc_bytecode
from hermes_dec.parsers.serialized_literal_parser import unpack_slp_array

bundle, output, source = map(pathlib.Path, sys.argv[1:4])
terms = re.compile(r"frecuen|headway|intervalo|despacho|departure|arrival|hora.?salida|hora.?llegada|tiempo.?recorrido|duraci[oó]n|programaci[oó]n|stop.?times|trip.?id|journey|itinerario|timetable|schedule|viajes|servicios", re.I)
clock = re.compile(r"^(?:[01]?\d|2[0-3]):[0-5]\d(?::[0-5]\d)?$")
schemas = c.Counter()
schema_functions = c.defaultdict(c.Counter)
schema_stats = c.defaultdict(c.Counter)
arrays = []
functions = []
errors = c.Counter()

def decode(buffer, offset, count, reader):
    return unpack_slp_array(buffer[offset:], count).to_strings(reader.strings)

with bundle.open("rb") as fp:
    reader = HBCReader()
    reader.read_whole_file(fp)
    string_hits = [{"id": i, "text": s[:180]} for i,s in enumerate(reader.strings) if terms.search(s)]
    for fid, header in enumerate(reader.function_headers):
        ops = c.Counter()
        for ins in parse_hbc_bytecode(header, reader):
            name = ins.inst.name
            if name in ("NewObjectWithBuffer", "NewObjectWithBufferLong"):
                ops[name] += 1
                try:
                    count = ins.arg3
                    keys = decode(reader.object_keys, ins.arg4, count, reader)
                    schema = tuple(sorted(k.strip("'\u0022") for k in keys))
                    schemas[schema] += 1
                    schema_functions[schema][fid] += 1
                    vals = decode(reader.object_values, ins.arg5, count, reader)
                    schema_stats[schema]["clock_values"] += sum(bool(clock.fullmatch(v.strip("'\u0022"))) for v in vals)
                    schema_stats[schema]["numeric_values"] += sum(bool(re.fullmatch(r"-?\d+(?:\.\d+)?", v)) for v in vals)
                except Exception as e:
                    errors[type(e).__name__] += 1
            elif name.startswith("NewArray"):
                ops[name] += 1
                # Preserve operand metadata rather than guessing the semantics.
                args = [getattr(ins, "arg"+str(i), None) for i in range(1,6)]
                arrays.append({"function_id":fid,"opcode":name,"operands":args})
        if ops:
            functions.append({"function_id":fid,"name":reader.strings[header.functionName],"allocations":dict(ops)})
schema_rows = [{"keys":list(k),"count":n,"functions":dict(schema_functions[k]),**schema_stats[k]} for k,n in schemas.most_common()]
lines = source.read_text(encoding="utf-8",errors="replace").splitlines()
# Pseudocode gives the declared array sizes independently of opcode operand conventions.
alloc = re.compile(r"new Array\((\d+)\)")
large = []
hits = []
for i,line in enumerate(lines):
    for m in alloc.finditer(line):
        if int(m[1]) >= 20:
            large.append({"line":i+1,"length":int(m[1]),"context":line.strip()[:180]})
    if terms.search(line):
        hits.append({"line":i+1,"context":line.strip()[:240]})
# Also identify long inline arrays with clock-like entries.
clock_arrays = []
for i,line in enumerate(lines):
    if "[" in line and "]" in line and len(re.findall(r"['\u0022]\d{1,2}:[0-5]\d['\u0022]",line)) >= 4:
        clock_arrays.append({"line":i+1,"clock_count":len(re.findall(r"['\u0022]\d{1,2}:[0-5]\d['\u0022]",line))})
report = {"function_count":len(reader.function_headers),"string_count":len(reader.strings),"object_schema_count":len(schemas),"object_allocations":sum(schemas.values()),"array_allocations":len(arrays),"decode_errors":dict(errors),"large_array_count":len(large),"clock_array_candidates":clock_arrays,"transport_string_hits":len(string_hits),"transport_source_hits":len(hits)}
data = {"summary":report,"schemas":schema_rows,"array_allocations":arrays,"functions":functions,"large_arrays":large,"transport_strings":string_hits,"transport_source_hits":hits}
(output/"dataset-inventory.json").write_text(json.dumps(data,ensure_ascii=False,indent=2,default=str),encoding="utf-8")
print("INVENTORY",json.dumps(report,ensure_ascii=False))
for row in schema_rows[:35]:
    print("SCHEMA",json.dumps({**row,"functions":list(row["functions"].items())[:12]},ensure_ascii=False))
for row in sorted(large,key=lambda x:-x["length"])[:40]:
    print("LARGE_ARRAY",json.dumps(row))
for row in string_hits:
    if re.search(r"frecuen|headway|intervalo|despacho|hora.?salida|hora.?llegada|tiempo.?recorrido|trip.?id|stop.?times",row["text"],re.I):
        print("TERM",json.dumps(row,ensure_ascii=False))
