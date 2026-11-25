"""Inspect remaining static arrays and transport API references without executing the app."""
import collections
import json
import pathlib
import re
import sys

src, out = map(pathlib.Path, sys.argv[1:3])
lines = src.read_text(encoding="utf-8", errors="replace").splitlines()
alloc = re.compile(r"\b(r\d+) = new Array\((\d+)\)")
function = re.compile(r"\bfunction\*?\s*\(|_fun\d+:")
arrays = []
for i, line in enumerate(lines):
    m = alloc.search(line)
    if not m or int(m[2]) < 20:
        continue
    reg, size = m[1], int(m[2])
    if size in (5024, 85):
        continue
    assignments = []
    # Bound the scan to a short span sufficient for ordinary literal arrays.
    for n in range(i+1, min(i+500, len(lines))):
        if re.search(r"\b"+reg+r"\s*=\s*", lines[n]):
            break
        if re.search(r"\b"+reg+r"\[\d+\]\s*=", lines[n]):
            assignments.append({"line":n+1,"instruction":lines[n].strip()[:250]})
    arrays.append({"line":i+1,"size":size,"assignments":assignments,
        "context":[s.strip()[:220] for s in lines[max(0,i-8):min(len(lines),i+min(100,size*3+15))]]})
# Keep only contexts directly relevant to the transport API, and distinguish
# library methods from the actual application call sites.
terms = {
    "stopTimespan":r"\bstopTimespan\b",
    "api_paths":r"181\.49\.177\.91|cms-ruti-set|['\x22]/(?:line|stop|loc)/['\x22]|/api/app-rutis",
    "api_methods":r"\b(?:getInfoVehicle|getDataRuta|getDataParaderos|getParaderos)\b",
    "services":r"\.services\b|\[['\x22]services['\x22]\]",
    "timing":r"frecuen|headway|intervalo|despacho|hora.?salida|hora.?llegada|tiempo.?recorrido|stopTimespan|arrivalTime|departureTime|estimatedTime|expectedArrival",
    "storage":r"CREATE TABLE|INSERT INTO|INSERT OR REPLACE INTO|openDatabaseAsync|openDatabaseSync",
}
evidence={}
for key, pattern in terms.items():
    hits=[]
    for i,line in enumerate(lines):
        if re.search(pattern,line,re.I):
            hits.append(i)
    spans=[]
    for i in hits:
        a,b=max(0,i-14),min(len(lines),i+21)
        if spans and a<=spans[-1][1]:
            spans[-1][1]=max(b,spans[-1][1])
        else:
            spans.append([a,b])
    evidence[key]=[{"start":a+1,"end":b,"context":[s.strip()[:400] for s in lines[a:b] if not ("'ID':" in s and "'Nombre':" in s)]} for a,b in spans]
report={"remaining_arrays":arrays,"evidence":evidence,"limitations":"Static pseudocode inspection; register aliases, dynamic arrays and network response schemas may need further analysis."}
(out/"remaining-datasets-report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
print("REMAINING_ARRAY_COUNT",len(arrays))
for a in arrays:
    print("ARRAY_DETAIL",json.dumps(a,ensure_ascii=False))
for key, blocks in evidence.items():
    print("EVIDENCE_COUNT",key,len(blocks))
    for b in blocks[:15]:
        print("API_DETAIL",key,json.dumps(b,ensure_ascii=False))
