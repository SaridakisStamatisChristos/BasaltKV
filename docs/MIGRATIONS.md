# Format and Migration Policy

Current on-disk format version: **1**.

v0.1 implements no automatic migration. WAL, record, or snapshot versions other than 1 fail closed with an explicit `FormatVersionError`. Users must keep a backup before adopting a future version that introduces migration.

Compatibility promise for v0.1: a given BasaltKV 0.1.x implementation must not silently change the meaning of format version 1. Any incompatible change requires a new format version and an explicit migration design/test fixture. Backward migration/downgrade is not supported.
