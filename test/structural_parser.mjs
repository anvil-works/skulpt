// Compare direct-AST execution with the compatibility checkpoint and CPython.
import assert from "node:assert/strict";
import fs from "node:fs";
import { createRequire } from "node:module";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";
import { spawnSync } from "node:child_process";
import vm from "node:vm";

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
const oracleBundle = process.argv[4];
assert.ok(oracleBundle, "Supply the compatibility checkpoint bundle as the third argument");
const oracleContext = vm.createContext({console, setTimeout, clearTimeout, TextEncoder, TextDecoder});
vm.runInContext(fs.readFileSync(resolve(oracleBundle), "utf8"), oracleContext);
const baseline = oracleContext.Sk;
baseline.builtinFiles = Sk.builtinFiles;
let count = 0;

async function run(source, adapter, python2 = false, flags = {}) {
    const runtime = adapter ? Sk : baseline;
    let output = "";
    runtime.configure({
        ...(runtime === baseline ? { sourceParser: parseModule } : {}),
        syspath: ["test"],
        __future__: { ...(python2 ? runtime.python2 : runtime.python3), ...flags },
        read: (name) => runtime.builtinFiles.files[name] ?? fs.readFileSync(name, "utf8"),
        output: (text) => { output += text; },
        yieldLimit: null,
        execLimit: null
    });
    await runtime.misceval.asyncToPromise(() => runtime.importMainWithBody("adapter_test", false, source + "\n", true));
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
    ["fstring conversions", "value = 'café'\nprint(f'{value!r} | {value!a} | {value!s:>8}')"],
    ["continue without finally", "def f():\n    count = 0\n    for i in range(3):\n        try:\n            count += 1\n            continue\n            count += 10\n        except:\n            raise\n    return count\nprint(f())"],
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
    assert.equal(await run(source, true), reference.stdout, `${name}: direct AST vs CPython`);
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

// Both compiler versions must retain suspension through the existing compiler/runtime.
for (const runtime of [Sk, baseline]) runtime.builtins.adapter_pause = new runtime.builtin.func(() =>
    runtime.misceval.promiseToSuspension(Promise.resolve(new runtime.builtin.int_(7))));
for (const adapter of [false, true]) {
    assert.equal(await run("print(adapter_pause() + 1)", adapter), "8\n");
}
delete Sk.builtins.adapter_pause;
delete baseline.builtins.adapter_pause;
count++;

// Newly implemented syntax compares with CPython; the checkpoint predates it.
for (const [name, source] of [
    // CPython Lib/test/test_type_params.py: test_name_non_collision_02.
    ["genericfunction", "def func[A](A): return A\nprint(func(1), func.__type_params__[0].__name__)"],
    ["namedexpr", "x = (y := 1)\nprint(x, y)"],
    // CPython Lib/test/test_except_star.py: test_match_single_type and doSplitTestNamed.
    ["exceptstar", "try:\n    raise ExceptionGroup('test2', [ValueError('V1'), ValueError('V2')])\nexcept* ValueError as e:\n    print([str(exc) for exc in e.exceptions])"],
]) {
    const reference = spawnSync(python, ["-c", source], { encoding: "utf8" });
    assert.equal(reference.status, 0, `${name}: ${reference.stderr}`);
    Sk.configure({ __future__: { ...Sk.python3 } });
    const saved = Sk.__future__;
    Sk.compile(source, `${name}.py`, "exec", true);
    assert.equal(Sk.__future__, saved, "Successful compilation must restore configured flags");
    assert.equal(await run(source, true), reference.stdout, `${name}: direct AST vs CPython`);
    count++;
}

for (const source of [
    "match x:\n    case 1: pass",
    "x = t'{value}'",
]) {
    Sk.configure({ __future__: { ...Sk.python3 } });
    const saved = Sk.__future__;
    assert.throws(() => Sk.compile(source, "guard.py", "exec", true), (e) =>
        e instanceof Sk.builtin.SyntaxError && e.toString().includes("not supported by the Skulpt compiler"));
    assert.equal(Sk.__future__, saved, "Failed compilation must restore configured flags");
    count++;
}
for (const source of ["return 1", "def f(x, x): pass", "x = (", "f(x=1, x=2)", "class C(x=1, x=2): pass", "if False:\n    f(x=1, x=2)", "if False:\n    class C(x=1, x=2): pass",
    "if False:\n    def f(*, x=g(a=1, a=2)): pass",
    "if False:\n    f = lambda *, x=g(a=1, a=2): x",
    "if False:\n    x = {g(a=1, a=2) for i in []}",
    "if False:\n    x = {i: g(a=1, a=2) for i in []}"]) {
    const oracle = spawnSync(python, ["-c", "import sys; compile(sys.stdin.read(), 'error.py', 'exec')"],
        { input: source, encoding: "utf8" });
    assert.notEqual(oracle.status, 0);
    assert.match(oracle.stderr, /SyntaxError/);
    for (const adapter of [false, true]) {
        const runtime = adapter ? Sk : baseline;
        runtime.configure({ ...(runtime === baseline ? { sourceParser: parseModule } : {}), __future__: { ...runtime.python3 } });
        const saved = runtime.__future__;
        assert.throws(() => runtime.compile(source, "error.py", "exec", true), (e) => e instanceof runtime.builtin.SyntaxError);
        assert.equal(runtime.__future__, saved);
    }
    count++;
}
Sk.configure({ __future__: { ...Sk.python3 } });
assert.throws(() => Sk.compile("x = (", "location.py", "exec", true), (e) =>
    e instanceof Sk.builtin.SyntaxError && e.$filename.v === "location.py" &&
    e.$lineno.v === 1 && e.$offset.v === 5 && e.$text.v.includes("x = ("));
assert.throws(() => Sk.compile("if True:\npass", "indent.py", "exec", true),
    (e) => e instanceof Sk.builtin.IndentationError);
assert.throws(() => Sk.compile("x = '\\N{SNOWMAN}'", "names.py", "exec", true),
    (e) => e.name === "UnicodeNameDatabaseRequired" && !(e instanceof Sk.builtin.SyntaxError));
assert.ok(Sk.compile("debugger", "debugger.py", "exec", true).code.includes("debugger;"));
count += 4;
// AST byte columns must not leak into the existing JS traceback/debugger contract.
for (const text of ["雪", "😀", "e\u0301"]) {
    const source = `x = "${text}"; location_pause(); missing`;
    const missingColumn = source.indexOf("missing");
    const callColumn = source.indexOf("location_pause");
    const reference = spawnSync(python, ["-c", `import ast, json, sys
source = sys.stdin.read()
try:
    ast.parse(source + " =")
except SyntaxError as e:
    print(json.dumps([ast.parse(source).body[-1].col_offset, e.offset]))`], { input: source, encoding: "utf8" });
    assert.equal(reference.status, 0, reference.stderr);
    const [astColumn, errorOffset] = JSON.parse(reference.stdout);
    Sk.configure({ __future__: { ...Sk.python3 } });
    const ast = Sk.parseModule(source, "locations.py");
    assert.equal(ast.body.at(-1).col_offset, astColumn);
    assert.throws(() => Sk.compile(source + " =", "locations.py", "exec", true),
        e => e instanceof Sk.builtin.SyntaxError && e.$offset.v === errorOffset);
    for (const runtime of [baseline, Sk]) {
        const breakpoints = [], debugStops = [], promiseStops = [];
        function column(suspension) {
            while (suspension.$colno === undefined && suspension.child) suspension = suspension.child;
            return suspension.$colno;
        }
        // The checkpoint's default frontend supplies the pre-migration JS locations.
        runtime.configure({ ...(runtime === baseline ? { sourceParser: null } : {}), __future__: { ...runtime.python3 }, debugging: true,
            breakpoints: (_filename, _line, column) => { breakpoints.push(column); return true; } });
        runtime.builtins.location_pause = new runtime.builtin.func(() =>
            runtime.misceval.promiseToSuspension(Promise.resolve(runtime.builtin.none.none$)));
        try {
            await assert.rejects(runtime.misceval.asyncToPromise(() =>
                runtime.importMainWithBody("locations", false, source, true), {
                "Sk.debug": suspension => {
                    debugStops.push(column(suspension));
                    return Promise.resolve(suspension.resume());
                },
                "Sk.promise": suspension => { promiseStops.push(column(suspension)); return null; },
            }), error => error instanceof runtime.builtin.NameError && error.traceback.at(-1).colno === missingColumn);
            assert.deepEqual(breakpoints, [0, callColumn, missingColumn]);
            assert.deepEqual(debugStops, breakpoints);
            assert.deepEqual(promiseStops, [callColumn]);
        } finally {
            delete runtime.builtins.location_pause;
            runtime.configure({ debugging: false, breakpoints: () => false });
        }
    }
    count++;
}
console.log(`${count} structural parser execution/error comparisons passed`);
