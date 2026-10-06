# JavaScript compiler roadmap to Python 3.14

This audit concerns the existing JavaScript compiler above `stu-dev/parser/direct-ast`, with the generator fix stack integrated above it. The bytecode experiment is parked. The target is Python 3.14 language behavior, not CPython bytecode, native extensions, or complete standard-library compatibility.

## Current scope

The active stack uses published `@anvil-works/skulpt-parser@0.0.1-dev.8` and the existing JavaScript compiler. Python async execution is parked on a separate sibling stack; Anvil host suspensions remain supported. Generator metadata, delegation temporaries and symbol-table flags are shared synchronous prerequisites rather than a reason to depend on the coroutine stack. Modern Python reserves `async` and `await` even when execution of their AST nodes is unsupported.

Reference checkout: `/Users/scork/Desktop/Projects/cpython` (the project sibling `../cpython`), branch `3.14`, commit `18ef0f0cb5278fa6583b753ffaaef7f46e416ab9` (2026-10-06). All CPython links below pin that commit. The version history is a discovery checklist; the current grammar, compiler, symbol table and tests define the target behavior. This is a **source audit**, not a completed conformance run. “Implemented path” does not mean every edge case passes; suspected discrepancies need a failing CPython-derived test before a fix.

The production stack passes `npm test`: 562 execution cases (2 existing disabled cases), 465 Python 2 tests, 2,984 Python 3 tests, and the generator/suspension JavaScript guards. Another 48 parser execution/error comparisons pass against the compatibility checkpoint and CPython 3.14.3. These are regression baselines, not counts of complete Python 3.14 conformance cases.

Completed layers:

| Branch | Change and upstream evidence |
| --- | --- |
| `stu-dev/compiler/class-cells` → `suspension-cleanup` → `exception-context` → `generator-suspensions` | Existing four-part generator dependency stack ported above the plain AST compiler. Conflicts adapted to modern identifiers and context nodes; original fix branches preserved. |
| `stu-dev/compiler/generator-314` | Initial `throw(StopIteration)` propagates the supplied exception before the body starts; `close()` returns the generator's return value once; `gi_yieldfrom` is hidden during execution. Seven unchanged `GeneratorCloseTest` methods plus the current delegated-close method were copied from CPython. Weakref/GC facilities remain outside this port. |
| `stu-dev/compiler/positional-only` | Symbol-table parameter order, emitted counts, keyword binding and diagnostics follow CPython. Eighteen unchanged `PositionalOnlyTestCase` methods pass, including defaults, invalid calls, closures, methods, generators and `super()`. Introspection, async and serialization remain separate coverage. |
| `stu-dev/compiler/dict-comprehension-order` | Dictionary keys are evaluated and saved before values. CPython's unchanged `test_evaluation_order` fails before the fix and passes afterward. |

The generator, delegation, positional-only and dictionary-comprehension modules also pass under CPython 3.14.3 (86 tests total). Existing deliberately broken delegated-close fixtures print an unraisable exception in CPython; the unittest run succeeds. Existing compiler/symtable lint findings remain (50 versus 53 on the direct-AST base); modified function/generator files pass ESLint. No unrelated lint cleanup was included.

## Implementation correspondence

Where the behavior maps directly, keep Skulpt recognizable as a JavaScript implementation of CPython's compiler: visit the same AST fields in the same semantic order, carry explicit scope/code-unit metadata, and preserve CPython's validation and binding phases. Cite the corresponding source function for changes. JavaScript block dispatch and host suspensions still require different emission mechanics.

| Skulpt seam | CPython reference |
| --- | --- |
| `SymbolTable.visitArguments`, scope analysis | `Python/symtable.c`: `symtable_visit_arguments` and block analysis |
| `Compiler.buildcodeobj` parameter metadata | `Python/codegen.c`: function/lambda scope metadata; `Python/assemble.c` code-object counts |
| `$resolveArgs` | `Python/ceval.c`: `initialize_locals`, `positional_only_passed_as_keyword`, `too_many_positional`, `format_missing` |
| `Compiler.ccompgen` | `Python/codegen.c`: `codegen_sync_comprehension_generator` (key before value) |
| Generator resume/throw/close | `Objects/genobject.c`: `gen_send_ex2`, `_gen_throw`, `gen_close`, `_PyGen_yf` |


## Existing foundation

The production path is modern parser AST → `Sk.symboltable` → generated JavaScript. [Parser boundary](../src/structural_ast.js), [compiler](../src/compile.js), [symbol table](../src/symtable.js), and [parser integration notes](parser-rollout.md).

Implemented paths include ordinary functions/lambdas, defaults and keyword-only parameters, classes/decorators, `global`/`nonlocal`, closures, ordinary exception handling and context managers, comprehensions, generators/`yield from`, f-strings, starred containers/calls/assignment, and annotated assignments/functions. Existing execution tests remain the regression baseline; these paths need targeted modern CPython cases rather than a blanket “supported through version X” label. See `visitStmt`/`visitExpr` in the [symbol table](../src/symtable.js) and `vstmt`/`vexpr` in the [compiler](../src/compile.js).

Unsupported AST statements/expressions fail explicitly in symbol-table traversal. The parser can accept syntax whose AST the compiler rejects. Its configuration reserves `async`/`await` in Python 3 and selects Python 2 versus 3, rather than individual Python 3 minor versions; any version-gating contract needs a separate decision and tests. [Parser options](../src/structural_ast.js).

## Inventory and order

| Area | Evidence in this checkout | Next step / dependencies |
| --- | --- | --- |
| Positional-only arguments, Python 3.8 / PEP 570 | Implemented in `stu-dev/compiler/positional-only`; eighteen unchanged CPython execution methods pass. Metadata and keyword matching distinguish positional-only parameters. [symtable](../src/symtable.js), [function binding](../src/function.js). | Selected execution contract covered; async, serialization, parser syntax cases and `__code__` introspection still need their own coverage. [CPython tests](https://github.com/python/cpython/blob/18ef0f0cb5278fa6583b753ffaaef7f46e416ab9/Lib/test/test_positional_only_arg.py). |
| Dictionary-comprehension evaluation order, Python 3.8 / PEP 572 | Fixed in `stu-dev/compiler/dict-comprehension-order`: `ccompgen` emits and saves the key before evaluating the value; the unchanged CPython test passes. [compiler](../src/compile.js), [CPython `test_evaluation_order`](https://github.com/python/cpython/blob/18ef0f0cb5278fa6583b753ffaaef7f46e416ab9/Lib/test/test_dictcomps.py#L87). | Selected synchronous side-effect test covered; scope isolation remains separate. Saving the key also preserves it across value evaluation and suspension. |
| Comprehension isolation and closures; Python 3.12 / PEP 709 visible semantics | List/set/dict comprehension visitors do not enter a symbol-table block. `ccompgen` writes targets through ordinary `vexpr`; generator expressions use their own block. These are strong indications of isolation/closure gaps, not proof that every test fails. [symtable](../src/symtable.js), [compiler](../src/compile.js). | Baseline no-leakage, iterable evaluation scope, class scope, nested comprehensions and captured iteration variables. Keep inlining if practical; CPython 3.12 inlines while preserving isolation. Avoid fixing only the final variable value: closures can escape, and failures must restore surrounding bindings. [3.12 changes](https://github.com/python/cpython/blob/18ef0f0cb5278fa6583b753ffaaef7f46e416ab9/Doc/whatsnew/3.12.rst#L398), [CPython tests](https://github.com/python/cpython/blob/18ef0f0cb5278fa6583b753ffaaef7f46e416ab9/Lib/test/test_listcomps.py). |
| Assignment expressions, Python 3.8 / PEP 572 (`NamedExpr`) | No expression visitor/emitter; symbol table rejects the node. [symtable](../src/symtable.js), [compiler](../src/compile.js). | Ordinary expression assignment is small; complete support includes nonlocal/global binding from comprehensions and special syntax restrictions. Build on the comprehension scope work instead of accepting walrus syntax with incorrect scope. [CPython named-expression scope implementation](https://github.com/python/cpython/blob/18ef0f0cb5278fa6583b753ffaaef7f46e416ab9/Python/symtable.c#L2309), [tests](https://github.com/python/cpython/blob/18ef0f0cb5278fa6583b753ffaaef7f46e416ab9/Lib/test/test_named_expressions.py). |
| Async functions, `await`, async `for`/`with`, async comprehensions and async generators (Python 3.5–3.11) | `AsyncFunctionDef`, `AsyncFor`, `AsyncWith`, `Await` have no active symtable/compiler cases; async comprehensions have an explicit guard. The `AsyncFunctionDef` mention in code-object construction is not execution support. [symtable](../src/symtable.js), [compiler](../src/compile.js). | Substantial runtime project after generator stability: Python coroutine/awaitable and async-iterator protocols, cancellation/close/throw and finalization. A Skulpt host suspension is not by itself a Python coroutine. Start with protocol tests that do not require `asyncio`. [coroutine tests](https://github.com/python/cpython/blob/18ef0f0cb5278fa6583b753ffaaef7f46e416ab9/Lib/test/test_coroutines.py), [async-generator tests](https://github.com/python/cpython/blob/18ef0f0cb5278fa6583b753ffaaef7f46e416ab9/Lib/test/test_asyncgen.py). |
| Structural pattern matching, Python 3.10 / PEP 634 (`Match`) | No statement visitor/emitter; rejected. [symtable](../src/symtable.js), [compiler](../src/compile.js). | Add pattern binding validation and ordered pattern/guard execution. Sequence/mapping/class protocols and binding visibility are part of the feature; do not lower patterns to equality tests alone. [CPython lowering](https://github.com/python/cpython/blob/18ef0f0cb5278fa6583b753ffaaef7f46e416ab9/Python/codegen.c#L6394), [tests](https://github.com/python/cpython/blob/18ef0f0cb5278fa6583b753ffaaef7f46e416ab9/Lib/test/test_patma.py). |
| Exception groups and `except*`, Python 3.11 / PEP 654 (`TryStar`) | No statement visitor/emitter. No exception-group class definitions in [errors](../src/errors.js). | Requires runtime grouping, splitting, subgroup identity/metadata, and combining reraised/new exceptions; ordinary `except` machinery is insufficient. Follow generator exception-context integration. [CPython lowering](https://github.com/python/cpython/blob/18ef0f0cb5278fa6583b753ffaaef7f46e416ab9/Python/codegen.c#L2613), [tests](https://github.com/python/cpython/blob/18ef0f0cb5278fa6583b753ffaaef7f46e416ab9/Lib/test/test_except_star.py). |
| Type parameters and `type` statements, Python 3.12 / PEP 695; defaults, Python 3.13 / PEP 696 | Nonempty function/class `type_params` explicitly rejected; no `TypeAlias` case. [symtable](../src/symtable.js). | Annotation scopes and lazy bounds/alias values plus runtime type-parameter/alias objects. Include name collisions, class visibility and nonlocal restrictions; erasing the syntax would lose runtime behavior. [3.12 changes](https://github.com/python/cpython/blob/18ef0f0cb5278fa6583b753ffaaef7f46e416ab9/Doc/whatsnew/3.12.rst#L180), [type-parameter tests](https://github.com/python/cpython/blob/18ef0f0cb5278fa6583b753ffaaef7f46e416ab9/Lib/test/test_type_params.py), [type-alias tests](https://github.com/python/cpython/blob/18ef0f0cb5278fa6583b753ffaaef7f46e416ab9/Lib/test/test_type_aliases.py). |
| Deferred annotations, Python 3.14 / PEP 649 and 749 | `cargannotation` evaluates expressions during definition; `cannassign` evaluates simple module/class annotations eagerly. `func_annotations` stores evaluated results, with no `__annotate__` mechanism. [compiler](../src/compile.js), [function](../src/function.js). | Clear architectural mismatch. Share annotation-scope work with PEP 695, but implement actual delayed evaluation, class/module/function lookup, conditional execution and introspection. `from __future__ import annotations` has its own stringized contract: no annotation future mode is visible in the parser/compiler boundary, and [the module is a stub](../src/lib/__future__.py). [3.14 changes](https://github.com/python/cpython/blob/18ef0f0cb5278fa6583b753ffaaef7f46e416ab9/Doc/whatsnew/3.14.rst#L148), [tests](https://github.com/python/cpython/blob/18ef0f0cb5278fa6583b753ffaaef7f46e416ab9/Lib/test/test_type_annotations.py). |
| Template strings, Python 3.14 / PEP 750 (`TemplateStr`, `Interpolation`) | No expression visitors/emitters. [symtable](../src/symtable.js), [compiler](../src/compile.js). | Parser/tokenizer acceptance must be checked; codegen must construct `Template`/`Interpolation` objects and retain expression text rather than eagerly formatting a string. Requires `string.templatelib` runtime support. [3.14 changes](https://github.com/python/cpython/blob/18ef0f0cb5278fa6583b753ffaaef7f46e416ab9/Doc/whatsnew/3.14.rst#L299), [tests](https://github.com/python/cpython/blob/18ef0f0cb5278fa6583b753ffaaef7f46e416ab9/Lib/test/test_tstring.py). |
| `locals()`, default `exec`/`eval` namespaces; Python 3.13 / PEP 667 | `Sk.builtin.locals` explicitly raises `NotImplementedError`. Compiler uses JavaScript locals/cells, so the feature crosses the compiler/runtime boundary. [builtin](../src/builtin.js), [compiler](../src/compile.js). | Independent snapshots for optimized scopes, shared mappings for module/class scopes, closure variables and execution namespace behavior. Required for the visible PEP 709 comprehension `locals()` changes; defer frame/profiling details separately. [3.13 changes](https://github.com/python/cpython/blob/18ef0f0cb5278fa6583b753ffaaef7f46e416ab9/Doc/whatsnew/3.13.rst#L420). |

## Smaller syntax and API checks still needing probes

These often arrive as familiar AST nodes, so missing new node names are not a sufficient audit.

| Change | Evidence and CPython source |
| --- | --- |
| Unparenthesized starred `return`/`yield` (3.8), starred iterable in `for` (3.11), starred subscripts (3.11 / PEP 646) | Existing tuple/starred/container paths could cover these, but actual parser AST and execution must be checked. These are **not new Python 3.14 features**. [3.8 history](https://github.com/python/cpython/blob/18ef0f0cb5278fa6583b753ffaaef7f46e416ab9/Doc/whatsnew/3.8.rst#L426), [3.11 history](https://github.com/python/cpython/blob/18ef0f0cb5278fa6583b753ffaaef7f46e416ab9/Doc/whatsnew/3.11.rst#L439), [grammar tests](https://github.com/python/cpython/blob/18ef0f0cb5278fa6583b753ffaaef7f46e416ab9/Lib/test/test_grammar.py#L862), [PEP 646 tests](https://github.com/python/cpython/blob/18ef0f0cb5278fa6583b753ffaaef7f46e416ab9/Lib/test/test_pep646_syntax.py). |
| Arbitrary decorator expressions (3.9 / PEP 614), parenthesized multiple context managers (3.10), modern f-string grammar (3.12 / PEP 701) | Existing emission evaluates expressions/decorators and `JoinedStr`/`FormattedValue`; parser acceptance and evaluation order remain unverified. [3.9 history](https://github.com/python/cpython/blob/18ef0f0cb5278fa6583b753ffaaef7f46e416ab9/Doc/whatsnew/3.9.rst#L246), [3.10 history](https://github.com/python/cpython/blob/18ef0f0cb5278fa6583b753ffaaef7f46e416ab9/Doc/whatsnew/3.10.rst#L99), [3.12 history](https://github.com/python/cpython/blob/18ef0f0cb5278fa6583b753ffaaef7f46e416ab9/Doc/whatsnew/3.12.rst#L244), [f-string tests](https://github.com/python/cpython/blob/18ef0f0cb5278fa6583b753ffaaef7f46e416ab9/Lib/test/test_fstring.py). |
| Unparenthesized exception-type lists (3.14 / PEP 758) | Ordinary `except A, B:` becomes an ordinary tuple handler in CPython; compiler `Try` support may suffice once parser acceptance is verified. `except*` still needs its own implementation. `as` imposes grammar restrictions. [grammar](https://github.com/python/cpython/blob/18ef0f0cb5278fa6583b753ffaaef7f46e416ab9/Grammar/python.gram#L446), [grammar `test_try` / `test_try_star`](https://github.com/python/cpython/blob/18ef0f0cb5278fa6583b753ffaaef7f46e416ab9/Lib/test/test_grammar.py#L1394). |
| Compiler warnings for exiting `finally` (3.14 / PEP 765) | Existing control-flow lowering handles `finally`, but no syntax-warning emission was found in the compiler. Add a warning delivery policy and targeted detection; warning semantics should not change execution behavior. [3.14 history](https://github.com/python/cpython/blob/18ef0f0cb5278fa6583b753ffaaef7f46e416ab9/Doc/whatsnew/3.14.rst#L932), [syntax tests](https://github.com/python/cpython/blob/18ef0f0cb5278fa6583b753ffaaef7f46e416ab9/Lib/test/test_syntax.py#L2705). |
| Syntax checks in optimized/dead code, including writes to `__debug__` | `nameop` rejects writes during emission, so skipped code paths need specific tests. CPython 3.14 detects more errors before optimization. [compiler](../src/compile.js), [3.14 changes](https://github.com/python/cpython/blob/18ef0f0cb5278fa6583b753ffaaef7f46e416ab9/Doc/whatsnew/3.14.rst#L827). |
| Public `compile()` contract and code introspection | `Sk.builtin.compile` takes `flags`, `dont_inherit`, `optimize` but forwards only source/filename/mode. The JS compiler currently uses module AST parsing. Audit `exec`/`eval`/`single` modes, accepted source types, flag validation, future inheritance and code metadata separately; do not claim CPython `CodeType` compatibility. [builtin](../src/builtin.js), [compiler](../src/compile.js), [CPython compile tests](https://github.com/python/cpython/blob/18ef0f0cb5278fa6583b753ffaaef7f46e416ab9/Lib/test/test_compile.py). |

Dictionary union (PEP 584) and generic aliases (PEP 585) already have runtime implementation paths in [dict](../src/dict.js), [generic aliases](../src/generic_alias.js) and [subscript dispatch](../src/abstract.js). Conversely, `int | str` uses the existing binary-operator compiler path but needs type-union runtime behavior (PEP 604); no `nb$or` implementation was found on [type](../src/type.js). Classify these as runtime compatibility checks rather than adding duplicate compiler AST support. Typing-library additions and standard-library APIs need a separate inventory.

## CPython-derived first increments

Use the actual method bodies and assertions from the pinned checkout. Record the upstream file, class, method, commit and any adaptation in each port. These selections avoid most CPython-only harness machinery.

1. **Dictionary-comprehension order:** `Lib/test/test_dictcomps.py`, `DictComprehensionTest.test_evaluation_order`. Its `add_call` helper observes order directly and needs only ordinary `unittest`, `zip`, lists and dicts. Preserve both result and call-order assertions. This is a small, high-confidence compiler fix candidate.
2. **Positional-only arguments:** `Lib/test/test_positional_only_arg.py`, `PositionalOnlyTestCase.test_optional_positional_only_args`, `test_pos_only_call_via_unpacking`, `test_use_positional_as_keyword`, `test_same_keyword_as_positional_with_kwargs`, `test_lambdas`, `test_mangling`, `test_generator`. Keep expected error text where the selected method asserts it. Do not silently remove `__code__` assertions from `test_pos_only_definition`; record it as a separate introspection requirement if the code-object API cannot support it.
3. **Comprehension baseline:** `Lib/test/test_dictcomps.py`, `DictComprehensionTest.test_scope_isolation`, `test_scope_isolation_from_global`; `Lib/test/test_listcomps.py`, `ListComprehensionTest.test_lambdas_with_free_var`, `test_lambdas_with_iteration_var_as_default`, `test_shadow_comp_iterable_name`, `test_unbound_local_after_comprehension`, `test_in_class_scope_inside_function_1`, `test_nested_free_var_in_iter`. Include zero-iteration and exceptional cleanup cases from the same upstream suites when changing binding restoration.
4. **Walrus:** `Lib/test/test_named_expressions.py`, `NamedExpressionAssignmentTest.test_named_expression_assignment_01`, `_06`, `_14`; `NamedExpressionScopeTest.test_named_expression_scope_02`, `test_named_expression_global_scope`, `test_named_expression_nonlocal_scope`, `test_named_expression_scope_in_genexp`; `NamedExpressionInvalidTest.test_named_expression_invalid_in_class_body`, `test_named_expression_invalid_rebinding_iteration_variable`, `test_named_expression_invalid_list_comprehension_iterable_expression`. These establish that expression emission alone is insufficient.
5. **Deferred annotations:** `Lib/test/test_type_annotations.py`, `DeferredEvaluationTests.test_function`, `test_class`, `test_module`, `test_class_scoping`, `test_ignore_non_simple_annotations`. The first test also uses positional-only arguments, so enabling that increment first avoids altering its language contract. Tests using `annotationlib`, generated modules or exotic globals need their helpers/runtime support ported explicitly.

The corresponding pinned test files are linked in the inventory. Other larger feature entry points are `TestPatma.test_patma_000` onward in `test_patma.py`; `TestExceptStarSplitSemantics.test_match_single_type_partial_match` and `test_match_single_type_nested`; `TypeParamsAccessTest.test_function_access_01`; `TypeParamsAliasValueTest.test_alias_value_01`; `TestTString.test_interpolation_basics`; and `CoroutineTest.test_await_1` onward. Each is a starting selection, not a sufficient complete feature suite.

### Positional-only implementation seam

Keep this change in the existing function machinery. In `visitArguments`, visit positional-only parameters before ordinary ones. In `buildcodeobj`, use their combined ordered list for JavaScript parameters, parameter-to-cell initialization and argument names; emit `co_argcount` including both groups and `co_posonlyargcount` separately. Existing `args.defaults` already spans both groups, so no new default representation is needed. Cache the count in function `$memoiseFlags`; keyword matching in `$resolveArgs` must start after the positional-only segment. Generators use the same binder. [Current compiler](../src/compile.js), [symtable](../src/symtable.js), [function](../src/function.js).

When a function has `**kwargs`, a keyword matching a positional-only parameter belongs in that dictionary; it neither binds the positional slot nor constitutes a duplicate positional argument. Without `**kwargs`, CPython collects conflicting positional-only names in declaration order when reporting an unmatched keyword. See [CPython keyword matching](https://github.com/python/cpython/blob/18ef0f0cb5278fa6583b753ffaaef7f46e416ab9/Python/ceval.c#L1765) and [conflict reporting](https://github.com/python/cpython/blob/18ef0f0cb5278fa6583b753ffaaef7f46e416ab9/Python/ceval.c#L1549). Follow CPython's binding-error precedence. The selected upstream invalid-call methods require CPython's positional/keyword-only wording and name formatting, so those diagnostics were aligned in the same binder. Add `test_closures` and `test_super` to the initial upstream selection because positional-only parameters can be cells and include the receiver of zero-argument `super()`.

## Harness boundaries and completion criteria

Skulpt's [unittest implementation](../src/lib/unittest/__init__.py) has `assertRaisesRegex`, so many synchronous method bodies can be copied with their assertions intact. CPython `test.support`, subprocess checks, `_testcapi`, bytecode/disassembly assertions, frame inspection, platform/resource skips and specialized-build tests cannot simply be imported into Skulpt. Select behavior tests first; port a required helper locally when small and necessary. Document any omitted infrastructure and retain skipped coverage as explicit debt. Do not weaken an assertion to make a port pass.

Run selected ports through the normal parser/compiler/runtime and also run their original methods under the matching CPython version. Use 3.14 for the target baseline; consult earlier versions only to resolve historical changes or a deliberate compatibility decision. Run `skulpt_bugs` and affected generator regressions after changes in binding/control flow. Timing comparisons should use the production bundle after correctness, with compilation and execution measured separately; CPython's internal optimizer instructions are not implementation requirements for generated JavaScript.

For each inventory row, track: unsupported / failing CPython test / passing selected tests / remaining unported assertions. A feature is complete only when its relevant language semantics and runtime protocol tests pass, not merely when parsing succeeds. Keep guards for unsupported nodes. The foundation and the small dictionary-order/positional-only increments are complete. Next, establish and fix comprehension isolation before adding walrus; annotation scopes and larger runtime features follow as separate reviewable branches. Existing `test_dictcomps` scope assertions are commented out: these are explicit missing coverage, and must be restored from upstream when scope isolation is implemented. No project board or parent issue is required to start this sequence.

## Comprehension scope increment

`stu-dev/compiler/comprehension-scopes` introduces logical symbol-table blocks for list/set/dict comprehensions and keeps their generated loops inline. Outer iterables execute in the enclosing scope; iteration locals and captured cells use distinct storage. Correspondence: CPython `symtable_handle_comprehension` and `codegen_comprehension`.

Selected upstream coverage now includes 53 unchanged list-comprehension methods and six dictionary-comprehension methods, including restored scope assertions. The list suite's infrastructure omits `subTest`, returns only requested output variables instead of `locals()`, and supplies `__name__` to work around existing Skulpt class construction in an empty `exec` namespace. Test bodies/assertions are unchanged. The production suite passes (3,038 Python 3 tests). Installed CPython 3.14.3 passes 47 list methods and all six dictionary methods. Six newer upstream methods involving `__class__`, `__classdict__`, or `__conditional_annotations__` raise CPython's own compiler `SystemError` in that installed version. A freshly built interpreter from the reference checkout passes all 53 list methods and all six dictionary methods. All pass in Skulpt. Frame/code inspection, `locals()` visibility, assignment expressions and `__classdict__` remain separate increments.

## Assignment-expression increment

`stu-dev/compiler/assignment-expressions` implements `NamedExpr` evaluation/store/result emission and CPython's `symtable_handle_namedexpr` / `symtable_extend_namedexpr_scope` binding rules. Comprehensions bind assignment expressions in the nearest enclosing function/module, respecting globals, nonlocals, and mangling. Iteration-target conflicts (including later inner loops), class-body use, and iterable-expression use are rejected during symbol-table traversal, including nested lambdas in iterable expressions.

The parent rejects CPython's `(a := 10)` case with unsupported `NamedExpr`; this increment passes 73 upstream named-expression methods in Skulpt and the built reference CPython interpreter. Only `subTest` infrastructure is adapted; assertions remain unchanged. The upstream generator-expression test that uses `locals()` remains pending that runtime feature. The list-comprehension assignment-expression method is also ported unchanged (54 list methods pass). The full production suite passes, including 3,112 Python 3 tests.

The walrus Spec review found that the compiler's existing unconditional `NotImplemented` shortcut discarded stores and bypassed rebinding. The follow-up removes that shortcut so builtin names follow normal symbol-table/name operations. Both ordinary and comprehension assignment-expression probes now agree with CPython; the 73 upstream methods and compiler regressions still pass.

## Locals and namespace increment

`stu-dev/compiler/locals-namespaces` implements independent optimized-scope `locals()` snapshots, shared module/class namespace dictionaries, closure visibility, and PEP 709 comprehension overlays. Compiler code units install their active namespace reader and restore the caller on return, exception, and host suspension. Inlined comprehension scope IDs survive suspension; error unwinding restores the enclosing view. `vars()` and no-argument `dir()` use the same namespace, and default `eval`/`exec` use caller globals and locals. Explicit dictionary namespaces share mutations and deletions directly with generated property access.

Class construction and Python-module import retain the same namespace seen by the compiler, class metaclasses, and `sys.modules`. The unittest helper now discovers `__main__` explicitly, because corrected `globals()` inside `unittest` properly returns that module's globals.

All 59 selected list-comprehension methods now use CPython's actual `locals()` function harness, with only `subTest` infrastructure adapted; all 74 named-expression methods pass. Three previously disabled scope methods and `BuiltinTest.test_vars` are restored unchanged from the pinned checkout, including their small upstream helpers. These selected cases pass under the built CPython reference. The production bundle passes full `npm test` (3,122 Python 3 tests), including generator/suspension guards. Focused host probes confirm namespace visibility before/after suspension, exceptional cleanup, and caller restoration while execution is suspended.

Remaining adjacent work: general mapping execution namespaces, byte sources, single code mode and flags, custom builtin namespaces, native module dictionary identity, and frame inspection APIs. Current execution namespace arguments still explicitly require dictionaries; this increment does not claim complete `compile`/`exec`/`eval` or frame compatibility.

The namespace review also found that the old `eval` result temporary overwrote and deleted a user binding. Expression-mode compilation now returns the expression directly, and `eval` of executable code returns `None`. A CPython-checked regression preserves the namespace throughout both modes; no Python-visible result temporary is emitted.

## General execution mappings

`stu-dev/compiler/execution-mappings` extends the existing namespace bridge to general mapping locals for `exec`/`eval`, and class `__prepare__` uses the same bridge. Globals retain dictionary base semantics; locals honor mapping lookup/store/delete and overridden `keys()`. No-argument `dir()` requests the mapping's keys. Python 3.13 keyword arguments for globals/locals are accepted while source remains positional-only.

The unchanged `TestSpecifics.test_exec_with_general_mapping_for_locals`, plus `BuiltinTest.test_eval_kwargs`, `test_exec_kwargs`, and `test_general_eval`, pass under Skulpt and the built pinned CPython checkout. Assertions are unchanged; one non-asserting `collections.UserDict` fixture call is omitted because that stdlib class is absent. The nested spreadsheet example covers locals mappings without `keys()`. Class/scope/list-comprehension and builtin regressions pass. Namespace property hooks retain the existing synchronous host-suspension limitation of class mapping access.

## Live super bindings and deletion

`stu-dev/compiler/live-super-bindings` moves zero-argument `super()` resolution into the builtin, using live code-unit metadata from the active compiler scope. Correspondence: `Objects/typeobject.c:super_init_without_args`. The first positional argument can be fast or a cell; PEP 709 comprehension bindings temporarily replace the visible receiver. Aliases and locally shadowed `super` now use ordinary call dispatch. Missing arguments, deleted first arguments, missing/empty class cells follow CPython error order.

Three previously disabled upstream methods (`test_super_with_closure`, `test_super_in_class_methods_working`, `test_obscure_super_errors`) are restored unchanged, and `test_shadowed_local` is added unchanged. Eight selected upstream/regression methods pass under the built reference interpreter; ten Skulpt super tests and the compiler/comprehension/positional-only/suspension suites pass. Focused CPython-checked regressions cover reassignment, alias calls, receiver cells across yields, comprehension receiver/class shadowing, fast-local deletion and global deletion. Fast deletion now unbinds the JS variable instead of attempting JavaScript `delete`; global deletion has its missing statement terminator restored.

## Compile options and optimization

`stu-dev/compiler/compile-options` accepts keyword compile arguments and validates C-integer flags/optimization levels, modes and unknown flag bits. Optimization level 1 removes assertions and makes `__debug__` false; level 2 also removes docstrings. The compiler treats `__debug__` as a constant even if the builtins module attribute changes. Symbol-table validation rejects writes/deletion before dead-code elimination. Correspondence: `Python/bltinmodule.c:builtin_compile_impl`, `Python/codegen.c:codegen_assert` and CPython symbol-table binding validation.

The native `builtins` module exposes the same shared namespace used by runtime name lookup and execution namespaces. Nine additional unchanged `TestSpecifics` methods are ported (only subTest infrastructure adapted). Source optimization and argument/error portions of `BuiltinTest.test_compile` retain their assertions; its AST/buffer paths remain separate coverage. All 15 compile methods pass in Skulpt and the pinned built CPython interpreter. The CPython syntax doctest debug writes are also checked inside dead suites and removed assertions.

This increment validates recognized flag bits but explicitly guards the remaining AST-return/type-comment, top-level-await/incomplete-input, Barry and stringized-annotation flags. Historical mandatory future flags are harmless in Python 3; future inheritance, special modes, bytes/AST source and complete code metadata still need their own implementation. Optimization -1 uses Skulpt's default interpreter level 0.

## Interactive compilation

`stu-dev/compiler/interactive-mode` supplies the `single_input` boundary over the parser's module entry point: one compound statement or one logical simple-statement line, with interactive newline rules. It produces an `Interactive` root; module-scope expressions call `sys.displayhook`, while nested function/class expressions remain ordinary. Top-level string expressions are displayed rather than treated as module docstrings. Correspondence: CPython `single_input` grammar and `Python/codegen.c:codegen_visit_stmt` / `PRINT_EXPR`.

The native sys module now supplies default/original display hooks with None suppression, shared `builtins._`, dynamic stdout and caller-supplied hook dispatch. CPython's unchanged valid/invalid single-statement and interactive docstring methods pass (18 compile methods total). Three unchanged DisplayHookTest methods pass with local test.support context fixtures and a StringIO fallback; only harness infrastructure changes. These 21 cases also pass in the built pinned CPython interpreter. Incomplete-input/dedent flags remain explicitly guarded until their separate contract is implemented.

## Byte source decoding

`stu-dev/compiler/source-decoding` decodes byte sources before AST parsing for `compile`, `exec`, and `eval`. It follows CPython tokenizer BOM detection, first/second physical-line encoding-cookie recognition and UTF-8/Latin-1 cookie normalization. Unicode sources ignore coding cookies; UTF-8 decoding is strict, Latin-1 preserves every byte, and conflicting BOM/cookie combinations fail explicitly. `eval` strips only leading ASCII spaces/tabs, following `builtin_eval_impl`.

CPython's unchanged `TestSpecifics.test_encoding`, eight `MiscSourceEncodingTest` methods and the fully restored `BuiltinTest.test_eval` pass in Skulpt and the pinned built interpreter. The source tests cover UTF-8, Latin-1, ISO-8859-15, CP932/CP949 fixture text, malformed/truncated UTF-8, BOM prefixes, conflicting cookies and decoded SyntaxError source text. Only subTest infrastructure is adapted. General buffer/AST sources and codec-registry integration remain separate work; nonstandard codecs are currently limited to host TextDecoder labels plus the aliases required by these upstream fixtures.

## Custom builtin namespaces and imports

`stu-dev/compiler/custom-builtins` makes name lookup use the builtin mapping captured by each frame/function. Function creation resolves a globals `__builtins__` module or mapping; replacing that globals entry later does not replace the function's captured mapping, while mutations to the captured mapping remain visible. Generator/host suspension state preserves the mapping. Python function `__builtins__` exposes it read-only. Correspondence: `Objects/funcobject.c:PyFunction_NewWithQualName` and `Python/ceval.c` name/import dispatch.

Import statements call the captured mapping's `__import__` with Python globals/locals, tuple fromlist (None for ordinary imports), and level 0 in Python 3. Missing hooks raise ImportError. Five unchanged CPython builtin methods cover empty/invalid builtin mappings, overridden dictionary lookups, mapping proxies and custom import arguments. Three CPython-checked regressions cover function/generator capture, module-valued builtins and import namespaces. All 27 compile tests pass in Skulpt and the pinned interpreter. Mapping hooks retain the existing synchronous host-suspension limitation. Native module dictionary sharing is completed by the later module-dictionaries layer. `__build_class__` dispatch, iterator reduce hooks, full function-code introspection and native-module dictionary identity remain separate increments.

## Class-builder dispatch

`stu-dev/compiler/class-builder` lowers classes through the captured builtin `__build_class__`, following `codegen_class`: evaluate decorators, load builder, create the class body function, then evaluate bases/keywords and call the builder. The default builtin validates a Python function/name and reuses the existing metaclass/prepare/class-cell construction path. The body function captures globals/builtins/closures, accepts no arguments and returns its class cell when needed. Module binding uses ordinary class name lookup, including the builtins fallback.

CPython's unchanged `BuiltinTest.test_exec_globals_frozen` is restored. Three CPython-checked regressions verify custom hook forwarding, class closures, lookup-before-base side effects and builtin argument validation. All 32 compile methods, 42 compiler regressions, ten super methods and 59 comprehension methods pass. These compile cases also pass the pinned built CPython interpreter. Existing dynamic base resolution (`__mro_entries__`) and suspension inside class preparation/body still need their own protocol increments.

## Live module dictionaries

`stu-dev/compiler/module-dictionaries` makes `module.__dict__` and `vars(module)` return a persistent Python dictionary shared with module attributes and compiled globals. Native imports bind existing JS namespace properties to the dictionary so native closures (including sys.displayhook stdout access) observe Python dictionary writes. Native module-valued builtin captures now retain live contents and dictionary identity. Module data-descriptor precedence preserves subclass overrides while namespace keys cannot shadow a data descriptor. Legacy raw JS builtin extensions/stubs are wrapped as Python function objects so the exposed dictionary remains printable.

Five existing module methods are restored unchanged from pinned CPython 3.14; all other existing module tests are retained. Three CPython-checked regressions cover namespace mutation/execution, native stdout dictionary writes and builtin dictionary repr; the compile regression verifies native module builtin mutations and identity. The unittest runner snapshots discovered module names before running methods because methods can add globals to the now-live module dictionary. The selected upstream methods and added behavioral cases pass the built reference interpreter; the complete Skulpt module and descriptor suites pass.

## Dynamic class bases

`stu-dev/compiler/dynamic-bases` implements CPython `update_bases`: only original non-type bases receive `__mro_entries__`, each hook sees the same original tuple, tuple replacements are flattened once, and changed bases produce `__orig_bases__` after the class body. Metaclass selection/preparation sees the resolved bases. Class code generation expands starred bases through the ordinary call argument expansion path. Direct `type()` rejects MRO-entry resolution and accepts tuple subclasses, preserving their tuple identity/type in `__bases__`. GenericAlias's existing hook now takes its required bases argument.

The class-construction helpers `types.new_class`, `resolve_bases`, `prepare_class`, `_calculate_meta` and `get_original_bases` are copied from pinned CPython 3.14. Nine unchanged `TestMROEntry` methods, seven unchanged `test_types` methods and one CPython-checked starred/generic-base regression pass in Skulpt and the reference interpreter. Existing generic-class and types methods are retained. Typing-specific generic aliases/type variables remain separate coverage. Class preparation/body and MRO hooks retain their existing synchronous host-suspension limit.

## Globals dictionary subclass lookup

`stu-dev/compiler/global-mapping-lookup` separates `LOAD_GLOBAL` from `LOAD_NAME` following `_PyEval_LoadGlobalStackRef`. Exact dictionaries retain direct lookup; function/global loads through dictionary subclasses honor item/missing hooks, propagate non-KeyError exceptions and fall back to captured builtins only for missing names. `LOAD_NAME` keeps CPython's direct globals fallback after locals lookup. Globals stores/deletions retain base-dictionary operations.

CPython's unchanged `TestSpecifics.test_globals_dict_subclass` is added, together with a CPython-checked regression distinguishing module lookup, function lookup, builtin fallback and hook exceptions. All 37 compile methods pass in both runtimes; scope, comprehension and generator/suspension regressions pass.

## Compile filenames

`stu-dev/compiler/compile-filenames` follows `PyUnicode_FSDecoder`/`PyOS_FSPath`: filenames accept strings, bytes and type-level `__fspath__`, reject invalid results and embedded NULs, and decode filesystem bytes as UTF-8 with surrogateescape. Code objects expose read-only `co_filename`. Generated JavaScript encodes filenames as string literals in traceback, breakpoint and suspension paths; quotes/newlines no longer break executable code.

CPython's filename, filename error-path and path-like methods are ported; assertions are unchanged, except the bytearray/memoryview fixture block remains deferred until those buffer types exist. The upstream FakePath fixture is retained unchanged. A CPython-checked regression exercises malformed UTF-8, BOM preservation, special-method lookup, invalid path results and functions/generators/classes/comprehensions under quoted filenames. All 41 compile methods pass in both runtimes; compiler and generator/suspension regressions pass.

The filename review found an identity mismatch: CPython retains string filename objects and subclasses. The follow-up preserves that Python object separately from generated JavaScript text, with direct/path-like identity assertions passing in both runtimes (42 compile methods).

## Qualified code-unit names

`stu-dev/compiler/qualified-names` follows `compiler_set_qualname`: each code unit records its qualified name on scope entry, functions/lambdas add `<locals>` to their children, classes preserve nested class paths, and explicit global declarations reset named definitions. Function and generator names use this metadata. Class bodies assign `__qualname__` before running user statements; type construction consumes it without retaining it in the final class dictionary or mutating the input namespace.

CPython's unchanged function qualified-name method, complete generator-name method and class qualified-name dictionary method are restored. A CPython-checked regression verifies metaclass namespace visibility, nested classes/functions/generators, PEP709 lambda naming and global class declarations. Function-attribute, descriptor, generator and compile suites pass. Annotation-scope qualification will be added alongside the annotation-scope implementation.

Full validation caught Python2 repr regressions from applying nested qualified names to both modes. The follow-up gates nested qualified-name emission to Python3 and retains Python2's existing class-method names.

The Spec review caught generator-expression children gaining an extra `<locals>` and implicit class-name stores bypassing declared scopes. Scope entry now retains the actual code-unit kind (distinct from temporarily inlined comprehension symbol tables), and implicit `__qualname__`/`__module__` stores use `nameop`. CPython-checked regressions cover lambda/nested-generator names plus global/nonlocal metadata bindings.

A second Spec pass caught the module nesting check still consulting an inlined symbol table. Module/Expression/Interactive code-unit kinds now determine that boundary, with module-comprehension names checked through exec/eval/single in both runtimes.

## Executable code objects and metadata

`stu-dev/compiler/code-metadata` emits code-unit metadata after defining the compiled JS functions, following `compiler_enter_scope`/`compute_code_flags`. Python code objects expose read-only argument counts, qualified names, filename, first line, flags, local names/count and cell/free names. Functions expose shared `__code__` objects and their live `__globals__`; `types.CodeType` identifies this code class. Compiled objects retain an executable JS function, so repeated exec shares nested function code identity; exec/eval also accept ordinary function code without free variables. Bytecode representation, constant/name tables, replacement/construction APIs, closure arguments, async flags, future inheritance and annotation-generated cells remain separate increments.

CPython's unchanged mangling, positional-only definition, code qualified-name and function-globals methods are restored. Local/cell/free/count/flag assertions are derived from test_code's opening doctest, with its functions retained; bytecode/constants output is explicitly deferred. CPython-checked regressions cover compiled identity/filename subclasses, execution, generators, inlined comprehension locals, decorated/source lines and metadata immutability. Symbol-table cleanup removes the phantom `lambda` local and propagates actual nested status through class scopes. Source annotation handles physical CR/CRLF lines and escapes JavaScript-only Unicode line separators.

Local indexes now follow compiler name-use order, including inlined comprehension temporaries, rather than symbol-definition order. Constant if/while suites are visited by code generation, preserving locals and rejecting invalid control flow even in dead suites. CPython's unchanged return/break/continue outside-function/loop methods and its full error checker are ported; no assertions are removed. Runtime control flow still skips dead suites.

Generator expressions now bind their implicit `.0` iterator through the ordinary function argument path, making the executable ABI agree with their exposed argument count. This replaces post-creation suspension-dictionary injection. Generator/comprehension and suspension tests verify the existing execution behavior. Class code metadata includes its existing implicit `__class__` cell.

The code-metadata review caught function defaults leaking into exec/eval of code objects; those execution frames now have no positional/keyword defaults, preserving the original functions' defaults. Explicit accepted future bits are retained in co_flags across nested code units. A generator-call argument-array regression caught during focused validation is corrected in the same follow-up; all affected paths have public CPython-checked assertions.

The walrus metadata follow-up distinguishes logical comprehension closure cells from cells needed by real function/class/generator-expression code units. Targets crossing only an inlined comprehension are reported as locals in compiler-use order; genuine captures retain cells. Regressions cover ordinary targets, argument targets, earlier bindings and real nested lambda captures. Runtime closure linkage remains the existing shared-cell implementation.

The follow-up review found class-shadowed outer captures use `DEF_FREE_CLASS`, rather than a FREE scope value. Capture classification now includes that flag, preserving the true outer cell and its exclusion from fast locals. The regression checks both metadata and execution against CPython.

## Function construction and closure cells

`stu-dev/compiler/function-construction` follows `Objects/funcobject.c:func_new_impl` for `types.FunctionType`, including the Python 3.14 keyword-default argument, globals/builtins capture and closure validation. Function defaults retain Python tuple/dictionary identity; mutations to keyword defaults affect subsequent calls. Functions expose their closure tuples, with cell identity shared by all functions using the same existing closure slot. `types.CellType` supports empty/populated construction and cell-content mutation/deletion. Module/expression code objects can also be invoked through FunctionType using their module execution ABI.

Six unchanged CPython function-attribute methods and two unchanged FunctionTests methods are restored/ported. Three CPython-checked regressions cover shared and supplied closure identity, validation/deletion, renamed functions, default identity/live mutation and module/expression execution. The main-module namespace now contains the already-loaded builtins module, matching CPython and preserving the upstream builtin-identity assertions without test adaptations. Function code reassignment, code constructors/replacement and execution closure keywords remain separate increments.

The review follow-up caches each compiled root code object on its executable and registers supplied cells on closure aliases. Constructed functions retain the supplied code object, and functions nested inside them expose the original supplied cells. Both identities have CPython-checked public regressions.

## Execution with explicit closures

`stu-dev/compiler/execution-closures` adds Python 3.11's keyword-only `exec(..., closure=...)` contract, following `Python/bltinmodule.c:builtin_exec_impl`: exact tuple, matching free-variable count, cell-only contents and code-source restriction. The execution frame reuses FunctionType's cell aliases, so nonlocal writes update supplied cells. CPython's unchanged `BuiltinTest.test_exec_closure` covers native and manually supplied closures plus invalid forms. A CPython-checked regression covers tuple subclasses, empty closures, argument placement and None/string execution.

## Function code replacement

`stu-dev/compiler/function-code-replacement` implements `function.__code__` assignment/deletion validation following `Objects/funcobject.c:func_set_code`. Existing closure cells retain their order/identity while compiler free-variable names are rebound to those cells. Argument metadata and dispatch refresh; function name, qualified name, docstring, defaults, keyword-default dictionary, globals and captured builtins retain their state. Three unchanged upstream methods are restored, with a CPython-checked regression exercising renamed closure slots and retained live defaults. The commented upstream assertion claiming a replaced function should use the other function's cell remains unchanged: CPython actually retains its existing cell. Cross generator/coroutine-kind assignment remains explicitly guarded until its required deprecation warning can be emitted.

The replacement follow-up marks refreshed call metadata ready immediately. Executing replacement module/expression code cannot refresh metadata again and discard retained defaults. The CPython-checked regression replaces code through an expression and back to an ordinary function; retained defaults still bind. The redundant single-argument makeClosure adapter is removed.

Module/expression code entered through a function uses that function's captured builtin mapping, including after code replacement. Ordinary exec/import entry still resolves the execution namespace. A regression changes globals' builtin entry after capture and checks both constructed and replaced functions.

Constructed root-code functions also mark constructor-refreshed metadata ready before their first call, preserving supplied defaults through execution and later replacement. The same replacement regression covers this constructor path.

## Future imports and compiler flag inheritance

`stu-dev/compiler/future-flags` scans initial future imports following Python/future.c and rejects misplaced imports in compiler scopes. Already-mandatory Python 3 source features do not set historical flags; explicit flags retain their existing code metadata. The CPython __future__ module supplies actual feature objects and release information, so future statements execute their imports normally. Runtime compile/exec/eval inherit only the calling frame's future bits, with dont_inherit controlling compile; parser flags and CO_NESTED are excluded. Barry and annotations source modes are explicitly guarded until their following implementations.

The two upstream future-flag methods retain their assertions; the compile check for the two guarded features is deferred. CPython-checked regressions cover import identity, mandatory flags, compile/exec/eval inheritance, class/function/generator frames, dont_inherit, parser-flag isolation and invalid future placement.

## Stringized annotations

`stu-dev/compiler/stringized-annotations` implements CO_FUTURE_ANNOTATIONS from source imports and explicit/inherited flags. Its limited expression unparser follows CPython Python/ast_unparse.c precedence, containers/comprehensions, lambda arguments, slices, numeric repr and f/template string formatting. The compiler emits these strings instead of evaluating annotation expressions. Symbol-table annotation blocks validate syntax without contributing names/cells to enclosing scopes, following symtable_enter_existing_block in future mode. Private annotation keys are mangled while their source expression strings retain original spelling.

Six unchanged upstream AnnotationsFutureTestCase methods cover canonical formatting (including template-string text), forbidden expressions, infinity, complex targets and symbol-table isolation. The typing integration method remains omitted until typing.get_type_hints is supported. CPython-checked regressions cover explicit/inherited flags, positional/variadic annotations, private names, closure isolation and annotation-only target evaluation. This also fixes existing missing base/index side effects and annotation namespace setup for nonsimple targets. Python 3.14's default deferred annotation functions and introspection follow separately.

The stringized-annotation follow-up also corrects existing function construction ordering: positional and keyword defaults are evaluated before annotations, and annotation data is attached to the original function before decorators run. Replacement functions retain their own annotations. A CPython-checked regression covers decorator visibility/replacements and default-expression ordering; the default-mode case forces annotation access inside the decorator so it applies both before and after deferred evaluation.

The Spec review also found future annotation blocks must be skipped when comprehension walrus bindings extend to their enclosing scope. Class-body restrictions and function/module symbol binding now follow symtable_extend_namedexpr_scope; a CPython-checked regression covers rejection and unevaluated outer bindings.

## Function annotation functions and lazy cache

`stu-dev/compiler/function-annotations` emits actual __annotate__ function code units for ordinary function scopes and for future-mode functions, following codegen_function_annotations/setup_annotations_scope. Their positional-only format argument has a distinct internal symbol and the public name format; formats above VALUE_WITH_FAKE_GLOBALS raise NotImplementedError before evaluation. Default annotations evaluate only on access, retain real enclosing cells, and cache successful dictionary results. Future annotations use the same callable interface with canonical strings and no closure. Variadic starred annotations unpack exactly one value. Default annotations for functions defined in class scopes and module/class annotation functions follow with the class-dictionary-cell layer.

Function __annotate__/__annotations__ getters and setters follow funcobject.c cache invalidation, deletion, callable validation and result checking. Two unchanged upstream deferred evaluation methods and the unchanged manual-annotation helper cover evaluation after late bindings and setter behavior. CPython-checked regressions cover generated code/signatures/formats, evaluation order, cache identity, explicit callbacks, future functions and starred annotations.

The function-annotation Spec follow-up also renames the argument-binding table's parameter to format, retaining the distinct internal variable. Missing/positional-only keyword diagnostics now use the public name; the generated-code regression checks both against CPython.

## Heap class dictionaries

`stu-dev/compiler/class-dictionaries` gives heap types a real Python dictionary, following type_new's copied namespace. Type/instance MRO lookup and the read-only __dict__ mapping proxy consult this shared dictionary; normal type attribute updates and __doc__/__module__ setters update it. The copy preserves supplied string-key identity and nonstring keys, removes consumed qualname/classcell entries, and incorporates generated descriptors and implied static/class methods. This is the storage needed for the following __classdictcell__ annotation scope layer.

An unchanged upstream metaclass dictionary-proxy method and three CPython-checked regressions cover live views, inherited class/instance attribute updates, replacement/deletion, copied input/key identity, nonstring keys and metadata/implied method descriptors. Existing class metadata such as __firstlineno__/__static_attributes__/weakref support remains separate compiler/runtime work.

Full validation found the heap namespace field collided with Sk.builtin.str.$dict, the existing __dict__ name constant. The follow-up uses a distinct $classDict field; a CPython-checked regression covers native str dictionaries/dir/module and string-subclass lookup/metadata.

The Spec review corrections also use the native hash-preserving dictionary copy and call descriptor __set_name__ with each original key from a namespace snapshot. A CPython-checked regression covers a key that rejects rehashing, a string-subclass descriptor name and a nonstring descriptor name.

## Class dictionary cells for method annotations

`stu-dev/compiler/class-annotation-scopes` emits __classdictcell__ alongside __classcell__ when method annotation functions need class scope. Type construction validates and fills that cell with its retained dictionary before descriptor naming and __init_subclass__. Annotation lookup follows codegen_nameop's LOAD_FROM_DICT_OR_DEREF/GLOBALS: actual class members precede outer cells or globals, class-bound names exclude same-named outer bindings, and explicit class globals bypass class lookup. The cell initially holds the class body mapping, then type construction replaces it with the retained dictionary. Nested lambda/comprehension bodies retain ordinary scope rules.

One unchanged upstream format-name collision method and five CPython-checked regressions cover late nested classes, live updates, cache isolation, construction callback timing, global/free/class precedence, nested scope rules and annotation access during the class body. Module/class variable annotation functions remain the next layer.

## Class and module annotation descriptors

The first `stu-dev/compiler/deferred-variable-annotations` commit adds typeobject.c/moduleobject.c __annotate__/__annotations__ descriptors. Classes use only their own dictionary, prefer explicit annotations over __annotations_cache__, bind explicit descriptors normally, and clear generated annotation callbacks on annotation assignment/deletion. Modules cache successful dictionaries in their own namespace and avoid caching during initialization, using Skulpt's existing loader flag and an explicit module spec. Callable validation, arbitrary explicit annotation values, deletion errors and None cache retention follow CPython.

Six unchanged upstream type annotation methods and the unchanged manual annotation helper (applied to classes/modules), plus two CPython-checked regressions, cover cache identity/storage, inherited isolation, descriptor overrides, invalid callbacks and initialization. Compiler-generated variable annotation functions follow in the next commit.

The descriptor Spec correction snapshots module initialization before invoking its callback and guards native type descriptor setters even when called directly. Three CPython-checked regressions cover callbacks flipping initialization in either direction, optional _initializing properties (AttributeError means absent; other errors propagate), and direct immutable-type setter/deleter calls.

## Deferred variable annotation compilation

The next `stu-dev/compiler/deferred-variable-annotations` commit follows symtable_visit_annotation and codegen_process_deferred_annotations: module/class simple annotations share an annotation scope and produce a real __annotate__ function. Module setup precedes body execution; class setup follows its body. A synthetic __conditional_annotations__ set records successful execution of module annotations and annotations in conditional class suites. Deferred evaluation checks membership, evaluates in source order and preserves repeated-name overwrites. Class conditional sets are closure cells; module sets are globals. Future-mode variables retain eager canonical string storage.

Function-local annotations validate in detached scopes without adding enclosing cells; nonsimple module/class annotations participate in shared scope analysis without emitting evaluation. Synthetic class dictionary closure loads are retained independently of same-named annotated targets, and annotation functions have CPython's ordinary/nested flags rather than CO_METHOD. Thirty unchanged upstream methods cover setup, default/future assignments, deferred class/module behavior, lexical and conditional scopes, loops/with/try, invalid expressions, complex comprehension regressions and rebinding the conditional set. Two CPython-checked regressions cover code metadata/live values and partially executed module setup/cache behavior. Upstream except-star and match annotation methods remain until those compiler increments; annotationlib's introspection remains a separate adjacent module.

Full execution validation also restores the explicit Python 2 annotated-assignment SyntaxError in symbol-table validation, before deferred emission. Existing execution case t905 protects this compatibility boundary.

The variable annotation review correction shares namespace scope analysis for nonsimple annotations and initializes conditional bookkeeping for every module annotation, including future mode. A CPython-checked regression covers nonsimple closure captures and empty conditional sets. The duplicate upstream format-name collision method remains only in its existing class-scope test module. Legacy annotation fixture/test expectations are updated to CPython 3.14: default modules no longer create __annotations__ eagerly, explicit mapping writes were removed upstream, and the separate-globals/locals exec method now accesses __annotate__ after merging namespaces.

A further Spec correction retains conditional parent bookkeeping without capturing its synthetic set in an annotation function unless a simple annotation requires a membership check. The namespace regression verifies closure arity with conditional nonsimple targets in either statement order.

## Exception notes and chaining descriptors

`stu-dev/compiler/exception-notes` adds PEP 678 `BaseException.add_note` using
Objects/exceptions.c optional attribute lookup and native list append. It respects
`__notes__` descriptors, accepts string/list subclasses, preserves arbitrary
explicit note storage and propagates getter/setter failures. The exception cause
setter now raises Python TypeError for invalid values, rejects deletion and sets
`__suppress_context__`; that descriptor accepts only bool and rejects deletion.
The existing OSError type is exposed in builtins, allowing unchanged upstream
exception subclass tests to exercise these inherited descriptors.

Three unchanged CPython test_exceptions methods cover notes and chaining
descriptors. Compiler propagation of active exceptions, implicit contexts and
traceback introspection follow separately.

## Exception group runtime

`stu-dev/compiler/exception-groups` implements BaseExceptionGroup construction,
readonly message/exceptions, derive, subgroup and split, following
Objects/exceptions.c. ExceptionGroup is created through the existing type
constructor with BaseExceptionGroup and Exception bases, matching CPython's
mutable heap type. Construction snapshots the exceptions, chooses ExceptionGroup
for non-base exceptions, validates subclass restrictions and preserves custom
sequence repr. Recursive partitioning retains hierarchy/order/leaf identity,
uses overridden derive and copies cause/context/notes. Predicates, derive and
metadata descriptors may suspend. Both group names are Python 3-only builtins.

Thirty-six unchanged upstream methods and the repr test with its Sequence ABC
helper base omitted, plus two CPython-checked regressions, cover construction,
multiple inheritance, fields/repr, generic aliases, splitting and custom derive
metadata. Harness adapters provide subTest/assertIsSubclass and narrow the
helper's known list template assertion. Existing MemoryError is exposed because
the actual upstream group helper uses it. Class-subscript and repr failure
diagnostics are aligned where these upstream methods require them. Traceback
introspection and the upstream limited-thread-stack machinery remain separate
runtime work; except-star compilation follows the group runtime.

The group Spec review correction retains supplied exact tuple identity while
converting tuple subclasses, and applies Python string conversion to message
subclasses. A CPython-checked regression covers both identities and conversion
failures.

## Active exception state and cleanup

`stu-dev/compiler/active-exceptions` separates pending errors from each compiled
frame's handled exception, following PUSH_EXC_INFO/POP_EXCEPT and codegen_try_except.
Bare raise and sys.exception read the current frame; a suspended generator with
no local handler inherits the current caller on every resume. Python 3 exception
targets are cleared on normal and nonlocal exits, including explicit deletion.
Class bodies have their own pending error. Finally and sync/async context-manager
cleanup restore the enclosing state, chain replacement errors, and preserve or
override pending return/break/continue as CPython requires. Break and continue
now enter cleanup immediately rather than executing following statements.
Raise-from records suppression without losing its implicit context.

Nineteen unchanged test_exceptions methods and three unchanged test_with methods
from CPython 3.14 at 18ef0f0cb5278fa6583b753ffaaef7f46e416ab9 cover cleanup,
context cycles, generators and context-manager truth conversion. The latter
class adapts unittest.fail to raise AssertionError as CPython's harness does.
Seven CPython-checked regressions cover runtime wrappers, generator propagation, nonlocal cleanup, class/frame inheritance,
finally overrides and context-manager failures. The existing host suspension
guard checks handled state before/after resume and absence in the suspended caller.
Traceback objects/sys.exc_info and except-star control flow follow separately.

Initial raises are distinguished from propagation through caller frames, so a
generator reraising an exception with no context does not acquire the current
caller's handled exception. Catch emitters share this policy. PEP 479 and invalid-__anext__ wrappers retain their original cause/context and
set suppression before propagation.


## Traceback objects and exception information

`stu-dev/compiler/tracebacks` adds native traceback nodes with frame/code/line
identity, mutable cycle-checked tb_next, TracebackType construction,
BaseException.__traceback__/with_traceback, sys.exc_info and the traceback
argument passed to context-manager exit. Compiler catch lowering prepends
call-site nodes once per propagation/frame; bare raise preserves the existing
node and explicit raise adds its location. Exception group subsets share native
traceback identity, while later propagation prepends independent nodes. Existing
JavaScript error rendering retains its legacy array without mutating siblings.
Frame identity survives suspension; code, line, globals, builtins and back-frame
getters are provided. Returned ordinary frames retain their back frame; inactive
generator/coroutine frames have no caller back frame.

Fourteen unchanged CPython 3.14 methods from test_exceptions, test_types, test_sys
and test_exception_group at 18ef0f0cb5278fa6583b753ffaaef7f46e416ab9 plus seven
CPython-checked regressions cover the native descriptor, frame and group contracts.
JavaScript-generated traceback/frame bytecode offsets and frame locals proxies
raise explicit NotImplementedError until those compiler metadata/runtime
increments land. Frame tracing/line jumps, frame clearing, sys._getframe and
traceback formatting modules remain separate work.

Traceback propagation compares persistent Python frame identity across resume,
so a pending error passing through a yielding finally block gains no duplicate
node. TracebackType arguments use CPython's signed C-int bounds; negative stored
line numbers require bytecode line mapping and have an explicit getter guard.

Fresh generator.throw injection resets propagation location so injecting an
exception into its original frame still prepends the current yield location.

Throw and close injections chain against only the generator's own handled state,
not its current caller's inherited state. Existing supplied context is preserved
when the generator has no local handler.

As in _gen_throw/gen_send_ex2, delegation runs first; each generator chains its
own handler only when its frame actually resumes with the resulting error.
A delegate that handles injection does not acquire its outer generator's state.

## Except-star compiler lowering

`stu-dev/compiler/except-star` implements TryStar using codegen_try_star_except's
ordered match/handler/error-accumulation stages and _PyExc_PrepReraiseStar's
metadata comparison and leaf-identity projection. Naked matches are wrapped,
partial groups invoke their actual split method, invalid catch types/group types
and malformed split results are rejected, and reraised leaves preserve the
original hierarchy while newly raised exceptions become siblings. None checks
avoid invoking group truth/equality/hash protocols. Subgroups remain active
during handler execution and suspension; targets and enclosing handled state
are cleaned up on every exit. Except-star return and outward break/continue are
rejected while nested loops and nested functions retain valid control flow.

Try lowering is separated into except, except-star and finally emitters following
CPython. Shared protected-block cleanup unwinds runtime catch targets on nonlocal
exits, fixing ordinary try-body break/continue retaining a stale catch target.
The entire 60-method CPython test_except_star module is retained unchanged, with
only local subTest/fail harness adapters and the actual support mixin copied.
Two unchanged test_grammar methods cover PEP 758 unparenthesized handler types;
two deferred annotation methods rejoin their upstream fixture classes. Two
CPython-checked regressions cover yielding handlers/error accumulation and
normal/starred try-body nonlocal cleanup. All source/tests use CPython 3.14
18ef0f0cb5278fa6583b753ffaaef7f46e416ab9. The existing EOFError builtin is exposed;
BlockingIOError's OSError subclass identity is enabled for upstream hierarchy
matching. Extended OSError errno/filename/characters_written behavior remains
separate exception-runtime work. Python 2 rejects TryStar explicitly.

Ordinary and starred matching share CHECK_EXC_MATCH-style complete tuple
validation and native subtype matching, bypassing metaclass __instancecheck__.
The unchanged upstream invalid-ordinary-matcher test is restored, and a
CPython-checked regression covers metaclass overrides and raising BaseException
itself (previously mistaken for a non-exception class).


### Type unions (PEP 604)

`stu-dev/compiler/type-unions` implements the existing binary-operator path's
runtime contract, following `Objects/unionobject.c` in the pinned CPython 3.14
checkout. The union builder flattens nested unions, converts None to NoneType,
preserves first-occurrence order and separates hashable and unhashable arguments
for equality and hashing. It handles generic aliases and metaclass overrides.
`types.UnionType` exposes readonly arguments and supports class subscription;
Python 3.14's checked builder accepts ordinary non-type arguments as CPython
does, rejecting exact tuples. String arguments explicitly require the pending
ForwardRef implementation. Parameter substitution remains guarded until native
type parameters are added.

`isinstance` and `issubclass` unwrap union arguments in order and invoke native
metaclass checks. Thus `isinstance(1, int | list[int])` succeeds, while reversing
the operands raises the parameterized-generic TypeError. Five unchanged CPython
UnionTests methods cover unhashable metaclasses, changing hashability and custom
instance/subclass checks; three CPython-checked tests select operator, metadata,
ordering, generic alias and invalid cases from the same suite. The broader typing
library, ForwardRef, substitution and serialization remain separate work.

The type-union review added a metaclass regression: freezing, hashing and comparing
unions retain the builder's original entry hashes, and parameter inspection skips
bare classes as `_Py_make_parameters` does. Nine focused cases pass both runtimes.


### Lazy type aliases (PEP 695, nongeneric increment)

`stu-dev/compiler/type-aliases` follows `codegen_typealias_body` and the
TypeAliasBlock traversal: a real annotation-scope closure evaluates the value,
and a native `typing.TypeAliasType` caches its first successful result. Failures
do not poison that cache; `evaluate_value` retains direct live evaluation.
Class aliases capture the class dictionary cell and lexical closures through the
existing annotation lookup machinery. Recursive references remain unevaluated
until access. The lazy closure has CPython's `.format` argument/default and
ordinary/nested code flags; restricted expressions report type-alias diagnostics.

The compiler-adjacent typing module exposes TypeAliasType and native get_args /
get_origin. Generic type parameters, unpacking, serialization and annotationlib
formats still require their corresponding increments; nonempty type_params are
explicitly guarded. Ten unchanged CPython methods and three CPython-checked scope,
cache, recursion, code-metadata and syntax tests pass in both runtimes. Full suite
with this increment and reviewed unions: 3,683 Python 3, 465 Python 2 and 562
execution tests passed before the final alias argument-metadata adjustment; the
focused alias tests pass after it.

Alias review fixes preserve the distinct type-alias restriction for comprehension
assignment expressions and skip alias scopes when qualifying child lambdas.
Constructed aliases use a native constant evaluator with exactly one C-int format
argument, keyword rejection and CPython's constant STRING rendering. Compiled
alias evaluators retain their defaulted positional-only `.format` parameter.
Fourteen focused cases pass both runtimes, including the review regressions.


### TypeVar runtime and generic substitution foundation

`stu-dev/compiler/type-variables` adds native TypeVar and NoDefault objects before
compiler type-parameter lowering. It follows `Objects/typevarobject.c` for
identity, variance, bounds/constraints/defaults, evaluator access, instance and
subclass rejection, and substitution/default preparation. The value getters
retain separate evaluator functions so the next compiler increment can create
actual lazy bound/default closures. String bounds/substitutions still explicitly
require ForwardRef support. ParamSpec, TypeVarTuple and generic compiler syntax
remain subsequent increments.

GenericAlias's former substitution stub is replaced with `_Py_make_parameters`
and `_Py_subs_parameters`-shaped ordered traversal: skip bare classes, discover
identity-distinct parameters, prepare defaults, recurse into nested aliases and
list/tuple arguments, then invoke substitution protocols. Union parameter
inspection/substitution uses the same implementation. Nineteen unchanged CPython
TypeVar/union/generic-alias methods and two CPython-checked default/evaluator and
substitution regressions pass (21 cases in both runtimes).

Type-variable review fixes reject preparation when the parameter is absent,
normalize non-tuple results before each subsequent preparation hook, and honor
list-subclass iteration in discovery and substitution. Twenty-two focused cases
pass both runtimes. The full foundation suite before these protocol fixes passed
3,705 Python 3, 465 Python 2 and 562 execution tests.

### Generic functions and aliases (TypeVar increment)

`stu-dev/compiler/type-parameters` follows CPython's type-parameter wrapper scope
for generic functions and aliases. Decorators and ordinary argument defaults are
evaluated outside it; parameter bindings enclose the actual function and its lazy
annotations. Bounds, constraints and defaults get separate lazy evaluator scopes,
with class visibility, successful-value caching and failed-evaluation retry.
Functions expose mutable tuple-only `__type_params__`; generic aliases expose
parameters and specialize through GenericAlias. Nonlocal binding of type
parameters and forbidden expressions in annotation scopes are rejected.

Twenty-seven complete CPython 3.14 `test_type_params.py` methods are preserved,
with small run_code/check_syntax_error/subTest harness adapters. Three additional
CPython-checked cases cover default/decorator ordering, evaluator metadata,
recursive bounds and constructor/default-order validation. All 30 pass in both
interpreters. Generic classes, ParamSpec, TypeVarTuple, ForwardRef and annotation
formats above VALUE_WITH_FAKE_GLOBALS remain separate increments with explicit
unsupported guards where their compiler paths are not implemented.

### Variadic type parameters

`stu-dev/compiler/variadic-parameters` adds native ParamSpec, ParamSpecArgs,
ParamSpecKwargs, TypeVarTuple and Unpack objects. Function/alias lowering now
handles all three parameter kinds and lazy defaults, including starred defaults.
CPython's ParamSpec and TypeVarTuple preparation helpers are ported directly from
`Lib/typing.py`. GenericAlias supports starred iteration, finite unpacking and
variadic nested substitution, including arbitrary-length tuples. Its attribute
exception list now retains `__class__`, fixing alias/type misclassification.

Twenty-three complete upstream methods from `test_typing.py`,
`test_type_params.py` and `test_genericalias.py`, plus three CPython-checked
compiler/substitution regressions, pass in both runtimes. Generic classes,
Concatenate, Callable typing aliases, ForwardRef and serialization remain later
work; string type arguments continue to raise an explicit unsupported error.

### Generic class parameter scopes

`stu-dev/compiler/generic-classes` creates the CPython parameter wrapper around
base expressions and the class body, appends the implicit Generic base, and
stores `__type_params__` before executing the body. Class/method/alias closures
retain the declared parameters, while decorators evaluate outside the wrapper.
Selective parameter mangling extends into base expressions and nested scopes;
ordinary class mangling is restored on exit. Leading underscores are stripped
from private class names, and context metadata stays off interned Python strings.

The Generic runtime and user-defined `_GenericAlias` live in Python, with CPython
collection, default preparation and substitution methods. They retain mutable
alias metadata, CPython specialization caching, defaults, variadic parameters
and original class tracking. Checked unions validate Python typing aliases
through the same typing helper as CPython. Public closure metadata maps hidden
compiler bindings to CPython names while preserving the JavaScript binding ABI. The compiler caches the Generic reference and constructs its alias
directly, as CPython's intrinsic does. Type-level `__type_params__` lookup is local
to the class; conflicting bases report CPython's distinct remaining MRO heads.

Sixty-three upstream `test_type_params.py` methods pass (61 bodies unchanged, two
with only their local make_base import path redirected), plus four CPython-checked
regressions for specialization, definition ordering, alias metadata, mangling and
reconstructing a class body from its closure cells. All 67 pass both interpreters. Callable/Concatenate, ForwardRef, annotation formats
and serialization remain separate compiler-adjacent work.

### Concatenate parameter expressions

`stu-dev/compiler/concatenate` ports CPython's special-form and Concatenate alias
classes, including cached subscription, nested parameter substitution and final/
non-iterable behavior. ParamSpec substitution recognizes Concatenate expressions,
including those created inside generic classes and lazy type aliases. Four
upstream ConcatenateTests methods are unchanged, plus one CPython-checked compiler
regression. Callable-dependent methods follow with Callable support.

### Abstract classes for compiler-produced protocols

`stu-dev/compiler/abstract-classes` ports CPython's Python ABCMeta implementation
and public abstract decorators/update helper. Native type/object paths implement
local `__abstractmethods__` lookup and abstract-instantiation checks; property,
classmethod and staticmethod descriptors expose wrapped abstract status. Direct
subclass introspection and ABC caches keep weak references to classes rather than
retaining generated classes. These APIs require host WeakRef support; ordinary
class creation remains available on older hosts.

Thirty-one complete upstream `test_abc.py` TestABC methods pass in both runtimes,
with only assertion/subTest harness helpers adapted, plus a CPython-checked native
lookup/Unicode diagnostic regression (32 focused cases). inspect.isabstract-dependent
methods remain deferred. This layer supplies the foundation for Callable and
compiler-produced generator/coroutine/async iterator ABC protocols.

### Compiler-produced protocol ABCs

`stu-dev/compiler/abc-protocols` turns collections into a package without changing
its existing native module implementation, and adds the compiler-related protocol
classes from CPython `_collections_abc.py`: Callable, Iterable/Iterator/Generator,
Awaitable/Coroutine and AsyncIterable/AsyncIterator/AsyncGenerator. Abstract mixin
methods and structural subclass checks are preserved. Compiler-produced native
types register with the corresponding ABCs. GenericAlias allocation now retains
subclasses, enabling the CPython collections.abc Callable alias implementation.
Direct type() factories select the most derived metaclass, so dynamically created
ABC subclasses receive their abstract-method set. Native alias representations
read class attributes normally; ParamSpec conversion preserves tuple parameter
expressions instead of validating them as individual type arguments.

Seven complete upstream test_collections methods and their validation helpers
are unchanged, plus a CPython-checked alias/subclass substitution regression.
Awaitable's upstream GC-dependent cleanup test remains deferred.

### Callable aliases and parameter-expression substitution

`stu-dev/compiler/callable` ports CPython's typing Callable alias classes and
special generic alias base, with Any/NoReturn, List and Tuple as direct prerequisites
of the unchanged Callable tests. It restores the CPython Callable argument
flattening branch, alias MRO behavior and get_args unflattening contract for
both typing.Callable and collections.abc.Callable. Subscriptions preserve
cached mutable metadata and nested ParamSpec/Concatenate/TypeVarTuple expressions.

Eighteen complete BaseCallableTests methods run against both alias variants,
plus CPython's consistency method and one compiler/type-alias regression (38
cases). The complete Concatenate valid_uses method is restored. Type-hint evaluation, weakref and pickle
methods remain deferred with those runtime facilities.

### Public AST objects and source-to-AST compilation

`stu-dev/compiler/ast-objects` exposes the CPython 3.14 ASDL schema, including
modern type parameters, pattern nodes and template nodes. `compile` with
PyCF_ONLY_AST and `ast.parse` return mutable Python AST objects with typed fields,
source locations, Python-valued constants and CPython default contexts/lists.
Traversal, transformation, literal evaluation, dumps and location helpers are
ported from CPython ast.py. AST representations follow Python-ast.c's depth and
sequence abbreviation rules. Fourteen complete upstream test_ast methods plus one
modern parser/value regression pass in both runtimes (15 cases).

Compilation of edited ASTs, statement unparsing, versioned grammars, optimized
ASTs, the AST-only func_type grammar, type comments and constructor deprecation
warnings follow separately. Unsupported func_type parsing raises an explicit
NotImplementedError. Review corrected typed exception-handler conversion and
shared parser operator/default-context identities.

### Compilation and validation of edited ASTs

`stu-dev/compiler/ast-compilation` converts public Python ASTs into the same
modern ASDL representation used by source parsing, then runs the existing symbol
table and compiler. Conversion checks field/sequence types, integer ranges,
required fields and immutable Constant values. Procedural semantic validation
follows CPython Python/ast.c for contexts, arguments, comprehensions, bodies,
imports, annotations and generic type parameters. Tuple/frozenset constants use
a closure retaining the Python payloads. Conversion reads fields once, bypasses
list/int subclass hooks like CPython, and checks for sequence size changes.
Semantic validation uses the converted snapshot. PyCF_ONLY_AST copies nodes while
retaining their immutable Constant payloads, as
CPython does, without applying semantic validation.

Thirty-seven complete upstream ASTValidatorTests methods and their compile
harness are unchanged, plus one edited-generic-function/immutable-constant
regression and a conversion/identity regression (39 cases), passing both runtimes. Pattern validation follows with
match compilation; whole-stdlib validation follows broader stdlib support.
