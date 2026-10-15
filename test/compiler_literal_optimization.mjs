import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { resolve } from "node:path";

createRequire(import.meta.url)(resolve(process.argv[2] || "dist/skulpt.min.js"));
const { Sk } = globalThis;
Sk.configure({ __future__: Sk.python3, execLimit: null, yieldLimit: null });
function compile(source) {
    Sk.resetCompiler();
    return Sk.compile(source, "literals.py", "exec", true).code;
}
for (const expr of ["x in [1, 2, 3]", "x not in ['a', 'b']", "x in [None, True, False]", "x in [(1, 2), 3]"]) {
    const code = compile(`def f(x):\n    return ${expr}\n`);
    assert.ok(!code.includes("new Sk.builtins['list']"), "Temporary list should be pooled: " + expr);
    assert.ok(code.includes("new Sk.builtin.tuple(["), "Expected tuple constant: " + expr);
}
assert.ok(!compile("def f():\n    for x in [1, 2, 3]:\n        pass\n").includes("new Sk.builtins['list']"));
for (const expr of ["[x for x in [1, 2, 3]]", "(x for x in [1, 2, 3])"]) {
    // List comprehensions allocate the result list, but the input is a constant tuple.
    assert.ok(compile(`def f():\n    return ${expr}\n`).includes("new Sk.builtin.tuple(["));
}
// An intermediate comparison operand remains observable by the next comparison.
for (const expr of ["x in [1, 2] == [1, 2]", "x in [1, []]", "x in [make(), 2]", "x in [*items, 2]", "[1, 2]"]) {
    assert.ok(compile(`def f(x):\n    return ${expr}\n`).includes("new Sk.builtins['list']"), "Keep observable/dynamic lists: " + expr);
}
console.log("Compiler literal pooling checks passed");
