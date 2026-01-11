Offgrid-Net memory v0.17.0 - minimal viable memory core
-----------------------------------------------------
Deutsch dokumentiert: Ziel ist eine speicher- und netzwerk-effiziente 'Erinnerung'-Schicht.

Enthaltene Module:
- memory/store.py       : SQLite + chunk storage (zlib)
- memory/synopses.py    : Bloom & Reservoir (lightweight)
- memory/retention.py   : Budget allocation + token multipliers
- memory/compact.py     : Micro-summary writer (json)
- memory/api.py         : einfache handler-funktionen für host-daemon

Installation / Nutzung (lokal):
1. Kopiere das Verzeichnis 'memory' in dein Projekt.
2. Integriere memory.api.ingest_endpoint in deinen Host-Daemon REST-Handler.
3. Setze Umgebungsvariablen falls nötig: OFFGRID_MEMORY_DB, OFFGRID_CHUNK_DIR, OFFGRID_CHUNK_THRESHOLD.

Hinweise:
- Keine externen Abhängigkeiten (nur Python Stdlib).
- Default-Budgets sollten per config gesetzt werden (siehe retention.compute_effective_budget).
