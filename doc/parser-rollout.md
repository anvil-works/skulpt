# Direct AST compiler

This branch is stacked above the old-AST compatibility checkpoint, PR #9.
Published parser `0.0.1-dev.7` and its scanner are bundled into Skulpt. Existing hosts keep their normal
`Sk.configure`, compilation and execution calls; no parser configuration or
separate script is needed. The compiler consumes the parser's plain AST directly.
No old-AST adapter or `Sk.parse` / `Sk.astFromParse` API is included in the build.
Consumers of those APIs must move to `Sk.parseModule(source, filename)` and its
modern node shapes and UTF-8 byte columns before deploying this version.
The function returns the module AST directly, uses the Python compatibility mode
from `Sk.configure`, and raises Skulpt syntax errors on invalid source.
AST consumers must convert UTF-8 columns before indexing JavaScript strings.
Traceback `colno`, suspension `$colno` and breakpoint callback columns retain
zero-based UTF-16 offsets. The compiler converts these when emitting locations;
AST nodes remain unchanged. Python syntax-error offsets retain CPython's
one-based Unicode-character convention.

Existing execution suites run through the new parser. CI compares execution with
the parent compatibility checkpoint and CPython 3.14.3. The Python 2 annotation
fixture accepts annotations in compatibility mode instead of requiring rejection.
Unsupported compiler features continue to raise Python syntax errors.

The Anvil rollout and IDE PRs are unchanged. This branch does not authorize
merging or deployment.
