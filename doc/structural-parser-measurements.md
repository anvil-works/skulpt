# Structural parser adapter measurements

This checkpoint measures the temporary adapter through the real compiler and
expands regression coverage. The adapter remains opt-in. It does not establish
Python 3.14 runtime support or readiness to change application defaults.

## Compatibility findings

The old frontend passed 2,901 Python 3 tests and 465 Python 2 tests. The initial
adapter run passed 2,891 Python 3 tests with ten failures, and 449 Python 2 tests
with one module failing to load. Investigation separated adapter bugs from
diagnostic and optional-capability differences:

- CPython encodes f-string conversions as integer character codes; Skulpt expects
  `"r"`, `"s"` and `"a"`. Translate them explicitly. Seven failing tests were in
  f-string suites. The initial numeric `!r` test missed this because string and
  repr results were identical. New execution coverage checks string repr, ASCII
  conversion and formatting against both CPython and old Skulpt.
- An absent `finally` suite is an empty array in CPython's AST but null in Skulpt.
  Skulpt tests truthiness, so the array activated finally control flow and broke
  two continue/break tests. Preserve the old sentinel. A new independent execution
  comparison protects continue within a try/except without finally.
- One grammar test required the old tokenizer's `EOF` wording. It now also accepts
  CPython's more specific unclosed-parenthesis message. The exception remains a
  syntax error; the diagnostic is not degraded to match the old one.
- The Python 2 integer test includes named Unicode escapes in a triple-quoted
  string used as a disabled test comment. Lean core correctly requests the
  optional database before parsing that module. Do not ignore escapes in unused
  literals or add the database to lean core to hide this difference.

After the fixes, Python 3 passes **2,901/2,901** with lean core. Python 2 passes
**465/465** when the optional resolver is explicitly supplied. Without it, the
integer module remains a capability requirement; its sixteen tests did not run
in the initial lean pass. This is not full lean-only Python 2 suite parity. The
40 focused execution/error comparisons also pass on the optimized build.

For the resolver validation, pass a module like this to `--source-parser`:

```js
import { parseModule as core } from "/path/to/parser/dist-core/index.js";
import { unicodeName } from "/path/to/parser/dist-core/unicode-names.js";
export const parseModule = (source, options) => core(source, { ...options, unicodeName });
```

The optional resolver is not loaded by timing workers or included in bundle totals.

## Measurement method

`support/run/benchmark-structural-parser.mjs` checks execution through both
frontends before timing. Python 3 outputs also match pinned CPython 3.14.3; the
legacy workload uses old Skulpt as its compatibility oracle. Five synthetic
workloads cover a small assignment, 50 and 200 functions with comprehensions,
a 50-function Unicode variant, and a 50-function Python 2 octal/long variant.
These are controlled inputs, not a representative deployed-app corpus.

Each frontend/phase/workload runs in a fresh Node process. Three rounds alternate
frontend order. Workers warm up with 30 operations, calibrate batch length, then
record seven batches targeting about 100 ms each, capped at 1,000 operations, so
the tiny-input batches are shorter. Report medians of per-process
medians. Parsing includes adaptation. Compilation includes parsing, adaptation,
symbol-table analysis and JavaScript generation, but not execution. Both paths
use the same optimized Skulpt bundle. Builds and suites finish before timing.

Load time/heap include the extra parser import only for the adapter. Retained
memory keeps sixteen returned ASTs or compilation results after GC; it is not
temporary allocation volume or peak parser memory. RSS is the whole worker's
high-water mark, including warmup and retention measurements. GC-sensitive figures
need repeated interpretation, not hard thresholds.

```sh
node support/run/benchmark-structural-parser.mjs /path/to/parser/dist-core/index.js /tmp/adapter-benchmark.json
```

## Timing and memory results

Measured on an Apple M1 Pro, macOS arm64, Node 26.7.0. Values below are milliseconds;
the [raw report](benchmarks/structural-parser.json) includes all 60 process runs,
batch samples, source text/hashes and exact bundle hashes.

| Workload | Old parse | Adapted parse | Old compile | Adapted compile |
| --- | ---: | ---: | ---: | ---: |
| Small assignment | 0.024 | 0.015 | 0.033 | 0.024 |
| 50 functions | 3.588 | 1.264 | 4.622 | 2.315 |
| 200 functions | 15.764 | 6.021 | 21.747 | 11.749 |
| Unicode, 50 functions | 3.641 | 1.417 | 4.732 | 2.456 |
| Python 2, 50 functions | 1.152 | 0.491 | 1.456 | 0.795 |

On the larger Python 3 workloads, parsing including adaptation is 61–65% faster
and compilation is 46–50% faster. The Python 2 workload improves by 57% and 45%,
respectively. These are steady-state improvements on these inputs, not a promise
about arbitrary applications or startup. No adapter-only timing was measured, so
this does not quantify the conversion cost or predict gains from removing it.

Loading the additional parser costs roughly 3–5 ms and 0.55 MiB of heap in these
processes. Faster first parsing does not always recover that cost for a tiny script.
High-water RSS is mixed: the large workload decreases, while several smaller
workloads increase. Calibrated batch counts also differ, so workers perform different
numbers of operations. Do not interpret RSS as a controlled per-parse peak.

The post-GC retention probe produced negative heap deltas on some inputs, showing
that unrelated collection/heap changes overwhelmed the retained-result signal.
It is recorded as `heapDeltaBytesPerResult` for transparency, not treated as an
AST size or evidence of lower retained memory. A reliable retained-memory or peak
allocation comparison is still outstanding. No general memory improvement is claimed.

The measured speed gain justifies continuing the opt-in integration. Next use
representative application inputs and decide how to retire the old frontend before
changing defaults; the current size and startup overhead remain real tradeoffs.

## Bundle sizes

Both Skulpt builds use the existing production build on Node 26.7.0. Baseline
`feat/nonlocal` at `86a1844a5b6016faf9dd535ed3e57d6321d1f25c` was built in a separate
worktree. Candidate includes this checkpoint's adapter fixes. Build metadata also
differs between revisions. Exact hashes and sizes are in
[bundle data](benchmarks/structural-parser-bundles.json).

| Artifact | Raw bytes | Gzip bytes | Brotli bytes |
| --- | ---: | ---: | ---: |
| Baseline Skulpt runtime | 620,275 | 163,661 | 132,942 |
| Runtime with adapter and old frontend | 626,216 | 165,356 | 134,373 |
| Separate lean parser | 230,871 | 37,118 | 28,333 |
| Candidate total, separately compressed | 857,087 | 202,474 | 162,706 |

Temporary dual-frontend deployment adds 38,813 gzip bytes: 1,695 in Skulpt plus
37,118 for the parser. This is not eventual replacement size; the old frontend
is still present. Figures exclude the standard-library bundle and the application
on both sides. They are not the size of the entire Skulpt deployment.
