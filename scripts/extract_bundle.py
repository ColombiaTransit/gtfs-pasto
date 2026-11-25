"""Extract the Hermes bundle without executing or publishing the APK."""
import hashlib
import io
import json
import pathlib
import struct
import sys
import zipfile

source = pathlib.Path(sys.argv[1])
out = pathlib.Path(sys.argv[2])
if not source.is_file():
    raise SystemExit("Source APK/XAPK not found on runner")
raw = source.read_bytes()
matches = []
with zipfile.ZipFile(io.BytesIO(raw)) as archive:
    if "assets/index.android.bundle" in archive.namelist():
        matches.append((source.name, archive.read("assets/index.android.bundle")))
    else:
        for member in archive.namelist():
            if member.lower().endswith(".apk"):
                with zipfile.ZipFile(io.BytesIO(archive.read(member))) as apk:
                    if "assets/index.android.bundle" in apk.namelist():
                        matches.append((member, apk.read("assets/index.android.bundle")))
if len(matches) != 1:
    raise SystemExit(f"Expected exactly one main bundle, found {len(matches)}")
member, bundle = matches[0]
if len(bundle) < 12 or bundle[:8] != bytes.fromhex("c61fbc03c103191f"):
    raise SystemExit("Not a Hermes bytecode bundle")
version = struct.unpack_from("<I", bundle, 8)[0]
expected = int(sys.argv[3]) if len(sys.argv) > 3 else 96
if version != expected:
    raise SystemExit(f"Expected Hermes v{expected}, got {version}")
(out / "index.android.bundle").write_bytes(bundle)
report = {
    "source_sha256": hashlib.sha256(raw).hexdigest(),
    "bundle_sha256": hashlib.sha256(bundle).hexdigest(),
    "hermes_version": version,
    "bundle_bytes": len(bundle),
    "source_member": member,
}
(out / "extraction-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print(json.dumps(report, indent=2))
