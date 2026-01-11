# Offgrid-Net v0 — Spezifikation (Starter)

**Ziel:** Off-grid Mesh-Internet ohne zentrale Infrastruktur. Nur Hosts + erreichbare User. 
Selbstorganisierte Speicherung, Rechnen, Token-Ökonomie (work-mint-only), ≥10% On-Call, 
lokale Cluster-Ledger (DAG), CRDT-Metadaten, DTN-Store&Forward, LoRa/BT-LR nur für Signalisation.

## Topologie
- Mesh über Wi-Fi Direct / 802.11s / Hotspot, optional Ethernet; LoRa/BT-LR für Signalisation.
- Routing-Empfehlung: BATMAN-adv oder Babel. DTN für Partitionen.

## Ressourcen & Ökonomie
- On-Call: Mind. 10% abrufbar; nur tatsächliche Nutzung vergütet („No need ⇒ No tokens“).
- Minting: Work-Mint-only (Nutzung schafft neue Tokens). Optionale Mini-Genesis (1% je Cluster).
- Gebühren: Host-Reserve ≈1% beim Settlement (Systemfonds lokal), Transfer-Fee 0.1–1% pro P2P-Token.
- Token: intern, p2p handelbar, nicht gepeggt. „Hardware host ↔ Tokens ↔ Hardware use“.

## Storage
- Content-Addressed (SHA-256 CID), Chunking (1–4 MiB), Replikation r=4–5 (klein/heiß), EC 12/20 (groß).
- E2EE clientseitig (hier als Stub; echte Kryptografie in v0.2+). Metadaten via CRDT (eventual consistency).

## Compute
- Mikro-Auktion im Cluster, r-Dispatch (2–3), SLA: T_activate (Compute ≤30s, Storage ≤120s).
- Modi: Batch-Serving (einfach), Async-RAG, später Parallel-Serving (nur IP mit hoher Bandbreite).

## Ledger & Belege
- Lokaler DAG je Cluster (append-only), Quittungen signiert (Stub: HMAC-SHA256).
- Batching: Merkle-Root pro N Tasks. Cluster-Merge via Gossip / DAG-Union.

## Sicherheit
- Identität: DID/Key (Stub), E2EE (Stub), Audit-Proben probabilistisch, Availability-Challenges.
- Missbrauch: Reputationsabzug; optional lokales Slashing.

## Schnittstellen (lokal)

Host-Daemon:
- `/announce`, `/toggle`, `/quote`, `/run`, `/receipts/export`

Broker:
- Mikro-Auktion, r-Dispatch, T_activate-Checks, Gossip/DTN-Queues.

## Default-Parameter
- min_oncall_percent: 10, burst_max: 60, redundancy r=2 (Compute), r=4–5 (Public), EC 12/20 (Groß).
- host_reserve: 1%, tx_fee: 0.1–1%, batch_size_tasks: 500, receipts_merkle: true.

> **Hinweis:** Diese v0 referenziert kryptografische / routing-nahe Funktionen nur als Stub, um ohne externe Abhängigkeiten lauffähig zu sein.
