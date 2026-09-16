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
