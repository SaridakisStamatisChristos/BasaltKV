# Assumption Ledger

| ID | Statement | Criticality | Confidence | Affected surfaces | Invalidation trigger |
|---|---|---:|---:|---|---|
| A-01 | Python 3.11+ is an acceptable v0.1 implementation target because the brief leaves language choice open and prioritizes correctness/portability over peak throughput. | MEDIUM | High | package, CI, architecture | user mandates another language or measured workload disproves suitability |
| A-02 | Default durability is `durable`; callers must opt into relaxed fsync semantics. | HIGH | High | API, WAL, docs | user contract requires a different default |
| A-03 | One writable process at a time is acceptable; concurrent writers inside that process are serialized. | HIGH | High | locking, transactions | multi-process concurrent writes become a requirement |
| A-04 | Empty binary keys and values are legal; limits are 1 MiB keys and 64 MiB values. | MEDIUM | Medium | API, parsers, docs | compatibility contract chooses different bounds/legality |
| A-05 | Local filesystem semantics are the supported persistence target; network/distributed filesystems are non-goal until validated. | HIGH | High | durability, security | deployment requires network filesystem support |
| A-06 | No open-source license grant should be invented when the brief does not specify one. | HIGH | High | repository legal posture | repository owner explicitly selects a license |
| A-07 | v0.1 uses format version 1 and has no automatic migration. | HIGH | High | persistent compatibility | a second format version is introduced |
| A-08 | CRC32 is an integrity/corruption detector, not a cryptographic authenticity mechanism. | MEDIUM | High | format, verifier, security | threat model requires tamper authenticity |
