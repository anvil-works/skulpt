# Experimental structural parser adapter

This branch can feed the Python 3.14 structural AST from `skulpt-parser/core` into
the existing Skulpt symbol table and compiler. It is opt-in. The old frontend
remains the default and remains available for comparison.

The adapter is temporary. The intended longer-term compiler should consume the
CPython-shaped AST directly. This step establishes execution tests and a working
boundary before that rewrite; it does not claim Python 3.14 runtime semantics.

## Enabling it

Load the parser before compiling Python, then pass its synchronous module parser:

```js
import { parseModule } from "skulpt-parser/core";

Sk.configure({ sourceParser: parseModule });
// Restore the old frontend:
Sk.configure({ sourceParser: null });
```

Omitting `sourceParser` in later configuration calls preserves the selection.
The parser must include the `printFunction` option added for this integration.
The parser package is supplied by the host; this branch does not vendor a bundle,
add an unpublished registry dependency, or change consumer packaging.

`Sk.compile`, imports, `exec`, and the preliminary parse in `eval` use the selected
frontend. Existing public `Sk.parse`, CST and tokenization APIs remain unchanged.
Future settings are restored even when parsing, adaptation or compilation fails.

The adapter converts structural nodes, identifiers, literal values, subscripts and
exception aliases to the existing runtime representation. It retains standalone
`debugger` statements. Duplicate keyword validation remains at the compilation
boundary. Unsupported node kinds, type parameters and positional-only parameters
raise explicit Python syntax errors before reaching old constructor dispatch.
Nonlocal statements use the implementation already present on the base branch.

## Python 2 compatibility boundary

Compatibility mode protects existing Python 2 applications. It is not an attempt
to enforce all historical Python 2 syntax restrictions. Modern syntax may work
when the existing compiler and runtime can implement it. A regression test checks
annotated assignment in this mode against CPython's result, even though the old
frontend rejected it solely on the language-version flag.

The adapter selects `python2Compat` from the runtime mode, keeps async/await as
ordinary names in both modes, and passes configured `print_function` separately.
Legacy octal/long literals, print statements, raise forms and exception targets
retain their dedicated conversions. No rejection is added solely because a
construct was absent in Python 2.

## Validation

From this worktree, build Skulpt and provide the built lean parser explicitly:

```sh
NODE_OPTIONS=--openssl-legacy-provider npm run devbuild
PYTHON314=python3.14 node test/structural_parser.mjs /path/to/parser/dist-core/index.js
node test/testunit.js --python3 --module nonlocal --source-parser /path/to/parser/dist-core/index.js
```

The execution/error runner requires CPython 3.14.3 and performs 40 comparisons:
ordinary outputs against both CPython and the existing Skulpt frontend; legacy
behavior against existing Skulpt; newer spelling against CPython; suspension;
compiler rejection; diagnostics; and optional Unicode capability errors. It runs
real generated JavaScript, rather than checking only AST construction. The
relative-import fixture exercises package loading through the selected parser.

For optimized-build verification:

```sh
NODE_OPTIONS=--openssl-legacy-provider npm run build
PYTHON314=python3.14 node test/structural_parser.mjs /path/to/parser/dist-core/index.js dist/skulpt.min.js
```

Existing regression modules checked through both frontends are `skulpt_bugs`,
`nonlocal`, `scope`, `call`, `calling`, and `bytes` in Python 3 mode, plus `calling`
and `exceptions` in Python 2 mode: 137 tests per frontend. These focused checks do
not establish compatibility with deployed apps. The subsequent full-suite
comparison and performance results are in [the adapter measurements](structural-parser-measurements.md).

## Remaining rollout work

- Measure combined source-to-AST and compilation cost. Conversion allocates a
  second tree. No end-to-end speed or memory improvement is claimed yet.
- Expand execution coverage before changing defaults. New grammar coverage alone
  does not implement new scoping, annotation, coroutine or other runtime semantics.
- Keep the Unicode-name database optional. The host may supply a parser function
  bound to a resolver, but synchronous compilation does not fetch it automatically.
  Missing database errors remain capability errors, not Python syntax errors.
- Audit normalized Unicode names across host globals and mixed old/new modules.
- Keep packaging, frontend retirement and the direct-AST compiler rewrite separate
  from this opt-in checkpoint.

## Opt-in Python tokenization wrapper

Configure both callbacks before importing Python `token` or `tokenize`:

```js
import {parseModule, scan} from "skulpt-parser/core";
Sk.configure({sourceParser: parseModule, sourceTokenizer: scan});
```

`sourceTokenizer` is independent of `sourceParser` and defaults to `null`, retaining
Skulpt's existing module. Modules are cached after import, so change this option
between interpreter sessions, not after importing either module in a live session.
The test runner's `--source-parser` option also configures `scan` when the supplied
module exports it.

With the callback configured, `token` exports the CPython 3.14.3 constants and
`EXACT_TOKEN_TYPES`, separately from the old compiler's internal table. `tokenize`
exports `TokenInfo`, `TokenError`, `generate_tokens`, `tokenize`, and the token
module's exports. TokenInfo supports indexed and named fields, `exact_type`,
CPython-style repr, and the named-tuple methods supplied by Skulpt's collections.

`generate_tokens` accepts decoded text. `tokenize` accepts UTF-8 bytes, including
a leading BOM and UTF-8 coding cookies. It also preserves Skulpt's existing text
callback extension, whose initial encoding token is labelled `UTF-8`. Standard
bytes input uses `utf-8`. A callback may terminate with an empty line or
`StopIteration`. Python 2 mode selects the parser's bounded legacy syntax support.

Both calls return iterators. They defer callback reads until iteration, buffer the
source at the first iteration, then produce tokens lazily. Incremental readline
consumption, suspending callbacks, non-UTF-8 codecs, `detect_encoding`, `open`, and
`untokenize` are not implemented. Byte decoding is strict throughout this wrapper;
CPython's native reader can replace invalid bytes after initial encoding checks.
Unsupported encoding declarations fail explicitly instead of silently decoding
with the wrong codec.

Lexer SyntaxError becomes TokenError with a message and position. The public
triple-quoted-string diagnostic follows CPython's `EOF in multi-line string`
compatibility wording. IndentationError and TabError retain their classes and
source information. Reader exceptions propagate unchanged, including reader-raised SyntaxError
that CPython may translate into TokenError. The compiler and IDE parser
diagnostics are unaffected.

Run the live public-module comparisons against pinned CPython 3.14.3:

```sh
node test/tokenize_wrapper.mjs /path/to/parser/dist-core/index.js
node test/testunit.js --module tokenize --source-parser /path/to/parser/dist-core/index.js
node test/testunit.js --module tokenize
```

The wrapper does not yet remove the old tokenizer. Moving its identifier and
configuration helpers, removing it from the replacement artifact, and measuring
the resulting bundle remain the next step described in the
[migration study](cpython-tokenize-research.md).
