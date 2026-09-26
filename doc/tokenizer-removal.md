> Historical measurements for the compatibility checkpoint. See
> [parser-rollout.md](parser-rollout.md) for the current bundled parser.

# Removing the old tokenizer from the replacement build

The replacement build now runs without `src/tokenize.js`. Python `tokenize` uses
the shared parser lexer through the opt-in wrapper. The default distribution
continues to include the old frontend and tokenizer.

Identifier recognition has moved to `src/identifier.js`, shared by the old
scanner and `Sk.token.isIdentifier`. This preserves the string runtime's existing
behavior. The replacement preparation script removes both old configuration
hooks and the unreachable legacy Python tokenize wrapper. It requires
`sourceTokenizer` when importing that module.

## Size

The two candidate builds use source commit
`876d7f798c9393481d41d13e4fa30ba259b8d479`, the preparation script in this PR,
and the production Webpack/Closure build on Node 26.7.0. Both omit the old parser
and AST builder; only the second also omits the tokenizer and its legacy wrapper.
The lean parser is unchanged at `67428dc`. Compression uses Node zlib defaults;
totals sum separately compressed artifacts. [Raw data and hashes](benchmarks/tokenizer-removal.json)
identify the measured files. Build metadata may affect later reproductions.

| Artifact | Raw bytes | Gzip bytes | Brotli bytes |
| --- | ---: | ---: | ---: |
| Runtime retaining old tokenizer | 562,560 | 148,021 | 119,920 |
| Runtime without old tokenizer | 557,743 | 146,087 | 118,366 |
| Stdlib retaining legacy wrapper | 497,398 | 125,504 | 106,611 |
| Stdlib without legacy wrapper | 496,816 | 125,396 | 106,511 |
| Separate lean parser | 230,871 | 37,118 | 28,333 |

Removing the tokenizer saves 1,934 gzip bytes in the runtime, plus 108 in the
standard library: **2,042 bytes total**. Runtime plus parser is 183,205 gzip bytes.
Including the standard library brings the replacement to **308,601 bytes**,
versus 310,643 with the old tokenizer retained.

The original pinned runtime plus stdlib was 287,135 gzip bytes. The complete
replacement remains **21,466 bytes larger, about 7.5%**. Compared with the earlier
replacement study before adding the modern tokenize wrapper, the total is nearly
unchanged: 308,561 then versus 308,601 now. The public API improvement consumes
roughly the space reclaimed by removing the old scanner.

The old Unicode tables remain because string operations still use them. This
change does not claim a broad Unicode cleanup, a timing improvement, or a memory
improvement. Sizes exclude Anvil application code and the optional Unicode-name
database.

## Compatibility checks

The final production artifact passed all 2,901 Python 3 execution tests with the
lean parser and all 465 Python 2 tests with the optional Unicode-name resolver.
The latter is necessary for a named escape in an existing test module, so it is
not a claim that the whole Python 2 suite passes without the database.

The real Python tokenize wrapper passed seven comparisons against CPython 3.14.3
and two Skulpt-specific compatibility checks. The replacement checker verifies
that `Sk._tokenize` is absent, the identifier helper remains, configuration works,
and standard-library loading plus eval/exec match CPython in two execution cases.

Nineteen Python `str.isidentifier()` cases match the original runtime exactly.
One probed case already differs from CPython: Skulpt accepts `a²`, while CPython
rejects it. The legacy helper normalizes before matching; this extraction preserves
that behavior. Correcting identifier semantics and consolidating Unicode data
are separate work. The comparison script reports existing differences rather
than treating the legacy behavior as CPython conformance.

The default build also passed the existing four token module tests after helper
extraction. This study does not retire public Skulpt parser/tokenizer APIs from
the default distribution or establish compatibility with deployed Anvil apps.

## Reproduction

Prepare fresh worktrees using an existing Skulpt dependency installation:

```sh
node support/run/prepare-replacement-build.mjs /tmp/tokenizer-retained /path/to/skulpt/node_modules 876d7f798c9393481d41d13e4fa30ba259b8d479
node support/run/prepare-replacement-build.mjs /tmp/tokenizer-removed /path/to/skulpt/node_modules 876d7f798c9393481d41d13e4fa30ba259b8d479 --without-tokenizer
```

In each generated worktree, run:

```sh
NODE_OPTIONS=--openssl-legacy-provider npm run build
```

From this checkout, use the final test helpers:

```sh
node support/run/check-replacement-build.mjs /tmp/tokenizer-removed/dist/skulpt.min.js /path/to/parser/dist-core/index.js --without-tokenizer
node test/tokenize_wrapper.mjs /path/to/parser/dist-core/index.js /tmp/tokenizer-removed/dist/skulpt.min.js
node test/identifier_compat.mjs /path/to/baseline/dist/skulpt.min.js /tmp/tokenizer-removed/dist/skulpt.min.js /path/to/parser/dist-core/index.js
```

The identifier runner loads each bundle's adjacent stdlib. Its baseline should be
`86a1844a5b6016faf9dd535ed3e57d6321d1f25c`. Set `PYTHON314` to override the default
`python3.14` executable; these checks require version 3.14.3.

In the removed-tokenizer worktree, run the execution suites:

```sh
node test/testunit.js --python3 --source-parser /path/to/parser/dist-core/index.js
node test/testunit.js --source-parser /path/to/parser-with-names-and-scan.mjs
```

The optional names wrapper must export both callbacks:

```js
import {parseModule as core} from '/path/to/parser/dist-core/index.js';
import {unicodeName} from '/path/to/parser/dist-core/unicode-names.js';
export {scan} from '/path/to/parser/dist-core/index.js';
export const parseModule = (source, options) => core(source, {...options, unicodeName});
```

Next, validate a concrete Anvil runtime artifact and its application consumers.
The tokenizer-removal experiment has reached its compatibility/size checkpoint;
more synthetic lexer experiments are not required before that integration.
