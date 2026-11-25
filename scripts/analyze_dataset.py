"""Audit extracted transport records without inferring missing timetables."""
import collections as c
import json
import pathlib
import sys
import re

root = pathlib.Path(sys.argv[1])
def load(name):
    return [x["record"] for x in json.loads((root / name).read_text())]
routes = load("rutas.json")
schedules = load("horarios_candidates.json")
patterns = c.defaultdict(list)
for r in routes:
    patterns[str(r["JRNYPATTRN_ID"])].append(r)
by_id = c.defaultdict(list)
for s in schedules:
    by_id[str(s.get("ID", s.get("idBus")))].append(s)
codes = c.Counter()
for s in schedules:
    for k in ("Horario1", "Horario2", "Horario3"):
        codes[str(s.get(k))] += 1
def passenger(r):
    return "MV" not in str(r["JRNYPATTRN_NM"]).upper() and "MV" not in str(r["ADDR"]).upper()
audit = []
for pid, rows in sorted(patterns.items()):
    eligible = [r for r in rows if passenger(r)]
    seq = [r["VEH_VIA_SEQ"] for r in eligible]
    audit.append({
        "id": pid, "line": rows[0]["ROUT_NM"],
        "names": sorted({str(r["JRNYPATTRN_NM"]) for r in rows}),
        "rows": len(rows), "passenger_rows": len(eligible),
        "duplicate_sequences": len(seq)-len(set(seq)),
        "invalid_coordinates": sum(not (-78 < float(r["X_COORD"]) < -76 and 0 < float(r["Y_COORD"]) < 2) for r in eligible),
        "schedules": by_id.get(pid, [])
    })
report = {
    "patterns": len(patterns),
    "schedule_ids": len(by_id),
    "matched_pattern_ids": len(patterns.keys() & by_id.keys()),
    "unmatched_pattern_ids": sorted(patterns.keys()-by_id.keys()),
    "unmatched_schedule_ids": sorted(by_id.keys()-patterns.keys()),
    "passenger_patterns": sum(x["passenger_rows"] > 0 for x in audit),
    "passenger_stops": len({str(r["DISP_STOPPOINT_ID"]) for r in routes if passenger(r)}),
    "service_codes": dict(codes),
    "patterns_with_duplicate_sequence": [x["id"] for x in audit if x["duplicate_sequences"]],
    "patterns_with_invalid_coordinates": [x["id"] for x in audit if x["invalid_coordinates"]],
    "schedule_pairs_sample": [{"id": k, "records": v} for k,v in list(by_id.items())[:10]],
    "unmatched_schedules": [s for k,v in by_id.items() if k not in patterns for s in v]
}
(root/"pattern-audit.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2))
(root/"join-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
print(json.dumps(report, ensure_ascii=False, indent=2))
# Look for service-code interpretation and schedule windows in decompiled pseudocode.
# Keep only transport-related snippets, never execute source.
if len(sys.argv)>2:
    lines=pathlib.Path(sys.argv[2]).read_text(encoding="utf-8", errors="replace").splitlines()
    matches=[]
    for i,line in enumerate(lines):
        if re.search(r'Lunes a Domingo|Lunes a Viernes|Lunes a S.bado|Domingos y Festivos|saveHorarios|horariosTwo|getHorario',line,re.I):
            matches.append({"line":i+1,"context":[x[:350] for x in lines[max(0,i-5):i+6]]})
    (root/"schedule-logic-evidence.json").write_text(json.dumps(matches,ensure_ascii=False,indent=2))
    print("Schedule logic references:",len(matches))
    for m in matches[:25]:
        print(json.dumps(m,ensure_ascii=False))

    # Inspect non-literal uses of schedule fields and explicit day-label mappings.
    field = re.compile(r"\b(?:Horario[123]|Desde[123]|Hasta[123]|horario[123]|desde[123]|hasta[123])\b")
    label = re.compile(r"""['"](?:L-D|L-S|L-V|S|D-F|L”D|L”S|L”V|D”F)['"]""")
    hits = []
    for i,line in enumerate(lines):
        if ("'ID':" in line and "'Nombre':" in line) or "CREATE TABLE" in line:
            continue
        if field.search(line) or label.search(line):
            hits.append(i)
    spans = []
    for i in hits:
        a,b=max(0,i-12),min(len(lines),i+13)
        if spans and a<=spans[-1][1]:
            spans[-1][1]=max(b,spans[-1][1])
        else:
            spans.append([a,b])
    evidence = []
    for a,b in spans:
        block=lines[a:b]
        # Remove large inline dataset literals; retain instructions.
        block=[x[:500] for x in block if not ("'ID':" in x and "'Nombre':" in x)]
        evidence.append({"start_line":a+1,"end_line":b,"context":block})
    (root/"schedule-field-usage.json").write_text(json.dumps(evidence,ensure_ascii=False,indent=2))
    print("Schedule field usage blocks:",len(evidence))
    # Prioritize contexts with explicit day labels, then UI/database field reads.
    ranked=sorted(evidence,key=lambda e: (not any(label.search(x) for x in e["context"]),not any("Horario1" in x for x in e["context"])))
    for e in ranked[:30]:
        print("FIELD_USAGE",json.dumps(e,ensure_ascii=False))
