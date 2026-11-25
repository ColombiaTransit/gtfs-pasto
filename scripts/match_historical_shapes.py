"""Audit historical geometries against current Ruti stop sequences (metres)."""
import collections
import csv
import json
import math
import pathlib
import sys

import numpy as np

old, current, out = map(pathlib.Path, sys.argv[1:4])
out.mkdir(parents=True, exist_ok=True)
def load(root, name):
    return json.loads((root / (name + ".json")).read_text(encoding="utf-8"))
def records(root, name):
    return [x["record"] for x in load(root, name)]
def xy(lat, lon):
    return [float(lon) * 111195 * math.cos(math.radians(1.2)), float(lat) * 111195]
def points(rows):
    return np.array([xy(r["Y_COORD"], r["X_COORD"]) for r in rows])
def grouped(rows):
    result = collections.defaultdict(list)
    for r in rows:
        result[str(r["JRNYPATTRN_ID"])].append(r)
    return {k: sorted(v, key=lambda r: int(r["VEH_VIA_SEQ"])) for k,v in result.items()}
historical = grouped(records(old, "rutas"))
patterns = grouped(records(current, "rutas"))
groups = load(old, "geometry-groups-candidates")
raw = [np.array([[float(x["record"]["Latitude"]), float(x["record"]["Longitude"])] for x in g]) for g in groups]
lines = [np.array([xy(*p) for p in g]) for g in raw]
def gap(a,b):
    return float(np.linalg.norm(lines[a][-1]-lines[b][0]))
links = {i:[j for j in range(len(lines)) if j != i and gap(i,j)<=50] for i in range(len(lines))}
# Allow directed chains of up to four distinct original segments.
chains = []
def extend(chain):
    chains.append(chain)
    if len(chain)<4:
        for j in links[chain[-1]]:
            if j not in chain:
                extend(chain+(j,))
for i in range(len(lines)):
    extend((i,))
def build(chain):
    return np.concatenate([lines[i] for i in chain])
def geo(chain):
    return np.concatenate([raw[i] for i in chain])
def prepare(line):
    a=line[:-1]; v=line[1:]-a
    length=np.linalg.norm(v,axis=1)
    return a,v,np.maximum(length**2,1e-12),length,np.r_[0,np.cumsum(length)]
# For each stop project onto every polyline edge. Dynamic programming selects
# an ordered sequence of projections with minimum squared lateral error.
def score(p, prepared):
    a,v,den,length,cum=prepared
    t=np.clip(np.sum((p[:,None,:]-a[None,:,:])*v[None,:,:],axis=2)/den[None,:],0,1)
    delta=p[:,None,:]-(a[None,:,:]+t[:,:,None]*v[None,:,:])
    d2=np.sum(delta**2,axis=2)
    along=cum[:-1][None,:]+t*length[None,:]
    nearest=np.sqrt(d2.min(axis=1))
    # A generous lower bound keeps expensive ordered checks tractable.
    if nearest.max()>300:
        return None
    cost=d2[0].copy()
    parents=[]
    for k in range(1,len(p)):
        # Within an edge, projected positions may go backwards; disallow that.
        prefix=np.minimum.accumulate(cost)
        ix=np.arange(len(cost))
        best=np.maximum.accumulate(np.where(cost==prefix,ix,0))
        prior=np.r_[np.inf,prefix[:-1]]
        prev=np.r_[-1,best[:-1]]
        same=(along[k]>=along[k-1]-1e-6)&(cost<=prior)
        prior=np.where(same,cost,prior)
        prev=np.where(same,ix,prev)
        cost=d2[k]+prior
        parents.append(prev)
    j=int(np.argmin(cost))
    if not np.isfinite(cost[j]):
        return None
    idx=[j]
    for parent in reversed(parents):
        j=int(parent[j]); idx.append(j)
    idx=np.array(idx[::-1])
    ds=np.sqrt(d2[np.arange(len(p)),idx])
    pos=along[np.arange(len(p)),idx]
    end=float(cum[-1]-pos[-1])
    start=float(pos[0])
    rms=float(np.sqrt(np.mean(ds**2)))
    # Penalize unused geometry, joins and unnecessary segments.
    objective=rms+0.02*(start+end)
    return dict(rms_m=round(rms,2),max_m=round(float(ds.max()),2),
                within_50=int(np.sum(ds<=50)),start_unused_m=round(start,2),
                end_unused_m=round(end,2),objective=round(objective,4),
                stop_distances_m=[round(float(x),2) for x in ds],
                stop_positions_m=[round(float(x),2) for x in pos])
prepared=[(c,prepare(build(c))) for c in chains]
results=[]
features=[]
for pid, rows in sorted(patterns.items()):
    p=points(rows)
    candidates=[]
    for chain, prep in prepared:
        s=score(p,prep)
        if s is None: continue
        s["segments"]=list(chain)
        s["objective"]+=2*(len(chain)-1)
        candidates.append(s)
    candidates.sort(key=lambda x:(x["objective"],x["max_m"],x["segments"]))
    best=candidates[0] if candidates else None
    second=candidates[1] if len(candidates)>1 else None
    # Distinguish genuinely different shapes from harmless extra end segments.
    ambiguous=bool(best and second and second["objective"]-best["objective"]<3)
    mv=any("MV" in str(r["JRNYPATTRN_NM"]) or "MV" in str(r["ADDR"]) for r in rows)
    status="unmatched"
    if best:
        status="review_distance" if best["max_m"]>50 else "review_endpoints" if max(best["start_unused_m"],best["end_unused_m"])>250 else "review_ambiguity" if ambiguous else "candidate_pass"
        coordinates=geo(best["segments"])
        features.append({"type":"Feature","properties":{"pattern_id":pid,"status":status,"route":rows[0]["ROUT_NM"],"segments":best["segments"]},"geometry":{"type":"LineString","coordinates":coordinates[:,::-1].tolist()}})
    result={"pattern_id":pid,"route":rows[0]["ROUT_NM"],"name":rows[0]["JRNYPATTRN_NM"],"mv_filter":mv,"stops":len(rows),"status":status,"best":best,"alternatives":candidates[1:4]}
    results.append(result)
    print("SHAPE_MATCH",json.dumps({**{k:v for k,v in result.items() if k not in ("best","alternatives")},"best":{k:v for k,v in (best or {}).items() if k not in ("stop_distances_m","stop_positions_m")}},ensure_ascii=False))
def canon(rows):
    return collections.Counter(json.dumps(r,sort_keys=True,ensure_ascii=False) for r in rows)
a=canon(records(old,"rutas")); b=canon(records(current,"rutas"))
sa=canon(records(old,"horariosTwo"))
sb=canon([r for r in records(current,"horarios_candidates") if "Desde1" in r])
summary={"segments":len(lines),"candidate_chains":len(chains),"patterns":len(patterns),"status_all":dict(collections.Counter(r["status"] for r in results)),"status_non_mv":dict(collections.Counter(r["status"] for r in results if not r["mv_filter"])),"route_records_old_only":sum((a-b).values()),"route_records_current_only":sum((b-a).values()),"numbered_schedule_old_only":sum((sa-sb).values()),"numbered_schedule_current_only":sum((sb-sa).values()),"limitations":"Candidates only. Raw geometry untrimmed; distances computed locally from coordinates. Chains limited to four segments and 50 m joins; no reversal or artificial long connectors."}
(out/"shape-match-report.json").write_text(json.dumps({"summary":summary,"patterns":results},ensure_ascii=False,indent=2))
(out/"shape-candidates.geojson").write_text(json.dumps({"type":"FeatureCollection","features":features},ensure_ascii=False))
print("SHAPE_SUMMARY",json.dumps(summary,ensure_ascii=False))
