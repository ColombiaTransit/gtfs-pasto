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
