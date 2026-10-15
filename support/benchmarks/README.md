# Runtime performance review

This change targets Python execution in Chrome/V8: fewer temporary Python
objects, callback/chain calls and generic dispatches in common builtin paths.
It also fixes slice reads when `__index__` mutates the target list. Compiler
constant indexing is a small secondary improvement; compilation is excluded
from the runtime comparisons below.

## Review entry points

Read the ten implementation commits in order, followed by the benchmark commit.
Each implementation commit includes its helper and callers together.

1. `src/compile.js`: constant lookup/literal pooling; guarded literal numeric
   operations and list reads; ordinary Python method calls and global reads.
   Method lookup stays fresh and precedes argument evaluation. Native methods,
   properties and other custom descriptors, instance shadows, custom access
   and starred/keyword calls keep
   generic dispatch. Numeric subclasses, large integers and overflow also
   retain generic behaviour. Local variables already use JavaScript variables.
2. `src/misceval.js`, then `enumerate.js`, `map.js`, `zip.js` and `filter.js`:
   synchronous iteration avoids suspension chains; resumable paths retain the
   callback, accumulator and next position. `iterArray` is used per output row
   by map/zip and avoids constructing a synthetic iterator each time.
3. `list.js`, `tuple.js`, `abstract.js`, `slice.js` and `bytes.js`: bulk copying,
   exact-sequence extension/unpacking and indexed loops replace per-item calls.
   Index conversion precedes reading list storage and normalising slice bounds,
   so conversion can clear, grow or replace that storage safely.
4. `builtin.js`, `range.js`, `dict.js` and `str.js`: native integer summation,
   two-argument min/max, arithmetic range queries, cached-hash dictionary copying
   and direct exact-dict keyword traversal. The native sum accumulator owns the
   result until it is boxed once on overflow/type transition. Range storage is
   still materialised; this change speeds queries, not construction.
5. Regression tests beside each change, then the measurements and harness here.
   Tests cover subclass overrides, ordering, mutation, overflow, partial errors,
   dictionary collisions/hash reuse and suspension through the real paths.

The hardest block is `cmethodcall`. A simpler emitter using one argument array,
prepending the receiver and pushing each argument was implemented and tested.
Three alternating Chromium rounds slowed `field` by 5.2%, ordinary method calls
by 10.4% and the method workload by 7.6%, with every pair slower. The retained
emitter keeps its direct-call flag and generated array literal; `argsWithSelf`
and local comments explain the binding bypass and lookup order. Raw evidence:
`review-common-args-chromium.json` in the archive. This is a readability tradeoff
measured against the preceding upstream-based candidate, not the Anvil baseline.

## Exact Anvil-base comparison

Base: Anvil `master` at `3b7a796ebdfa9b19209c0f6587af1b22ae55f413`. Implementation candidate:
`f294e6c5f5cd9ef58cf168ad0dbe8c1649cf9bdb`. The PR contains only the runtime work; Anvil's
packaging and Safari fixes are preserved. The production core bundle grows
**6,025 bytes (1.0%)**, from 615,874 to 621,899 bytes.

- Baseline SHA-256: `3861f82471b0ebe4d25f3b5ce82eb4b39d9ba1f3455a047a17d9ec850bebb2b7`.
- Candidate SHA-256: `5d7253bd89e73d8d1b7a8df5d5fdc1a3215ab10c4f3a69464d51f02c645c7b77`.

| Workload | Before | After | Less runtime |
| --- | ---: | ---: | ---: |
| `list-slice-consumed` | 38.550 ms | 11.671 ms | 69.7% |
| `list-extended-assign-forward` | 2.586 ms | 0.493 ms | 80.9% |
| `range-count-index` | 38.950 ms | 0.030 ms | 99.9% |
| `list-inplace-extend` | 2.348 ms | 0.376 ms | 84.0% |
| `dict-copy` | 10.914 ms | 5.846 ms | 46.4% |
| `keyword-unpack` | 3.505 ms | 2.300 ms | 34.4% |
| `bytes-list` | 8.100 ms | 4.206 ms | 48.1% |
| `bytes-search` | 9.863 ms | 0.892 ms | 91.0% |
| `lookup-globals` | 0.985 ms | 0.806 ms | 18.1% |
| `lookup-methods` | 0.802 ms | 0.648 ms | 19.2% |
| `iteration-sum` | 0.264 ms | 0.113 ms | 57.4% |
| `iteration-zip` | 2.617 ms | 1.090 ms | 58.3% |
| `iteration-map` | 1.100 ms | 0.588 ms | 46.5% |
| `field` | 134.400 ms | 98.600 ms | 26.6% |
| `arithmetic` | 0.975 ms | 0.700 ms | 28.2% |
| `binary-trees` | 2.648 ms | 1.435 ms | 45.8% |

The 6,000-frame `field-long` fixture measures **3.972 →
2.945 seconds (25.9% less runtime)** across three rounds.
All three pairs improve (25.0–28.2%). All five pairs improve for each
standard workload in the table. These are cumulative base-to-candidate changes;
the historical incremental slice/map/etc. results measure different bundle pairs.

These are workload-specific measurements, not an application-wide guarantee.
The fully consumed slice case sums every copied element; copy-only historical
probes are not used to forecast application speed. Range probes repeat queries
on an already constructed range. Dictionary copies preserve cached hashes;
subclasses/generic mappings and custom comparisons retain fallback paths.

Production bundles, headless Chromium 153.0.8010.12 on Apple M1 Pro. Each
engine/case/round starts a fresh temporary browser, with alternating engine
order. Standard cases use five warmups, three calibration calls and seven timed
batches targeting 75 ms; long field uses one warmup, one calibration call and
three timed invocations per round. Results are medians of worker medians.
Imports, library preloading and compilation are untimed; allocation and natural
GC remain timed. Comparisons, builds, profiles and tests run separately.
Each worker’s check result is compared with CPython 3.14.8+ using
relative/absolute tolerance `1e-9`. Timed invocations are not individually checked.

The exact Anvil candidate passes `npm test`: **562 execution tests** (plus two
disabled), **465 Python 2 tests** and **2,903 Python 3 tests**, with zero failures.
The host iteration/suspension and compiler-literal emission checks also pass.
The three benchmark tools were checked with Anvil's library groups; the Node
and profile smoke reports are tooling checks, not additional performance claims.

This correctness evidence and the fresh-context reviewability pass are separate
assessments. Reviewability does not establish whole-PR correctness. Runtime
semantics have a broad reach despite the narrow fast-path guards; Chrome/V8 is
the measured target and other engines still need maintainer assessment.

## Reproducing

Build base and candidate separately, saving each `dist/skulpt.min.js` and its
matching `.map` before changing commits. Use `npm run build` with installed
repository dependencies. The local shared webpack installation required
`NODE_OPTIONS=--openssl-legacy-provider`; that is an environment requirement,
not a source change. Playwright is supplied explicitly and is not a new runtime
or project dependency. Use a complete stdlib for both bundles; Anvil production
builds require the three JSON groups below, preloaded before untimed imports.
Reports record library and core-bundle hashes.

```sh
node support/benchmarks/compare-browser.mjs \
  --baseline /tmp/skulpt-base.js --candidate /tmp/skulpt-candidate.js \
  --playwright /absolute/path/to/playwright --python /absolute/path/to/python3 \
  --stdlib-groups dist/skulpt-stdlib-1.json,dist/skulpt-stdlib-2.json,dist/skulpt-stdlib-3.json \
  --case field,lookup-methods,iteration-map,iteration-sum,list-slice-consumed \
  --rounds 5 --output /tmp/runtime-comparison.json
```

Select `--case field-long --rounds 3` for the extended field fixture. It repeats
30 independent 200-frame simulations, resetting and accumulating a checksum each time;
a single invocation takes several seconds. `field.py` preserves the original
simulation's grid, drawing comprehension, vector calculations and bouncing ball.
The original source file is not modified. `cases.mjs` contains the smaller
probes and controls. `compare.mjs --execution-only` provides fresh-process Node
comparisons with the same baseline/candidate, stdlib and case flags (no
Playwright flag). `javascript-loops.mjs` isolates loop syntax overhead; its
results do not imply a blanket rule to replace JavaScript array callbacks.

Capture profiles separately from timing comparisons:

```sh
node support/benchmarks/profile-browser.mjs \
  --bundle /tmp/skulpt-candidate.js \
  --playwright /absolute/path/to/playwright \
  --stdlib-groups dist/skulpt-stdlib-1.json,dist/skulpt-stdlib-2.json,dist/skulpt-stdlib-3.json \
  --case field --seconds 3 --output /tmp/field-profile.json
```

Profiles use CDP sampling at 500 microseconds after ten warmups (one warmup and
one complete invocation for long field). The tool writes `.cpuprofile` files
for DevTools plus a function summary. Add `--source-map /path/to/matching.map`
when the map matches the bundle. Anvil’s production postbuild naming rewrite
does not update its map, so omit that flag for the bundles measured here. The
historical source-mapped profiles use upstream builds without that rewrite.
Add `--trace-v8` with
`DEBUG=pw:browser` to capture optimisation/deoptimisation logs. Profiles locate
work; compare unprofiled timings to establish gains. Inlining and changed total
work make differences in self-sample shares unsuitable as saved-time estimates.

```sh
npm test
node test/runtime_iteration.mjs
node test/compiler_literal_optimization.mjs
```

## Evidence and CPython references

`results.json` is the compact final review table with paired per-round medians,
engine/library hashes, test counts and base/head provenance. `evidence.json.gz`
preserves full raw comparison reports, profile summaries, rejected experiments
and the contemporaneous investigation notes. Historical reports describe their
own bundle pairs; their figures must not be presented as final Anvil-base
results. Raw `.cpuprofile` files can be regenerated with the command above.

Extract a full report without unpacking the entire archive into the repository:

```sh
python3 - <<'PY'
import gzip, json
from pathlib import Path
with gzip.open('support/benchmarks/evidence.json.gz', 'rt') as source:
    evidence = json.load(source)
report = evidence['reports']['anvil-master-chromium.json']
Path('/tmp/anvil-master-chromium.json').write_text(json.dumps(report, indent=2))
print(sorted(evidence['reports']))
PY
```

Useful historical reports: `field-next-cumulative-chromium.json` (earlier
upstream cumulative field comparison), `field-long-chromium.json`,
`lookup-chromium.json`, `collections-chromium.json`,
`iteration-slices-chromium.json` and `slices-keywords-chromium.json`.
Profiles beside those reports identify chain/callback, slice traversal and
keyword unpacking costs. Broader shared numeric dispatch, integer subtraction
and float-variable dispatch experiments were rejected when field or controls
failed to improve; those experiments are absent from the implementation commits.

The reference checkout is CPython commit
[`18ef0f0c`](https://github.com/python/cpython/tree/18ef0f0cb5278fa6583b753ffaaef7f46e416ab9).
These are adaptations of existing techniques, not a claim that they originated
in Python 3.14 or a port of CPython's adaptive inline-cache machinery:

- [Constant iterable pooling](https://github.com/python/cpython/blob/18ef0f0cb5278fa6583b753ffaaef7f46e416ab9/Python/flowgraph.c#L1621).
- [Exact numeric specialisation](https://github.com/python/cpython/blob/18ef0f0cb5278fa6583b753ffaaef7f46e416ab9/Python/bytecodes.c#L640),
  [method calls without bound objects](https://github.com/python/cpython/blob/18ef0f0cb5278fa6583b753ffaaef7f46e416ab9/Python/bytecodes.c#L3616)
  and [global loads](https://github.com/python/cpython/blob/18ef0f0cb5278fa6583b753ffaaef7f46e416ab9/Python/bytecodes.c#L1805).
- [Integer sum accumulator](https://github.com/python/cpython/blob/18ef0f0cb5278fa6583b753ffaaef7f46e416ab9/Python/bltinmodule.c#L2836)
  and [arithmetic range queries](https://github.com/python/cpython/blob/18ef0f0cb5278fa6583b753ffaaef7f46e416ab9/Objects/rangeobject.c#L444).
- [Slice conversion before bounds adjustment](https://github.com/python/cpython/blob/18ef0f0cb5278fa6583b753ffaaef7f46e416ab9/Objects/listobject.c#L3629)
  and [unit-stride copying](https://github.com/python/cpython/blob/18ef0f0cb5278fa6583b753ffaaef7f46e416ab9/Objects/listobject.c#L3610).

The generic paths keep existing Skulpt limitations. In particular, this PR does
not change suspended augmented-assignment compilation or make reentrant
extended-slice assignment match CPython when source iteration clears the target.
The new mutation fix concerns slice reads.
