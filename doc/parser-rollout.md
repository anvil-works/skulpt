# Direct AST compiler

This branch is stacked above the old-AST compatibility checkpoint, PR #9.
The compiler and symbol table consume the parser's plain AST directly. Hosts
must configure `sourceParser`; `sourceTokenizer` supplies the tokenizer wrapper. No old-AST adapter or
`Sk.parse` / `Sk.astFromParse` compatibility API is included in the build.
Consumers of those APIs must move to `Sk.parseCompilerModule(...).ast` and its
modern node shapes and UTF-8 byte columns before deploying this version.

Existing execution suites run through the new parser. CI compares execution with
the parent compatibility checkpoint and CPython 3.14.3. The Python 2 annotation
fixture accepts annotations in compatibility mode instead of requiring rejection.
Unsupported compiler features continue to raise Python syntax errors.

The Anvil rollout and IDE PRs are unchanged. This branch does not authorize
merging or deployment.
