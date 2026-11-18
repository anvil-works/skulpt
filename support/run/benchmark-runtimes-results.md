# Runtime results, 30 September 2026

The lexer pair is selected for staging in the parser project after a separate
checked-in client-module comparison. The measurements below retain the original
six-workload capture, including mixed small-case results. Runtime artifacts remain
private benchmark inputs; no installed runtime or release asset was replaced.

Skulpt adapter reference `480d7ee4b6638d139dbdba2b3c2c416be2881a22`, direct-AST
reference `deafa5692ebf56581efb3210e106c6fe9d4dbd60`, parser dev.5 reference
`3667c2129542f1dd457321c6b4e38ad1d4ebd8bd`. Frozen runtime artifacts also include
compiler patches `86a087e2ea2cd4786e1c3cf9556f3dcb40f9861a` and
`c6e7b0a5247edf12f4b95204d3fa226c3c8cbd81`. Their recorded build environment was
Node 26; measurement and candidate rebuilding used Node 22.15.0. Reports preserve
those distinct versions rather than implying identical build provenance.

Measurements used CPython 3.14.3, Apple M1 Pro, MacBookPro18,3, 10 logical CPUs,
32 GiB RAM and Darwin 24.5.0. Three fresh processes measured original, adapter and
direct-AST baselines. Five alternating-order pairs compared baseline and trial in
each parser integration, with original runtime measurements retained as a reference.
All six workload execution results matched CPython before timing. The adapter uses
the public parser callback; the direct runtime embeds the rebuilt candidate core.

[The summary](benchmark-runtimes-results.json) records initialization, first
operations, warmed median/p95, retained result memory, source and artifact hashes.
Raw batch means and individual samples remain in the evidence archive. The following
deltas are median paired changes in warmed batch-median latency; negative is faster.

| Workload             | Adapter AST change | Adapter compile change | Direct AST change | Direct compile change |
| -------------------- | -----------------: | ---------------------: | ----------------: | --------------------: |
| small                |             -10.6% |                  +0.4% |            +16.0% |                +12.0% |
| 50 functions         |              -9.9% |                  +1.3% |             -8.2% |                 -5.0% |
| 200 functions        |             -12.7% |                  -6.2% |            -14.5% |                -13.2% |
| 50 Unicode functions |             -12.7% |                  -3.1% |            -16.4% |                -12.2% |
| multiline expression |              -0.2% |                 -15.5% |            -10.7% |                -29.5% |
| list-method fixture  |             -10.2% |                  +1.9% |             -2.0% |                 +2.8% |

Large direct-AST cases show throughput gains. Tiny direct cases are mixed, with
substantial baseline variation; the small-case loss occurs in three of five pairs.
These consumer timings retain the standalone small-module p95 concern that caused
the initial rejection. The later client-module comparison supports retaining the
lexer work, with a focused tail/first-operation recheck still needed before release.

Median runtime load in the paired capture is 25.35 ms for original, 32.72 / 33.61 ms
for baseline / trial adapter and 27.25 / 28.21 ms for baseline / trial direct.
Load includes artifact evaluation. Returned AST/compiler-output retained bytes are
measured with five explicit-GC samples and reported separately from temporary
allocation; process RSS is not treated as peak parser memory.

| Runtime bundle   | Raw bytes | gzip bytes | Brotli bytes |
| ---------------- | --------: | ---------: | -----------: |
| original         |   616,317 |    163,663 |      132,450 |
| baseline adapter |   788,554 |    184,039 |      146,113 |
| baseline direct  |   761,007 |    185,047 |      146,476 |
| trial direct     |   760,935 |    185,025 |      146,346 |

The adapter artifact stays fixed and receives the parser callback separately. Its
parser core changes from 231,052 to 230,994 raw bytes, 37,181 to 37,165 gzip bytes,
and 28,392 to 28,399 Brotli bytes. That small increase is recorded and was not a
rejection reason. Artifact SHA-256 hashes and full provenance are in the summary.

## Validation and follow-ups

The direct trial passed 562 execution, 465 Python 2 and 2,901 Python 3 unit checks,
seven CPython tokenizer and two Skulpt compatibility checks, and 49 location checks.
The adapter passed 465 Python 2 and 2,901 Python 3 unit checks, the same tokenizer
checks, and Python 2/3 REPL checks. Its ordinary dual-frontend AST comparison covered
564 sources: 563 exact matches and one asserted annotation extension.

Adapter execution goldens passed 560 of 562. The same two failures reproduce with
the baseline parser: `t502.py` differs on legacy slice/maxint/explicit `[::]` output;
`t905.py` exercises the intentionally supported Python 2 annotation extension.
These are existing golden differences, not new regressions, and were not expanded
into unrelated fixes during this pass.

Keep future optimization validation on real execution, tokenizer, REPL and location
paths. Small-input measurements need more focused evidence before a speed claim.
Python 2 remains bounded legacy coverage. Memoization redesign and incremental
parsing remain separate work.

See [the benchmark instructions](benchmark-runtimes.md) for commands. Selected raw
reports, tested runtime/parser bundles, manifests, profiles, patches and logs are
in the parser checkout's ignored `tmp/performance-pass/evidence.tar.gz`.
`skulpt-baseline.json` records the three-process baseline;
`skulpt-paired.json` records the five-pair comparison.
