# GTFS Pasto

Research and GTFS Static generation for the SETP bus network in Pasto, Colombia.

## Source

Ruti SETP Android app (`com.ruti`), version 2.0.0, Hermes bytecode v96. Research targets embedded `rutas`, `horarios` and `horariosTwo` data. Online realtime endpoints returned empty results and are out of scope.

The analysis workflow downloads the existing `source-ruti-2.0.0` prerelease asset and checks its pinned SHA-256 digest. The source release is public; review redistribution rights. Do not commit the original APK or full decompiled application code.

## APK analysis

Run **Analyze Ruti APK** from Actions on `main`. The workflow runs on `ubuntu-latest`, extracts the Hermes bundle, installs hermes-dec 0.1.2 and attempts disassembly and decompilation. Only analysis reports are uploaded as artifacts (seven-day retention); full decompiled code remains temporary on the runner. Do not execute the APK. Data-only extraction is the next step.

## Status

Research in progress. No validated GTFS feed yet. Route and stop IDs, coordinates, sequence, service calendars, frequencies and travel times must be verified before release. Use MobilityData GTFS Validator before publication.
