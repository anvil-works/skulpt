# Replacing the old compiler frontend

Removing the old parser and AST builder works in the execution suites, but the
replacement still costs 21,426 additional gzip bytes versus the pinned baseline.
This experiment leaves the production entry point and configuration unchanged.
It supports investigating a runtime-only artifact, not silently replacing the
existing distribution.

## Size

These are production Webpack/Closure builds on Node 26.7.0. Baseline commit is
`86a1844a5b6016faf9dd535ed3e57d6321d1f25c`. The candidate uses
`abc3fa1d7cf618bc5205f6df6263337ff0c1da95` plus the edits made by the preparation
script. The lean parser comes from anvil-works/skulpt-parser at `67428dc`.
[Raw measurements and artifact hashes](benchmarks/replacement-build.json) identify
the exact artifacts. Build metadata can change hashes and sizes on rebuild.

| Artifact | Raw bytes | Gzip bytes | Brotli bytes |
| --- | ---: | ---: | ---: |
| Baseline runtime | 620,275 | 163,661 | 132,942 |
| Runtime retaining both frontends | 626,216 | 165,356 | 134,373 |
| Runtime without old parser/AST builder | 562,390 | 147,969 | 119,875 |
| Separate lean parser | 230,871 | 37,118 | 28,333 |
| Replacement runtime plus lean parser | 793,261 | 185,087 | 148,208 |
| Common standard library | 491,450 | 123,474 | 105,003 |

Totals sum separately compressed artifacts using Node zlib defaults. Removing the old frontend saves
17,387 gzip bytes compared with shipping both frontends and the parser. The net
increase over the old runtime is 13.1%. Including the common standard library,
baseline and replacement are 287,135 and 308,561 gzip bytes respectively, a 7.5%
increase. The two standard-library artifacts are hash-identical.

These figures exclude the application and optional Unicode-name database. They
are not the size of the deployed Anvil client. No new timing or memory results
were collected for this stripped build. The earlier
[speed measurements](structural-parser-measurements.md) used the runtime retaining
both frontends.

## Compatibility boundary

The experiment removes `gen/parse_tables.js`, `src/parser.js`, and `src/ast.js`
from the entry point. It removes the fallback to the old frontend and requires
an injected `sourceParser`. It also removes the configuration call to
`Sk.setupOperators`, which only updates the old AST builder's operator map.

The exported `Sk.parse`, `Sk.Parser`, `Sk.astFromParse`, `Sk.astDump`,
`Sk.parseTreeDump`, `Sk.ParseTables`, `Sk.OpMap`, and `Sk.setupOperators` disappear.
Consumers of those APIs must migrate or keep the existing distribution. The old
CST, AST-dump, and symbol-table inspection tests in `test/test.js` also depend on
those APIs; execution-suite success does not cover those inspection contracts.

The old tokenizer and token constants remain. Python's `tokenize` module calls
`Sk._tokenize`; `token` uses the old token definitions. The tokenizer also retains
its Unicode support dependency. Removing it needs a separate compatibility study.

## Validation

The production replacement bundle passed:

- All 2,901 Python 3 execution tests using the lean parser.
- All 465 Python 2 execution tests with the optional Unicode-name resolver.
- All four token/tokenize tests using the lean parser.
- Checks that the removed APIs are absent, the tokenizer remains, and missing
  `sourceParser` fails explicitly.
- Two execution comparisons against CPython 3.14.3, covering standard-library
  loading through `textwrap`, f-string conversion in `eval`, and `exec` bindings.

The Python 2 suite needs the optional resolver because a triple-quoted string in
its integer test module contains a named Unicode escape. The full Python 2 result
must not be interpreted as a pass with only the lean parser.

## Reproduction

From this checkout, supply an existing installed Skulpt `node_modules` directory
and a fresh destination. The helper creates a detached worktree and applies the
three-file experiment there. It does not modify this checkout's runtime sources.

```sh
node support/run/prepare-replacement-build.mjs /tmp/skulpt-replacement /path/to/skulpt/node_modules abc3fa1d7cf618bc5205f6df6263337ff0c1da95
cd /tmp/skulpt-replacement
NODE_OPTIONS=--openssl-legacy-provider npm run build
node test/testunit.js --python3 --source-parser /path/to/skulpt-parser/dist-core/index.js
node test/testunit.js --source-parser /path/to/parser-with-names.mjs
node test/testunit.js --module tokenize --source-parser /path/to/skulpt-parser/dist-core/index.js
```

The resolver wrapper exports the lean parser with the optional database:

```js
import { parseModule as core } from '/path/to/skulpt-parser/dist-core/index.js';
import { unicodeName } from '/path/to/skulpt-parser/dist-core/unicode-names.js';
export const parseModule = (source, options) => core(source, { ...options, unicodeName });
```

Back in this checkout, run the boundary and CPython checks. Set `PYTHON314` if
CPython 3.14.3 is not installed as `python3.14`.

```sh
node support/run/check-replacement-build.mjs /tmp/skulpt-replacement/dist/skulpt.min.js /path/to/skulpt-parser/dist-core/index.js
```

## Next decision

Choose whether Anvil should consume a dedicated runtime-only artifact with these
API omissions. Then validate its real runtime integration and representative
application workloads. Keep the existing default distribution until that decision
and consumer validation are complete.
