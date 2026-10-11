# Security and Trust Boundary

BasaltKV is not an authentication, authorization, encryption, or sandboxing product.

## Trusted

- the application process and Python interpreter;
- the operating system kernel and local filesystem contract;
- callers allowed to access the database directory.

## Untrusted / malformed inputs

Persistent database bytes are treated as potentially malformed. Parsers check magic/version fields, flags, transaction state, sequence continuity, CRC32, key/value length bounds, snapshot ordering, and trailing bytes before accepting state.

## Resource bounds

Keys are capped at 1 MiB and values at 64 MiB. Persisted length fields are checked before payload reads. This bounds per-record allocation driven by attacker-controlled file bytes, but an attacker with filesystem write access can still cause denial of service by creating very large files, repeated valid records, or storage exhaustion. v0.1 does not claim protection against such resource-exhaustion attacks.

## Paths and permissions

BasaltKV creates files using the process umask/default OS permissions. It does not follow user-supplied per-record filesystem paths; all internal persistence filenames are fixed under the opened database directory. Symlink attacks by an adversary who can modify the database directory concurrently are outside the trusted-directory model.

## Filesystems

Remote/network filesystem lock and durability semantics are not trusted. Use a local filesystem unless independently validated.
