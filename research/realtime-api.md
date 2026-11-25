# Ruti SETP 2.0.0 — realtime API research

Status: parked pending evidence of live services (2026-11-25).

## Static evidence

Source: Ruti 2.0.0 XAPK, Hermes v96. See [analysis run 45644979309](https://github.com/ColombiaTransit/gtfs-pasto/actions/runs/45644979309) and `scripts/inspect_realtime.py`.

Base URL: `http://181.49.177.91:8086/if/rs/pasto`.

| Wrapper | Path | Identifier |
|---|---|---|
| getLineInfo | /line/{id} | JRNYPATTRN_ID, confirmed in map caller |
| getDataParaderos | /stop/{id} | Stop identifier type not confirmed |
| getInfoVehicle | /loc/{id} | Presumed vehicle ID, not confirmed |

Module 1042 (decompiled lines 404869–405045) uses fetch with default GET, no body or explicit query parameters, and Content-Type: application/json. Authorization is added only if busApiToken is nonempty; the bundled token is empty. Successful responses are parsed as JSON. The line screen groups services by CURRENT_STOP_ID and reads VEH_ID (lines 403840–403959). The map caller uses JRNYPATTRN_ID (486670–486730); refreshes immediately and every 10,000 ms while focused, clearing the interval on cleanup (486949–486978). Two direct getLineInfo call sites were found; no direct callers of the other wrappers were found in this audit. No active socket connection was established by the static evidence; configured socket address is private.

## Observed HTTP tests

The base URL returned HTTP 404 in the user's browser. Earlier line tests (including C1 pattern IDs 1000000386, 1000000387 and 1000000388) returned HTTP 200 with an empty services array. Earlier stop tests also returned empty services; /loc/ without an ID returned 404.

Latest user-supplied Windows curl test:

```cmd
curl.exe -i -H "Content-Type: application/json" "http://181.49.177.91:8086/if/rs/pasto/line/1000000388"
```

```http
HTTP/1.1 200 OK
Date: Wed, 25 Nov 2026 15:17:03 GMT
Server: Apache/2.2.17 (Win32) mod_jk/1.2.31
Set-Cookie: SCOUTER=[redacted]; Expires=Mon, 13-Dec-2094 18:30:01 GMT
Content-Length: 15
Content-Type: application/json

{"services":[]}
```

Local Pasto time: 10:17:03 (UTC-5), Wednesday, within the Ruti C1 circular pattern's listed weekday service window 05:55–18:19. Cookie value omitted because it is not necessary to reproduce the research.

## Interpretation and outstanding checks

The server responds in the expected JSON format, but no active services were observed. This does not establish that realtime service has been permanently discontinued, nor rule out upstream faults or geographic differences. No populated response has been captured; vehicle position, arrival-time fields and the exact meaning of CURRENT_STOP_ID remain unverified.

Optional low-volume manual follow-up: compare requests with and without a retained SCOUTER cookie, and check C2 (1000000385), E4 (1000000375), E3 (1000000377), E2 (1000000379), E1 (1000000381), and C3 (1000000362) during operating hours. These follow-up tests have not been reported as completed. Do not commit cookie jars.

No frequencies can be derived from empty responses. If populated responses become available, evaluate repeated vehicle/stop observations for measured headways, keeping them separate from approved schedule frequencies. No continuous polling job has been enabled.

Official frequency research remains open: resolutions 2218–2221 of 2022 and operational studies from 2020, 2023 and 2024. Contract 2023-143 explicitly includes support for schedules and frequencies for a typical operating week, but the technical results were not located in the public contract records reviewed.
