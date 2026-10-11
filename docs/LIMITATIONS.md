# Limitations and Non-Goals

v0.1 intentionally does not implement distributed consensus, replication, clustering, sharding, SQL, remote multi-tenant hosting, authentication, distributed transactions, encryption at rest, long-lived MVCC snapshots, serializable transactions, online backup, background compaction, or multi-process concurrent writers.

Writer throughput is bounded by serialized commits and, in durable mode, one WAL `fsync` per transaction. Compaction blocks reads/writes while persisting a new snapshot and resetting the WAL. The full logical index resides in memory.

Power-loss semantics depend on documented local filesystem and storage guarantees. Windows lacks the POSIX directory-`fsync` step in this implementation. Network filesystem behavior is unsupported.
