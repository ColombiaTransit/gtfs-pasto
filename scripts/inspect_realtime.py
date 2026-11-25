"""Static analysis of Ruti's public transit API; no network calls or app execution."""
import json
import pathlib
import re
import sys

src,out=map(pathlib.Path,sys.argv[1:3])
out.mkdir(parents=True,exist_ok=True)
lines=src.read_text(encoding="utf-8",errors="replace").splitlines()
def safe(s):
    # Avoid exposing unrelated embedded map credentials.
    return re.sub(r"AIza[\w-]{30,}", "[REDACTED_MAP_KEY]",s.strip())[:500]
def block(a,b):
    return [{"line":i+1,"text":safe(lines[i])} for i in range(max(0,a),min(len(lines),b))]
# Module 1042 was identified by the earlier static analysis. Include its
# complete body rather than just the endpoint wrapper lines.
starts=[i for i,l in enumerate(lines) if "Original name: getHeaders" in l and any("busApiToken" in x for x in lines[i:i+35])]
modules=[]
for i in starts:
    a=next((j for j in range(i,max(-1,i-100),-1) if "function(a0, a1, a2, a3, a4, a5, a6)" in lines[j]),max(0,i-35))
    b=next((j for j in range(i,min(len(lines),i+500)) if re.search(r"= 1042;",lines[j])),min(len(lines),i+220))
    modules.append(block(a,b+3))
terms={
 "callers":r"\.(getLineInfo|getInfoVehicle|getDataParaderos)\b",
 "configuration":r"busApiUrl|busApiToken|urlSocket|cms-ruti-set|181\.49\.177\.91",
 "response":r"CURRENT_STOP_ID|\bservices\b|\b(?:VEHICLE_ID|LINE_ID|JRNYPATTRN_ID|EXPECTED_ARRIVAL|STOPPOINT_ID|DISP_STOPPOINT_ID)\b",
 "polling":r"\b(?:setInterval|clearInterval|setTimeout|clearTimeout|useFocusEffect)\b",
 "socket":r"\.emit\b|\.on\b|socket\.io|urlSocket",
}
report={"request_modules":modules,"contexts":{}}
for key,pat in terms.items():
    hits=[i for i,l in enumerate(lines) if re.search(pat,l) and len(l)<2000]
    if key in ("polling","socket","response"):
        # Restrict library-heavy terms to the application neighborhoods
        # of known transit calls, while recording configuration independently.
        anchors=[i for i,l in enumerate(lines) if re.search(terms["callers"],l)]
        hits=[i for i in hits if any(abs(i-a)<1500 for a in anchors)]
    spans=[]
    for i in hits:
        a,b=max(0,i-18),min(len(lines),i+45)
        if spans and a<=spans[-1][1]: spans[-1][1]=max(b,spans[-1][1])
        else: spans.append([a,b])
    report["contexts"][key]=[block(a,b) for a,b in spans]
    print("REALTIME_CONTEXT_COUNT",key,len(spans))
    for a,b in spans[:25]:
        for row in block(a,min(b,a+150)):
            print("REALTIME",key,row["line"],row["text"])
for mod in modules:
    for row in mod:
        print("REQUEST_MODULE",row["line"],row["text"])
(out/"realtime-api-report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
if not modules:
    raise SystemExit("Request module not located; inspect decompiler output")
