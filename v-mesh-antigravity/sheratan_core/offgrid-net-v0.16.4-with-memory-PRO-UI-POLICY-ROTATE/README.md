# Offgrid-Net v0 (Python-only, no external deps)

Dies ist ein **Starterpaket** für dein Off-Grid Mesh-Internet:
- Host-Daemon mit einfachen REST-Endpunkten (Python stdlib `http.server`)
- Broker (Mikro-Auktion + r-Dispatch)
- Storage (Chunking, Replikations-Stub, *unsichere* Demo-Verschlüsselung)
- Ledger (lokaler DAG + Merkle-Batch via Receipts)
- DTN/Radio Stubs

> ⚠️ Kryptografie & Funk sind **nur Stubs**. Nicht für Produktion!

## Quickstart

1) Host-Daemon starten (z. B. Port 8081):
```
python host_daemon/daemon_stub.py --port 8081 --node_id node-A
```

2) Broker gegen einen oder mehrere Hosts laufen lassen:
```
python broker/broker_stub.py --hosts http://127.0.0.1:8081 http://127.0.0.1:8082 --jobs 5
```

3) Quittungen exportieren (am Host):
```
curl http://127.0.0.1:8081/receipts/export
```

4) Ledger-Block erzeugen (Merkle-Root aus Receipts):
```
python -c "from ledger.local_dag import LocalDAG; import json,sys; import pathlib
# Lade letzten Batch
import glob
batch_files = sorted(glob.glob('_receipts/batch_*.json'))
if not batch_files: 
    print('Keine Batches gefunden'); sys.exit(0)
import json
batch = json.loads(pathlib.Path(batch_files[-1]).read_text())
print(LocalDAG('./_ledger').append_block(batch))"
```

## Endpunkte des Host-Daemon
- `GET /announce` → Status/Preise
- `POST /announce` → Update (min_oncall_percent, burst_percent_max, prices)
- `POST /toggle` → `{"active": true|false}`
- `GET /quote?type=compute&size=0.25`
- `POST /run` → `{"job_id":"...", "metrics":{"compute_tokens_m":0.1,"latency_ms":800}}`
- `GET /receipts/export` → Merkle-Batch + Items

## Hinweise
- Signaturen: **HMAC-SHA256** als Platzhalter (kein Ed25519/Nacl ohne Deps).
- Verschlüsselung: **XOR-Stub** nur zur Demonstration. Ersetze durch XChaCha20-Poly1305.
- Routing/Funk: Nur Interfaces. Integration von BATMAN-adv/LoRa in v0.2+.


---
## v0.1 Upgrade
- **Receipts Schema v0.1**: version/cluster_id/resource_type/units/metrics/proofs/cids/sig.
- **Broker SLA**: `--t_activate_s` Timeout (default 30s), einfache Reputation (`_reputation.json`).
- **CLI Tools** in `scripts/`: `toggle.py`, `quote.py`, `run_job.py`, `settle.py`, `status.py`.

### Beispiele (CLI)
```bash
# Host aktivieren/deaktivieren
python scripts/toggle.py http://127.0.0.1:8081/toggle true

# Quote abfragen
python scripts/quote.py http://127.0.0.1:8081 compute 0.3

# Job manuell auf Host starten
python scripts/run_job.py http://127.0.0.1:8081 job-123

# Quittungen exportieren (Host) und im Ledger batchen
curl http://127.0.0.1:8081/receipts/export
python scripts/settle.py

# Host-Status ansehen
python scripts/status.py http://127.0.0.1:8081
```


---
## v0.2 Upgrade — **PyNaCl Krypto + Mesh Discovery**

### 🔐 Kryptografie
- **Ed25519**: Signaturen für Receipts (echte Verify-Keys in `/pubkeys` & Receipts)
- **X25519**: Schlüsselaustausch (ECDH) für E2EE
- **XChaCha20-Poly1305**: Datenverschlüsselung (Bindings)

**Keys erzeugen:**
```bash
python keys/key_utils.py --node_id node-A
python keys/key_utils.py --node_id node-B
```

**Host-Daemon nutzt:** `--node_id` und liest `./keys/<node_id>.json` automatisch (Pfad in Code `keys_path`).  
Publiziere PubKeys:
```bash
curl http://127.0.0.1:8081/pubkeys
```

### 📡 Mesh Discovery (UDP Broadcast)
Starte Peer Discovery:
```bash
python discovery/peer_discovery.py --node_id node-A --endpoint http://127.0.0.1:8081
```
Gefundene Hosts landen in: `discovery/mesh_hosts.json`  
Broker nutzt diese Liste automatisch, wenn `--hosts` weggelassen wird:
```bash
python broker/broker_stub.py --jobs 5 --t_activate_s 20
```

> Hinweis: Für echtes Mesh-Routing (BATMAN/Babel) sowie LoRa/BT-LR ist die v0.3+ vorgesehen (Systemintegration).


---
## v0.3 Upgrade — **Mesh-Binding**

### 🔌 Mesh Binding & Health
- Module: `mesh/binding.py` — versucht **BATMAN-adv** (`batctl`) oder **Babel** (Socket) zu lesen.
- Fallback: `mesh/metrics.json` (manuell) oder auto-Discovery → schreibt `mesh/last_metrics.json`.
- Daemon: `mesh/metrics_daemon.py` (schreibt periodisch die Metriken).

**Starten:**
```bash
# (Optional) Falls batctl/babel nicht vorhanden: lege manuelle Metriken an
echo '{"proto":"none","neighbors":[],"routes":[],"health":{"interfaces_up":1,"mesh_ok":true}}' > mesh/metrics.json

# Daemon starten
python mesh/metrics_daemon.py --interval 5 --out ./mesh/last_metrics.json
```

### 🤝 Broker + Mesh
- Broker berücksichtigt `mesh/last_metrics.json` automatisch in der **Auktionsbewertung** (leichte Strafgewichtung, wenn `mesh_ok` false).
- Host-Daemon bietet `GET /mesh` an (Metriken ansehen/abfragen).

> Hinweis: Echte Systemintegration (Interfaces binden, LoRa/BT-LR) folgt in v0.4. Hier geht es um **Health/Discovery/Scoring-Hooks**, die off-grid funktionieren.


---
## v0.4 Upgrade — **Lokale Wallets + Settlement-Rechner**
- **Wallets**: `_balances.json` mit einfachen Konten (`system`, Host-Accounts = Host-URL)
- **Settlement**: `economy/settlement.py` rechnet aus **Receipts-Batch** die Rewards je Host (Units × Host-Preis)
  - wendet **host_reserve** (z. B. 1 %) an: Anteil an `system`
  - schreibt **Netto** dem Host-Konto gut
- **Transfers**: `scripts/transfer.py` mit **tx_fee** (Mittel zwischen `tx_fee_min`/`tx_fee_max` aus `config`), Fee → `system`

### Beispiele
```bash
# Nach Export eines Batches am Host:
curl http://127.0.0.1:8081/receipts/export

# Rewards verteilen (Node-ID → Host-URL Map angeben)
python scripts/settle_rewards.py '{"did:key:z-demo":"http://127.0.0.1:8081"}'

# Kontostände ansehen
python scripts/balances.py

# P2P-Transfer (mit tx_fee → system)
python scripts/transfer.py "http://127.0.0.1:8081" "alice" 12.5
python scripts/balances.py
```


---
## v0.5 Upgrade — **LoRa Announce/Keep-alive** (kein Bulk)

### Ziele
- Off-grid Discovery & Keep-alive auch ohne IP-Connectivity
- Pflegt `discovery/mesh_hosts.json` mit `via: "lora"`
- Keine großen Datenmengen über Funk: nur kleine JSON-Frames (≤ ~220 B)

### Voraussetzungen
- Optional: `pyserial` für echten UART-Zugriff
- Alternativ: **Mock-Transport** (Datei-basierter Bus) zum Testen ohne Hardware

### Nutzung
```bash
# (Optional) pyserial installieren
python -m pip install pyserial

# LoRa-Daemon starten (Mock-Transport)
python radio/lora_daemon.py --node_id node-A --endpoint http://127.0.0.1:8081 --interval 5

# In einem zweiten Terminal (simulierter zweiter Knoten):
python radio/lora_daemon.py --node_id node-B --endpoint http://127.0.0.1:8082 --interval 7

# Discovery-Datei wächst automatisch:
cat discovery/mesh_hosts.json
```

### Echte Hardware (Beispiel)
```bash
# Wenn ein LoRa-Modul als /dev/ttyUSB0 verfügbar ist:
python radio/lora_daemon.py --serial /dev/ttyUSB0 --baud 57600 --node_id node-A --endpoint http://192.168.4.1:8081
```
> Hinweis: Das Modul muss Zeilen-orientierte Frames transportieren (TNC/AT-Firmware o.ä.). Payload ist JSON pro Zeile.


---
## v0.6 Upgrade — **Erasure Coding (Reed–Solomon k/n = 12/20)**

- Reale EC-Implementierung in Pure-Python: `storage/ec_rs.py` (GF(256), Vandermonde, systematisch)
- CLI:
  - `storage/ec_encode.py <file> --k 12 --n 20 --shard_size 65536 --outdir ./_ec_out`
  - `storage/ec_decode.py --indir ./_ec_out --outfile ./_ec_restore.bin`

**Beispiel:**
```bash
# Datei in 20 Shards (12 Daten + 8 Parität) zerlegen
python storage/ec_encode.py ./README.md --k 12 --n 20 --shard_size 32768 --outdir ./_ec_out

# Beliebige 12 Shards behalten, Rest löschen… dann wiederherstellen:
rm ./_ec_out/shard_13.bin ./_ec_out/shard_14.bin ./_ec_out/shard_15.bin
python storage/ec_decode.py --indir ./_ec_out --outfile ./_ec_restore.bin
diff -q ./README.md ./_ec_restore.bin && echo OK
```

> Hinweis: Für große Dateien wird blockweise kodiert (Shard-Größe steuert RAM/Performance). Die Implementierung ist robust, aber nicht Vektorisierungs-optimiert; für Produktion ggf. in C/Rust/Numpy portieren.


---
## v0.7 Upgrade — **All-in-One Patch**

### 🧠 Broker-Scoring (Mesh-Kennzahlen)
- Nutzt `mesh/last_metrics.json` stärker:
  - **Neighbor-Count** → kleiner Bonus (mehr Nachbarn = stabiler)
  - **Path-Metric** (Surrogat) → leichte Strafgewichtung bei hohen Werten
  - Beibehaltung: Reputation + Mesh-Health

### 📡 BT-LR Anbindung (Mock)
- `radio/bt_lr_binding.py`, `radio/bt_lr_daemon.py`
- Wie LoRa: Beacons füllen `discovery/mesh_hosts.json` (`via: "bt_lr"`)

### 🔒 Signierte Public-Assets-Policy
- `assets/policy.py` – Ed25519-Signatur
- Schema enthält: `asset_id`, `license`, `distribution` (`replication r=5` oder `ec k/n`), `safety_tags`, `verify_key`, `signature`
- Beispiel:
```bash
python assets/policy.py --keys ./keys/node-A.json --node_id node-A --asset_id CID:abc123 --license MIT --mode replication --r 5 --out ./assets/policy.json
```

### 🧾 Auto-Settlement Daemon
- `economy/auto_settle_daemon.py`
- Baut Mapping `{node_id: endpoint}` aus Discovery, triggert lokal `/receipts/export`, settled neueste Batch → Wallets
```bash
python economy/auto_settle_daemon.py --interval 30 --host_reserve 0.01 --local_endpoint http://127.0.0.1:8081
```

> Hinweis: BT-LR ist ein Mock (file-bus) ohne echte BT-Stack-Abhängigkeiten – analog zum LoRa-Mock. Für echte Radioschnittstellen kommt ein Hardware-Binding in einer späteren Version.


---
## v0.8 Upgrade — **Data Path: E2EE + EC/Replication, put/get**

### Host-Erweiterung
- Endpunkte:
  - `POST /store` → `{asset_id, index, data_b64}` (verschlüsselter Shard)
  - `GET  /fetch?asset_id=ID&index=i` → `{data_b64}`

### Transfer
- `transfer/uploader.py` (`put`): wählbar **EC 12/20** oder **Replication r=5**
- `transfer/downloader.py` (`get`): holt Shards, entschlüsselt, rekonstruiert

### CLI
```bash
# EC 12/20 (Standard)
python scripts/put.py ./README.md --mode ec --k 12 --n 20 --shard_size 65536 --keys ./keys/node-A.json
python scripts/get.py asset-<hashprefix> --mode ec --k 12 --n 20 --outfile ./_downloads/readme.bin --keys ./keys/node-A.json

# Replikation r=5
python scripts/put.py ./README.md --mode rep --r 5 --keys ./keys/node-A.json
python scripts/get.py asset-<hashprefix> --mode rep --outfile ./_downloads/readme_rep.bin --keys ./keys/node-A.json
```

> Hinweis: Für EC-Decode nutzt der Downloader die in `_ec_out/<asset_id>_meta.json` gespeicherte `parity_matrix`. Beim Replikationsmodus ist keine Matrix erforderlich.


---
## v0.9 Upgrade — **Gossip + Reconciliation**

### Gossip-Service
- Datei: `broker/gossip_service.py`
- Endpunkte:
  - `GET /gossip/blocks` → Liste lokaler Ledger-Blöcke
  - `GET /gossip/block?name=...` → Einzelner Block
  - `GET /gossip/balances` → Wallet-Snapshot (`_balances.json`)
  - `GET /gossip/rep` → Reputation (`_reputation.json`)
  - `POST /gossip/append_block` → Block anhängen (wenn nicht vorhanden)
  - `POST /gossip/merge_balances` → Balance-Snapshot mergen
  - `POST /gossip/merge_rep` → Reputation mergen

**Start:**
```bash
python broker/gossip_service.py --port 8091 --peers http://127.0.0.1:9091 --interval 20
```

### Ledger-Merge Tool
- `ledger/merge_tool.py` → Einfache Union (append-only) aus einem anderen Ledger-Verzeichnis

### Wallet-Reconciliation
- `economy/wallet_reconcile.py` → naive Konfliktlösung (elementweise Max, Konflikte protokolliert in `_txlog.json`)

### Reputation-Sync (leicht)
- `scripts/rep_merge.py <remote_rep.json>` → nimmt Max pro Feld (hits/misses)

> Hinweis: Die hier implementierten Reconciliation-Regeln sind **bewusst konservativ & simpel** (ohne globale Finalität). Für produktive Nutzung später: transaktionsbasierte Wallet-Logs + Quorum-basierte Double-Spend-Prevention.


---
## v0.10 Upgrade — **Data Path Hardened**

### Was ist neu
- 🔁 **Retries + Exponential Backoff** (Store/Fetch)
- 🪟 **Windowing/Parallelität** (Standard `WINDOW=8`) für Upload/Download
- ♻️ **Resume** für Uploads via Manifest `_ec_out/<asset_id>_upload.json`
- 📜 **Logging** Zeitstempel via `transfer/common.py`
- 🧪 **Stresstest**: `scripts/stresstest_transfer.py` (3 MB Zufallsdatei EC 12/20 durch den Pfad)

### Beispiele
```bash
# Upload (EC, mit Windowing/Resume)
python scripts/put.py ./README.md --mode ec --k 12 --n 20 --shard_size 65536 --keys ./keys/node-A.json

# Download (EC, parallel)
python scripts/get.py <asset_id> --mode ec --k 12 --n 20 --outfile ./_downloads/readme.bin --keys ./keys/node-A.json

# Stresstest
python scripts/stresstest_transfer.py
```


---
## v0.11 Upgrade — **Wallet-TX & Quorum**

### Neuer Kern
- `economy/txlog.py` — **append-only Transaktionen** mit **Ed25519**-Signaturen, **Witnesses** und **Quorum-Finalität**
  - `create_tx`, `sign_tx`, `add_witness`, `finalize_tx(quorum_m)`
  - Bilanzen werden **nur** über finalisierte TXs angepasst

### Gossip-Erweiterung
- `broker/gossip_service.py` Endpunkte:
  - `GET  /gossip/tx_pool` → Pending TXs
  - `POST /gossip/tx_witness` → TX mit Witness in den Pool mergen

### CLI
```bash
# TX erstellen & an Peers senden (Autor signiert mit)
python scripts/send_tx.py <src> <dst> <amount> <fee> <nonce> ./keys/node-A.json http://127.0.0.1:8091

# TX zeugen (Witness)
python scripts/witness_tx.py <tx_id> ./keys/node-B.json http://127.0.0.1:8091

# Finalisieren (Quorum >= 2)
python scripts/finalize_tx.py <tx_id> 2
```

### Settlement-Integration
- `economy/auto_settle_daemon.py` erzeugt nun **TXs** statt direkter Saldenänderungen:
  - `mint → host` (Netto) & `mint → system` (Reserve) mit `meta.batch`
  - Quorum über `--quorum` steuerbar, Signatur via `--keys`

> **Hinweis:** Quorum-Mechanik ist leichtgewichtig und lokal. Für produktive Nutzung kannst du `gossip_service`-Peers gegenseitig Witnesses austauschen lassen und dann `finalize_tx.py` auf den Knoten triggern.


---
## v0.12 Upgrade — **Unified Radio & Robust Simulation**

### Neu
- `radio/transport.py` — einheitliche Schnittstelle:
  - **UDP Multicast** (Simulation, läuft auf jedem Laptop)
  - **LoRa Serial** (optional, `pyserial`)
  - **FileBus** (Fallback)
- `radio/frames.py` — kompaktes JSON-Frame-Format (beacon/ping/pong)
- `radio/radio_gateway.py` — Gateway, das Beacons sendet/empfängt und `discovery/mesh_hosts.json` füttert

### Schnellstart (Laptop, ohne Hardware)
```bash
# Terminal 1
python radio/radio_gateway.py --node_id node-A --endpoint http://127.0.0.1:8081 --transport udp --interval 5
# Terminal 2 (zweiter Knoten simuliert)
python radio/radio_gateway.py --node_id node-B --endpoint http://127.0.0.1:8082 --transport udp --interval 7

# Discovery prüfen
cat discovery/mesh_hosts.json
# Broker nutzt Hosts automatisch, wenn --hosts weggelassen wird
python broker/broker_stub.py --jobs 5
```

### Echte LoRa-Seriell (optional)
```bash
python -m pip install pyserial
python radio/radio_gateway.py --transport lora --serial /dev/ttyUSB0 --baud 57600 \  --node_id node-A --endpoint http://192.168.4.1:8081
```

> Hinweis: UDP-Multicast nutzt Gruppe `239.23.0.7:47007` (lokal). Das reicht für die Simulation und ist robust auf typischen Laptop-Setups.


---
## v0.13 Upgrade — **BLE (bleak) Scanner-Binding**

### Was bringt's?
- Laptops mit Bluetooth können nun **BLE-Scans** machen und so **Offgrid-Endpunkte** entdecken,
  wenn Nachbargeräte ihren Namen mit `OFFGRID:<b64url(endpoint)>` ausstrahlen.
- Das ist ein **minimal-invasiver** Weg, Discovery über BLE zu bekommen, ohne komplexes GATT/Advertising-Setup.

### Nutzung
```bash
# 1) bleak installieren
python -m pip install bleak

# 2) Scanner starten (alle 10s)
python radio/ble_binding.py --interval 10

# 3) Geräte-Name erzeugen (für Tests)
python radio/ble_name_encode.py http://127.0.0.1:8081
# -> OFFGRID:aHR0cDovLzEyNy4wLjAuMTo4MDgx
# Stelle den Bluetooth-Gerätenamen eines Testgeräts (z. B. Smartphone, anderes Laptop) auf diesen String
```

> Hinweis: **Advertising**/Senden über BLE aus Python ist plattformabhängig (über bleak meist nur eingeschränkt).
> Für Discovery genügt aber häufig **Scannen + ein anderes Gerät, das den Namen sendet**.
> Parallel kannst du weiterhin die **UDP-Multicast-Simulation** (v0.12) als Fallback nutzen.


---
## v0.14 Upgrade — **Parallelität stabilisiert**

### 🔐 Signierte Beacons (radio_gateway)
- `radio/frames.py`: `sign_frame`, `verify_frame` (Ed25519, PyNaCl)
- `radio/radio_gateway.py`: sendet **signierte** Beacons (`--keys`), akzeptiert nur **validierte** Frames

### 🧩 Atomische Discovery-Merges
- `discovery/atomic_hosts.py::merge_entry()`
- Verwendet in: `radio/radio_gateway.py`, `discovery/peer_discovery.py`, `radio/lora_daemon.py`, `radio/bt_lr_daemon.py`, `radio/ble_binding.py`

### 🚦 Transport-Priorität im Broker
- `broker/broker_stub.py`: via-Faktor **udp=1.0 < ble=1.05 < lora=1.1 < file=1.2** in der Auktionsbewertung

### 🧰 Host-Concurrency-Limiter
- `host_daemon/daemon_stub.py`: `/store` begrenzt parallele Uploads (Semaphore=4), bei Überlast **503 + Retry-After**

**Hinweis:** Passe die Semaphore bei Bedarf an (Code `STORE_SEM = threading.Semaphore(4)`).



---
## v0.14.3 Patch — dummy `receipts` package
- Adds `receipts/__init__.py` with a minimal `ReceiptStore` to satisfy host daemon imports.
- No behavior change beyond removing the ModuleNotFoundError.


---
## v0.15 — Quorum Auto-Finalizer (Uploads/Jobs/Tokens)

- `consensus/quorum.py` — generischer Quorum-Store (JSON-basiert)
- `scripts/quorum_cli.py` — CLI zum Anlegen/Acken/Listen
- `economy/tx_auto_finalizer.py` — beobachtet `_txpool.json` und ruft `finalize_tx` bei Quorum
- `transfer/uploader.py` — erzeugt Upload-Quorum (EC: required=k), ack't pro erfolgreichem Shard

### Beispiele
```bash
# Tokens: Auto-Finalizer starten
python economy/tx_auto_finalizer.py --quorum 2 --interval 3

# Upload-Quorum inspizieren
python scripts/quorum_cli.py --kind upload --id <asset_id> --show

# Job-Quorum (manuell)
python scripts/quorum_cli.py --kind job --id job-123 --required 2
python scripts/quorum_cli.py --kind job --id job-123 --ack_from node-A
python scripts/quorum_cli.py --kind job --id job-123 --ack_from node-B
```


---
## v0.15.1 — Weighted Acks + Age Decay

### Neu
- **Gewichtete Acks**: pro Node `weight_default` oder individuellen `weights[node_id]` setzen
- **Zeitlicher Decay**: exponentieller Verfall per `decay_half_life_s`; optional `max_age_s` (Acks verfallen ab Alter X)
- **CLI** `scripts/quorum_policy_cli.py` zum Setzen/Anzeigen der Policy
- Rückwärtskompatibel: alte `acks: ["node-A", ...]` werden beim Lesen migriert

### Beispiele
```bash
# Policy ansehen
python scripts/quorum_policy_cli.py --show

# Default-Gewicht = 1.0, Half-Life = 1h, max Age = 6h
python scripts/quorum_policy_cli.py --weight_default 1 --decay_half_life_s 3600 --max_age_s 21600

# Individuelle Gewichte setzen
python scripts/quorum_policy_cli.py --set_weight http://127.0.0.1:8081=1.0 --set_weight http://127.0.0.1:8082=1.5

# Upload-Quorum anlegen (required ist nun float-basiert möglich, z. B. 3.5)
python scripts/quorum_cli.py --kind upload --id <asset_id> --required 3.5

# Ack adden (Gewicht und Decay werden automatisch berücksichtigt)
python scripts/quorum_cli.py --kind upload --id <asset_id> --ack_from http://127.0.0.1:8082
python scripts/quorum_cli.py --kind upload --id <asset_id> --show
```


---
## v0.15.2 — Broker-Job-Acks + Auto-Weight-Feeds + per-Kind Decay

### Neu
- **Broker-Jobpfad**: bei erfolgreichem Assignment wird `add_ack(job_id="shard-<i>", "job", node_id=<host>)` aufgerufen.
- **Auto-Weights**: `scripts/quorum_policy_feed.py` setzt **Gewichte** aus Discovery-Transport (`udp/ble/lora/file`) und optionaler Reputation (`broker/_rep.json`).
- **Per-Kind Decay**: `scripts/quorum_policy_cli.py --kind <upload|job|token>` steuert getrennte `decay_half_life_s`/`max_age_s` pro Kind.

### Beispiele
```bash
# Policy-Feed starten (alle 10s)
python scripts/quorum_policy_feed.py --show

# Decay für Jobs schärfer, Uploads ohne Decay
python scripts/quorum_policy_cli.py --kind job --decay_half_life_s 1800 --max_age_s 7200
python scripts/quorum_policy_cli.py --kind upload --decay_half_life_s 0 --max_age_s 0

# Job-Quorum inspizieren
python scripts/quorum_cli.py --kind job --list
```


---
## v0.15.3 — Failover-Regeln (Decay-Stall → Reassign)

### Neu
- **Failover-Daemon** `scripts/quorum_failover.py`
  - erkennt **Stalls** (Summe der Gewichte wächst nicht mehr, Mindestalter erreicht, Cooldown und Retry-Budget)
  - schreibt Requeue-Events in `_requeue_jobs.json`
  - `--kind job` → konkrete Reassign-Ziele (basierend auf Discovery + via-Priorität)
  - `--kind upload` → erzeugt vorerst **Alerts** (da Quelle evtl. nicht mehr verfügbar)

- **Broker-Integration**
  - `broker/broker_stub.py` pollt `_requeue_jobs.json` und loggt Reassigns (`[broker][failover] reassign ...]`)
  - (Hook-Punkt vorgesehen, um echte Re-Dispatches einzubauen)

### Default-Parameter (änderbar)
- `--stall_age_s 90` (ab 90s Inaktivität)
- `--min_progress_delta 0.05` (unter 0.05 Gewichtszuwachs = kein Fortschritt)
- `--cooldown_s 60` (mind. 60s zwischen Reassigns pro ID)
- `--max_retries 3`

### Start
```bash
# auto-weights (optional)
python scripts/quorum_policy_feed.py --show

# failover-daemon (jobs)
python scripts/quorum_failover.py --kind job --interval 8 --stall_age_s 90 --min_progress_delta 0.05 --cooldown_s 60 --max_retries 3

# broker (liest requeue-file)
python -m broker.broker_stub --jobs 2
```


---
## v0.16-alpha — Sessions & Placement (prepared; disabled by default)
- `crypto/session.py` — sessions for UDP/File
- `placement/policy.py` — adaptive (k,n) placement
- `config/offgrid.defaults.json` — feature flags (all false)
Enable via `--noise 1` (gateway) and `--auto_place` (uploader).
