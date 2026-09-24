# Parser rollout review boundaries

The migration has five review boundaries. None authorizes merging or deployment.
Skulpt PRs go to `anvil-works/skulpt`.

| Stage | Repository | Deliverable | Depends on |
| --- | --- | --- | --- |
| 1 | Anvil | Existing IDE-only migration, PR #7444 | Published lean parser |
| 2 | Skulpt | New parser with the old AST adapter and compatibility CI | Parser indentation fix, anvil-works/skulpt-parser#52 |
| 3 | Skulpt | Compiler and symbol table consume modern AST directly; remove adapter | Stage 2 |
| 4 | Anvil | Runner/designer phased rollout of stage 2 | Stage 2 compatibility evidence |
| 5 | Anvil | Separate phased rollout of stage 3 | Stages 3 and 4 |

The IDE migration is ready for independent review, but is not authorized to ship.
Stage 3 must not delay or replace the stage 2 compatibility checkpoint. Its
implementation is not part of this branch.

## Compatibility checkpoint

This branch retains the old compiler AST. The host selects the new parser through
`sourceParser` and `sourceTokenizer`; the existing frontend remains the default.
The published runtime candidate can omit old frontend implementation files using
`support/run/prepare-replacement-build.mjs`. That removes the old parser, not the
AST adapter. Direct modern-AST compilation is a separate change.

The original AST source corpus is `test/run/*.py`. The old `testTransform` job is
disabled by default, and its `.trans` goldens predate today's Skulpt AST schema.
For example, current Module nodes have a docstring field, and the old dumper
throws on its undefined value. Two `.trans` files have no corresponding source.
The goldens are left untouched; passing them is not claimed.

`test/ast_compat.mjs` parses all 564 existing source files through both production
frontend entry points. It compares declared AST fields and Python literal values,
using the current old frontend as the oracle. As with the original dumps, source
locations and prototype identity are outside this comparison. It normalizes only:

- Undefined optional fields to null.
- Comprehension filter lists and synchronous flags, and lambda argument lists,
  where the old builder inconsistently uses missing values instead of empty lists
  or zero.
- An explicit None slice step versus an absent step.
- An ExtSlice of only Index nodes versus an Index containing a tuple.

It does not normalize arbitrary arrays or node kinds. In particular, null and an
empty array remain different for Try.finalbody. Call argument and empty dictionary
sentinels now match the old builder directly in the adapter.

The corpus has one existing policy extension, `t905.py`: the old frontend rejects
annotated assignment solely because Python 2 mode is active. The test asserts that
old rejection and verifies that the candidate parses and compiles the source.
No fixture is silently skipped. The other 563 sources must match.

The parser indentation prerequisite restores the old frontend's eight-column tab
behavior in Python 2 compatibility mode. The unchanged sources `t530.py` and
`t543.py` exercise that regression. Strict Python 3 indentation remains unchanged.

The `parser-compatibility` workflow has separate AST and execution jobs. The latter
runs the optimized runtime's existing suites under both frontends, CPython-backed
execution comparisons, tokenizer module tests and identifier checks. Full Python 2
execution tests explicitly load the optional Unicode-name resolver because an
existing integer fixture needs it. That is not evidence of lean-only Unicode-name
support, and the runtime candidate still uses lean core.

The workflow pins parser source at an immutable revision pending publication of
the indentation fix. Stage 4 must pin the resulting reviewed parser artifact;
it must not silently use the older published version without this fix.

## Deployment contract for the Anvil stages

Ship two separately named asset sets in one deployment, including matching stdlib
chunks and source maps. Each page loads only its selected set. Runner, preview and
designer use the same selection for an app. Autocomplete is independent.

Select from the server-owned asset sets using the first four hexadecimal digits
of SHA-256 of the canonical app ID and a percentage threshold. Default to zero
candidate traffic. Global rollback wins over per-app overrides, which win over the
percentage. Missing identity/configuration selects the current runtime. Preserve
normal cache versioning and record selected runtime revision in diagnostics.

Stage 4 keeps the current deployed runtime as rollback. Stage 5 keeps the tested
adapter runtime as rollback. Rollback takes effect on page reload; never retry
application execution automatically under another runtime. Standalone/enterprise
installations remain on current unless explicitly configured.

After separate approval, advance manually through internal apps, 1%, 5%, 25%, 50%
and 100%, reviewing errors and startup/compile performance between steps. Keep both
asset sets until the observation period is complete. No rollout starts merely
because implementation or CI is complete.
