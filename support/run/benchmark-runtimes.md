# Compiler and execution measurements

`benchmark-runtimes.mjs` compares original, adapter and direct AST runtimes in
fresh Node processes. Inputs are individual `{name, source}` objects in a JSON
array. Workload selection belongs to the consuming application; this harness
does not collect app sources. Use Node 22 and CPython 3.14.3.

The existing `--original` mode compares frontend artifacts. `--baseline-parser`
and `--baseline-direct` add matching reference pairs and require identical
generated JavaScript when running `--compile-only`.

Use `--optimizer` instead of `--original` to compare normal and optimized ASTs in
both modern compiler paths. The optional bundle's public `optimizeAST` is inserted
at the test-only parsing boundary, guarded for Python 3. No runtime configuration
or public parsing behavior changes. Optimization intentionally changes generated
code, so this mode verifies acceptance/compilation and records code hashes/bytes
rather than requiring equal hashes.

```sh
node support/run/benchmark-runtimes.mjs --adapter /path/to/adapter.js \
  --direct /path/to/direct.js --parser /path/to/core.js \
  --optimizer /path/to/optimize.js --stdlib /path/to/stdlib.js \
  --cases /path/to/cases.json --compile-only --rounds 5 --output /tmp/compile.json
```

Without `--compile-only`, execution output is compared with CPython before timing.
Application modules needing network/UI services can use compilation-only checks;
they still need their application's real execution tests before rollout.

`--execute-only` compiles synchronous workloads once per case, evaluates the
generated JavaScript into a callable, and times calls with fresh module globals.
Compilation/evaluation setup, first execution and warmed execution are separate.
Use import-free, synchronous execution probes; the standard library is loaded for
builtins such as `print`. Suspensions are rejected during correctness preflight.

```sh
node support/run/benchmark-runtimes.mjs --adapter /path/to/adapter.js \
  --direct /path/to/direct.js --parser /path/to/core.js \
  --optimizer /path/to/optimize.js --stdlib /path/to/stdlib.js \
  --cases /path/to/execution-cases.json --execute-only --rounds 5 \
  --output /tmp/execution.json
```

Reports retain initial load time/heap, first operations, calibrated batches,
individual latency samples, warmed median/p95, retained output heap and artifact
hashes. Retained heap is not peak memory. Optimizer comparisons default to five
rounds; ordinary artifact comparisons default to three. Engine order alternates
each round. `--rounds 0` writes correctness and artifact metadata without timing.
Use `--phase parse` or `--phase compile` to measure one compiler phase. For a
fresh-engine first-compilation comparison, pass exactly one source case and
`--phase compile`; the measured worker will not parse another case first.
Worker inputs and reports use temporary files to avoid synchronous pipe stalls
observed on macOS. File I/O and serialization stay outside timed sections. Each
worker and CPython acceptance check has a three-minute timeout; temporary files
are removed when the child completes or fails.
Keep builds, tests and profiles out of measured runs. Synthetic execution wins do
not by themselves justify changing a consumer's default compiler policy.
