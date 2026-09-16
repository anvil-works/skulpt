// Real compiler/execution comparisons. The parser bundle is supplied explicitly
// until package publication and consumer rollout are decided.
import assert from "node:assert/strict";
import fs from "node:fs";
import { createRequire } from "node:module";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";
import { spawnSync } from "node:child_process";

const require = createRequire(import.meta.url);
require(resolve(process.argv[3] || "dist/skulpt.js"));
require("../dist/skulpt-stdlib.js");
const { Sk } = globalThis;
const parserPath = process.argv[2];
if (!parserPath) throw new Error("Usage: node test/structural_parser.mjs <parser-core-bundle> [skulpt-bundle]");
const { parseModule } = await import(pathToFileURL(resolve(parserPath)).href);
const python = process.env.PYTHON314 || "python3.14";
const version = spawnSync(python, ["-c", "import sys; print(sys.version_info[:3])"], { encoding: "utf8" });
assert.equal(version.status, 0, version.stderr || String(version.error));
assert.equal(version.stdout.trim(), "(3, 14, 3)", "Use the pinned CPython oracle");
let count = 0;

async function run(source, adapter, python2 = false, flags = {}) {
    let output = "";
    Sk.configure({
        sourceParser: adapter ? parseModule : null,
        syspath: ["test"],
        __future__: { ...(python2 ? Sk.python2 : Sk.python3), ...flags },
        read: (name) => Sk.builtinFiles.files[name] ?? fs.readFileSync(name, "utf8"),
        output: (text) => { output += text; },
        yieldLimit: null,
        execLimit: null
    });
    await Sk.misceval.asyncToPromise(() => Sk.importMainWithBody("adapter_test", false, source + "\n", true));
    return output;
}

const programs = [
    ["literals", "print((9007199254740993 + 2, -0.0, 2j, b'abc', True, None, ...))"],
    ["control flow", "x = 0\nfor n in range(6):\n    if n == 2: continue\n    x += n\nelse: x += 1\nwhile x > 10:\n    x -= 1\nprint(x, not x, x in [10])"],
    ["functions and closures", "def outer(x):\n    def f(y=3, *, z=4):\n        return x + y + z\n    return f\nprint(outer(2)(z=5))"],
    ["nonlocal", "def outer():\n    x = 1\n    def update():\n        nonlocal x\n        x += 2\n    update()\n    return x\nprint(outer())"],
    ["class and docstrings", "'module doc'\nclass C:\n    'class doc'\n    def f(self, x):\n        'function doc'\n        return x + 1\nprint(__doc__, C.__doc__, C.f.__doc__, C().f(4))"],
    ["comprehensions", "print([x*x for x in range(5) if x % 2])\nprint(sorted({x for x in [3,1,3]}))\nprint(sorted({x: x+1 for x in range(3)}.items()))"],
    ["generators", "def g():\n    yield 1\n    yield from [2, 3]\nprint(list(g()))"],
    ["mixed slices", "class C:\n    def __getitem__(self, key):\n        return (key[0], key[1].start, key[1].stop, key[1].step)\nprint(C()[1, 2:8:2])\nprint([1,2,3,4][1:3])"],
    ["exception binding", "try:\n    raise ValueError('bad')\nexcept ValueError as e:\n    print(str(e))\nfinally:\n    print('done')"],
    ["context manager", "class C:\n    def __enter__(self): return 3\n    def __exit__(self, *args): print('exit')\nwith C() as x:\n    print(x)"],
    ["fstrings", "value = 12\nprint(f'{value!r:>4}')"],
    ["eval and exec", "x = 5\nprint(eval('x + 2'))\nexec('x += 3')\nprint(x)"],
    ["imports", "from math import sqrt\nprint(sqrt(16))"],
    ["relative import", "from structural_parser_package import answer\nprint(answer)"],
    ["annotations", "x: int = 3\ndef f(a: int) -> int:\n    return a\nprint(f(x), f.__annotations__['a'] is int)"],
];
for (const [name, source] of programs) {
    const reference = spawnSync(python, ["-c", source], {
        encoding: "utf8", env: { ...process.env, PYTHONPATH: resolve("test") }
    });
    assert.equal(reference.status, 0, `${name}: ${reference.stderr}`);
    const baseline = await run(source, false);
    assert.equal(baseline, reference.stdout, `${name}: existing runtime vs CPython`);
    assert.equal(await run(source, true), reference.stdout, `${name}: adapter vs CPython`);
    count++;
}

// Newly accepted spelling, unchanged runtime operations. Exercise eval's parser gate too.
const modern = "x = 3\nprint(eval(\"f'{x=}'\"))";
const modernReference = spawnSync(python, ["-c", modern], { encoding: "utf8" });
assert.equal(modernReference.status, 0, modernReference.stderr);
assert.equal(await run(modern, true), modernReference.stdout);
count++;

// Compatibility mode must not introduce historical Python 2 syntax restrictions.
const py2Modern = "x: int = 3\nprint(x)";
const py2ModernReference = spawnSync(python, ["-c", py2Modern], { encoding: "utf8" });
assert.equal(py2ModernReference.status, 0, py2ModernReference.stderr);
assert.equal(await run(py2Modern, true, true), py2ModernReference.stdout);
count++;

for (const [name, source, flags] of [
    ["print and long", "print 0755L,\nprint type(1L).__name__", {}],
    ["legacy raise", "try:\n    raise ValueError, 'bad'\nexcept ValueError, e:\n    print str(e)", {}],
    ["configured print", "print(0755L)\nprint(1, 2)", { print_function: true }],
    ["legacy async names", "async = 2\ndef await(x): return x + async\nprint await(3)", {}],
    ["modern-compatible syntax", "print([x*x for x in range(3)])", { print_function: true }],
]) {
    assert.equal(await run(source, true, true, flags), await run(source, false, true, flags), name);
    count++;
}

// Both frontends must retain suspension through the existing compiler/runtime.
Sk.builtins.adapter_pause = new Sk.builtin.func(() =>
    Sk.misceval.promiseToSuspension(Promise.resolve(new Sk.builtin.int_(7))));
for (const adapter of [false, true]) {
    assert.equal(await run("print(adapter_pause() + 1)", adapter), "8\n");
}
delete Sk.builtins.adapter_pause;
count++;

for (const source of [
    "match x:\n    case 1: pass",
    "def f[T](): pass",
    "def f(x, /): pass",
    "x = (y := 1)",
    "try:\n    pass\nexcept* ValueError: pass",
    "x = t'{value}'",
]) {
    Sk.configure({ sourceParser: parseModule, __future__: { ...Sk.python3 } });
    const saved = Sk.__future__;
    assert.throws(() => Sk.compile(source, "guard.py", "exec", true), (e) =>
        e instanceof Sk.builtin.SyntaxError && e.toString().includes("not supported by the Skulpt compiler"));
    assert.equal(Sk.__future__, saved, "Failed compilation must restore configured flags");
    count++;
}
for (const source of ["return 1", "def f(x, x): pass", "x = (", "f(x=1, x=2)", "class C(x=1, x=2): pass"]) {
    const oracle = spawnSync(python, ["-c", "import sys; compile(sys.stdin.read(), 'error.py', 'exec')"],
        { input: source, encoding: "utf8" });
    assert.notEqual(oracle.status, 0);
    assert.match(oracle.stderr, /SyntaxError/);
    for (const adapter of [false, true]) {
        Sk.configure({ sourceParser: adapter ? parseModule : null, __future__: { ...Sk.python3 } });
        const saved = Sk.__future__;
        assert.throws(() => Sk.compile(source, "error.py", "exec", true), (e) => e instanceof Sk.builtin.SyntaxError);
        assert.equal(Sk.__future__, saved);
    }
    count++;
}
Sk.configure({ sourceParser: parseModule, __future__: { ...Sk.python3 } });
assert.throws(() => Sk.compile("x = (", "location.py", "exec", true), (e) =>
    e instanceof Sk.builtin.SyntaxError && e.$filename.v === "location.py" &&
    e.$lineno.v === 1 && e.$offset.v === 5 && e.$text.v.includes("x = ("));
assert.throws(() => Sk.compile("if True:\npass", "indent.py", "exec", true),
    (e) => e instanceof Sk.builtin.IndentationError);
assert.throws(() => Sk.compile("x = '\\N{SNOWMAN}'", "names.py", "exec", true),
    (e) => e.name === "UnicodeNameDatabaseRequired" && !(e instanceof Sk.builtin.SyntaxError));
assert.ok(Sk.compile("debugger", "debugger.py", "exec", true).code.includes("debugger;"));
count += 4;
console.log(`${count} structural parser execution/error comparisons passed`);
