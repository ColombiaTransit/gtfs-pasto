# GTFS Pasto

Research and GTFS Static generation for the SETP bus network in Pasto, Colombia.

## Source

Ruti SETP Android app (`com.ruti`), version 2.0.0, Hermes bytecode v96. Research targets embedded `rutas`, `horarios` and `horariosTwo` data. Online realtime endpoints returned empty results and are out of scope for now.

## APK analysis

The original APK/XAPK and full decompiled application code must not be committed or published. Use a trusted self-hosted runner with the source file at a local path accessible to the runner. Run the **Analyze Ruti APK** workflow manually, specifying that path. Analysis output stays on the runner by default. Only a SHA-256 manifest and extraction status are printed; review extracted data and redistribution rights before publishing any dataset. Do not execute the APK.

## Status

Research in progress. No validated GTFS feed yet. Route and stop IDs, coordinates, sequence, service calendars, frequencies and travel times must be verified before release. Use MobilityData GTFS Validator before publication.
