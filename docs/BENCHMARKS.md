# Benchmark Methodology

Performance is secondary to correctness. `benchmarks/bench.py` is a deterministic, single-process harness that reports environment metadata and measures:

- sequential durable puts;
- random gets;
- batched writes;
- mixed reads/writes;
- reopen/recovery time;
- compaction time;
- `.bkv` bytes before/after compaction.

Run `PYTHONPATH=src python benchmarks/bench.py --quick` for a short smoke benchmark or omit `--quick` for the larger local workload.

The harness has **no competitor baseline** and the project makes no SOTA/superiority claim. Numbers from one machine are observations, not portable performance guarantees.
