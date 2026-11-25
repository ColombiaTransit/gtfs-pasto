"""Compare decoded records and ordered geometry groups across Ruti releases."""
import collections
import hashlib
import json
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
old = root / "v12"
def load(folder, name):
    return json.loads((folder / (name + ".json")).read_text(encoding="utf-8"))
def canon(rows):
    return collections.Counter(json.dumps(x["record"], sort_keys=True, ensure_ascii=False) for x in rows)
def diff(a,b):
    return {"v12_count":sum(a.values()),"v15_count":sum(b.values()),"identical":sum((a&b).values()),"v12_only":sum((a-b).values()),"v15_only":sum((b-a).values())}
report = {}
for name in ("rutas","horarios","horariosTwo","paraderosAndRutas","geometry_points"):
    report[name] = diff(canon(load(old,name)),canon(load(root,name)))
def groups(folder):
    return collections.Counter(hashlib.sha256(json.dumps([x["record"] for x in group],sort_keys=True,ensure_ascii=False).encode()).hexdigest() for group in load(folder,"geometry-groups-candidates"))
report["geometry_groups"] = diff(groups(old),groups(root))
(root/"version-comparison.json").write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
print("VERSION_COMPARISON",json.dumps(report,ensure_ascii=False))

# Compare fields using stable pattern and stop sequence keys; do not conflate
# changed display labels with changed geometry or actual clock times.
def keyed(rows, fields):
    result = collections.defaultdict(list)
    for x in rows:
        r = x["record"]
        result[tuple(str(r.get(k)) for k in fields)].append(r)
    return result
def field_diff(left,right,keys):
    a,b=keyed(left,keys),keyed(right,keys)
    counts=collections.Counter()
    samples=collections.defaultdict(list)
    ambiguous=0
    for key in sorted(a.keys() & b.keys()):
        if len(a[key])!=1 or len(b[key])!=1:
            ambiguous+=1
            continue
        x,y=a[key][0],b[key][0]
        for field in sorted(x.keys() | y.keys()):
            if x.get(field)!=y.get(field):
                counts[field]+=1
                if len(samples[field])<5:
                    samples[field].append({"key":key,"before":x.get(field),"after":y.get(field)})
    return {"field_counts":dict(counts),"samples":dict(samples),"left_only_keys":len(a.keys()-b.keys()),"right_only_keys":len(b.keys()-a.keys()),"ambiguous_keys":ambiguous}
details={
    "routes_v12_v15":field_diff(load(old,"rutas"),load(root,"rutas"),["JRNYPATTRN_ID","VEH_VIA_SEQ"]),
    "schedule_v12_current":field_diff(load(old,"horariosTwo"),[x for x in load(root/"current","horarios_candidates") if "Desde1" in x["record"]],["ID"])
}
(root/"version-field-differences.json").write_text(json.dumps(details,indent=2,ensure_ascii=False),encoding="utf-8")
print("FIELD_COMPARISON",json.dumps(details,ensure_ascii=False))
