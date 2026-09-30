// Test the published-style optimizer through both existing Skulpt compiler paths.
// No runtime rollout: the compiler boundary is wrapped only inside this harness.
import assert from "node:assert/strict";
import fs from "node:fs";
import { createRequire } from "node:module";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";
import { spawnSync } from "node:child_process";

const args = process.argv.slice(2).filter((arg) => arg !== "--direct");
const [parserPath, optimizerPath, runtimePath, stdlibPath] = args;
assert.equal(
  args.length,
  4,
  "Usage: node test/ast_optimizer.mjs <parser> <optimizer> <runtime> <stdlib> [--direct]",
);
const direct = process.argv.includes("--direct");
const require = createRequire(import.meta.url);
require(resolve(runtimePath));
require(resolve(stdlibPath));
const { Sk } = globalThis;
const { parseModule } = await import(pathToFileURL(resolve(parserPath)).href);
const { optimizeAST } = await import(
  pathToFileURL(resolve(optimizerPath)).href
);
const python = process.env.PYTHON314 || "python3.14";
const version = spawnSync(
  python,
  ["-c", "import sys; print(sys.version_info[:3])"],
  { encoding: "utf8" },
);
assert.equal(version.status, 0, version.stderr || String(version.error));
assert.equal(
  version.stdout.trim(),
  "(3, 14, 3)",
  "Use the pinned CPython oracle",
);
let enabled = false;
if (direct) {
  const original = Sk.parseModule;
  Sk.parseModule = (source, filename) => {
    const tree = original(source, filename);
    return enabled && Sk.__future__.python3 ? optimizeAST(tree) : tree;
  };
}

function configure(optimize, python2 = false) {
  enabled = optimize;
  let output = "";
  Sk.configure({
    ...(!direct
      ? {
          sourceParser: (source, options) => {
            const tree = parseModule(source, options);
            return enabled && options.pythonVersion === 3
              ? optimizeAST(tree)
              : tree;
          },
        }
      : {}),
    __future__: python2 ? Sk.python2 : Sk.python3,
    read: (name) =>
      Sk.builtinFiles.files[name] ?? fs.readFileSync(name, "utf8"),
    output: (text) => {
      output += text;
    },
    yieldLimit: null,
    execLimit: null,
  });
  return () => output;
}

async function run(source, optimize, python2 = false) {
  const output = configure(optimize, python2);
  await Sk.misceval.asyncToPromise(() =>
    Sk.importMainWithBody("optimizer_test", false, source + "\n", true),
  );
  return output();
}

const programs = [
  "print(1 + 2 * 3, 9007199254740993 + 2, 2 ** 64, -7 // 3, -7 % 3)",
  "print(-7.5 % 2.0, 0.0 / -2.0, -0.0)",
  "print('a' + 'b', 'ab' * 3, 'x' * -3, b'abc' + b'd', b'x' * 2)",
  "print((1, (2, 3)) * 2, ((1, 2) + (3,))[1], b'abc'[1])",
  "'module' + 'doc'\nclass C:\n    'class' * 2\n    def f(self):\n        ('function',)[0]\n        return 1 + 2\nprint(C.__doc__, C.f.__doc__, C().f())",
  "'module doc'\ndef f():\n    'function doc'\n    return 1 + 2\nprint(__doc__, f.__doc__, f())",
  "def f():\n    print('called')\n    return 1\nprint(False and f(), True or f())",
  "def f(x: 1 + 2) -> 'a' + 'b':\n    return 1 + 2\nprint(f.__annotations__['x'], f.__annotations__['return'], f(0))",
  "x = [0, 1, 2, 3]\nx[1 + 2] = 5\nprint(x)",
  "def f():\n    print('called')\n    return 1\nprint((f(), 2)[1])",
  "print(eval('1 + 2'))\nexec('x = 2 * 3')\nprint(x)",
  "for expression in ['1 / 0', '1 // 0', '1 % 0', '1 << -1', \"'x'[2]\"]:\n    try: eval(expression)\n    except Exception as e: print(type(e).__name__)",
];
for (const source of programs) {
  const reference = spawnSync(python, ["-c", source], { encoding: "utf8" });
  assert.equal(reference.status, 0, reference.stderr);
  assert.equal(
    await run(source, false),
    reference.stdout,
    `Unoptimized compiler: ${source}`,
  );
  assert.equal(
    await run(source, true),
    reference.stdout,
    `Optimized compiler: ${source}`,
  );
}
// Existing Skulpt uses Math.floor(x/y), unlike CPython's float_divmod.
// Record the runtime defect; folded constants use the verified Python value.
assert.equal(await run("print(1.0 // 0.1)", false), "10.0\n");
assert.equal(await run("print(1.0 // 0.1)", true), "9.0\n");
for (const optimize of [false, true]) {
  await assert.rejects(
    () => run("False and (bound := 1 + 2)", optimize),
    (error) =>
      error instanceof Sk.builtin.SyntaxError &&
      error.toString().includes("NamedExpr is not supported"),
  );
}
// Legacy division and explicit long constants never enter the Python 3 pass.
const legacy = "print 1 / 2, 1L + 2L, type(1L).__name__";
assert.equal(await run(legacy, true, true), await run(legacy, false, true));
assert.equal(await run(legacy, true, true), "0 3 long\n");

function compiled(optimize) {
  configure(optimize);
  Sk.resetCompiler();
  return Sk.compile("answer = 1 + 2\n", "fold.py", "exec", true).code;
}
const before = compiled(false);
const after = compiled(true);
assert.match(before, /numberBinOp/);
assert.doesNotMatch(after, /numberBinOp/);
console.log(
  JSON.stringify(
    {
      compiler: direct ? "direct" : "adapter",
      cpythonPrograms: programs.length,
      python2: "passed",
      knownRuntimeDifference:
        "Unoptimized Skulpt 1.0 // 0.1 == 10.0; CPython and folded value == 9.0",
      constantAdd: {
        beforeBytes: Buffer.byteLength(before),
        afterBytes: Buffer.byteLength(after),
      },
    },
    null,
    2,
  ),
);
