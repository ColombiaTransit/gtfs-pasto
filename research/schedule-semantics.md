# Ruti SETP 2.0.0 schedule semantics

Evidence: [analysis run 45627269866](https://github.com/ColombiaTransit/gtfs-pasto/actions/runs/45627269866), decompiled pseudocode lines 412856–412903; database initialization lines 243203–243212; persistence lines 395708–395753.

The app initializes SQLite from `horariosTwo` (85 numbered-window records). `ID` joins to `JRNYPATTRN_ID`. The UI explicitly labels slot 1 `L–V`, slot 2 `SÁB`, slot 3 `DOM`. Each slot reads `DesdeN` and `HastaN` and checks `HorarioN` for truthiness and inequality to string `null`. The position, rather than the numeric value, determines the displayed service day. The tutorial describes Sunday and holidays together; treating Colombian holidays as Sunday service is the proposed GTFS calendar policy, not a separately verified holiday timetable.

Do not interpret Horario values as headways. No departure frequency or complete departure list has been verified. The displayed windows alone do not establish exact first/last departures. The audit found 87 patterns, 85 matched schedule IDs, 46 patterns and 759 stop IDs after applying the app's MV filter; the operational meaning of MV remains unverified. Two patterns have no schedule: 1000000310 and 1000000382.
