// Fresh-process comparison of installed original, adapter and direct-AST builds.
import assert from "node:assert/strict";
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { createHash } from "node:crypto";
import { createRequire } from "node:module";
import { spawnSync } from "node:child_process";
import { cpus, arch, platform, release, tmpdir, totalmem } from "node:os";
import { resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { gzipSync, brotliCompressSync } from "node:zlib";

const args = process.argv.slice(2);
const option = (flag, fallback) =>
  args.includes(flag) ? args[args.indexOf(flag) + 1] : fallback;
const quantile = (values, fraction) =>
  [...values].sort((a, b) => a - b)[Math.ceil(values.length * fraction) - 1];
const hash = (bytes) => createHash("sha256").update(bytes).digest("hex");
function measure(operation) {
  for (let i = 0; i < 10; i++) operation();
  const trial = performance.now();
  for (let i = 0; i < 5; i++) operation();
  const iterations = Math.max(
    1,
    Math.min(1000, Math.ceil(25 / ((performance.now() - trial) / 5))),
  );
  const samplesMs = [],
    latencySamplesMs = [];
  for (let batch = 0; batch < 9; batch++) {
    const start = performance.now();
    for (let i = 0; i < iterations; i++) {
      const begin = performance.now();
      operation();
      latencySamplesMs.push(performance.now() - begin);
    }
    samplesMs.push((performance.now() - start) / iterations);
  }
  return {
    iterations,
    samplesMs,
    latencySamplesMs,
    medianMs: quantile(samplesMs, 0.5),
    p95Ms: quantile(latencySamplesMs, 0.95),
  };
}
if (args.includes("--worker")) {
  const { engine, cases, validation, stdlib, executeOnly, phase } = JSON.parse(
    readFileSync(option("--input"), "utf8"),
  );
  global.gc();
  const heapBefore = process.memoryUsage().heapUsed;
  const start = performance.now();
  createRequire(import.meta.url)(engine.path);
  const { Sk } = globalThis;
  const parser = engine.parser
    ? (await import(pathToFileURL(engine.parser).href)).parseModule
    : null;
  const optimizeAST = engine.optimizer
    ? (await import(pathToFileURL(engine.optimizer).href)).optimizeAST
    : null;
  if (executeOnly) createRequire(import.meta.url)(stdlib);
  if (optimizeAST && engine.kind === "direct") {
    const parse = Sk.parseModule;
    Sk.parseModule = (source, filename) => {
      const tree = parse(source, filename);
      return Sk.__future__.python3 ? optimizeAST(tree) : tree;
    };
  }
  Sk.configure({
    __future__: Sk.python3,
    ...(engine.kind === "adapter"
      ? {
          sourceParser: optimizeAST
            ? (source, options) => {
                const tree = parser(source, options);
                return options.pythonVersion === 3 ? optimizeAST(tree) : tree;
              }
            : parser,
        }
      : {}),
    output: () => {},
    ...(executeOnly
      ? {
          read: (name) => {
            assert.ok(
              name in Sk.builtinFiles.files,
              "Missing standard library source: " + name,
            );
            return Sk.builtinFiles.files[name];
          },
        }
      : {}),
    execLimit: null,
    yieldLimit: null,
  });
  const loadMs = performance.now() - start;
  global.gc();
  const loadHeapBytes = process.memoryUsage().heapUsed - heapBefore;
  if (validation && !executeOnly) createRequire(import.meta.url)(stdlib);
  const results = [];
  const sourceToAST = (source) => {
    if (engine.kind === "direct") return Sk.parseModule(source, "benchmark.py");
    if (engine.kind === "adapter")
      return Sk.parseCompilerModule(source, "benchmark.py").ast;
    const parsed = Sk.parse("benchmark.py", source);
    return Sk.astFromParse(parsed.cst, "benchmark.py", parsed.flags);
  };
  const compile = (source) => {
    Sk.resetCompiler();
    return Sk.compile(source, "benchmark.py", "exec", true);
  };
  const executable = (source) => {
    Sk.resetCompiler();
    const compiled = Sk.compile(source, "benchmark.py", "exec", false);
    const callable = Sk.global.eval(compiled.code);
    return () => callable({ __name__: new Sk.builtin.str("benchmark") });
  };
  for (const item of cases) {
    if (validation === "compile") {
      sourceToAST(item.source);
      const compiled = compile(item.source);
      results.push({
        name: item.name,
        compiledSha256: hash(compiled.code),
        compiledBytes: Buffer.byteLength(compiled.code),
      });
      continue;
    }
    if (validation) {
      let stdout = "";
      Sk.configure({
        output: (text) => {
          stdout += text;
        },
        read: (name) => {
          if (!(name in Sk.builtinFiles.files))
            throw new Error("Missing standard library source: " + name);
          return Sk.builtinFiles.files[name];
        },
        execLimit: null,
        yieldLimit: null,
      });
      if (executeOnly) {
        const result = executable(item.source)();
        assert.ok(
          !(result instanceof Sk.misceval.Suspension),
          "Use synchronous execution workloads",
        );
      } else {
        await Sk.misceval.asyncToPromise(() =>
          Sk.importMainWithBody("benchmark", false, item.source, true),
        );
      }
      results.push({ name: item.name, stdout });
      continue;
    }
    for (const measuredPhase of executeOnly
      ? ["execute"]
      : phase
        ? [phase]
        : ["parse", "compile"]) {
      const setupStart = performance.now();
      const operation =
        measuredPhase === "execute"
          ? executable(item.source)
          : measuredPhase === "compile"
            ? () => compile(item.source)
            : () => sourceToAST(item.source);
      const setupMs = performance.now() - setupStart;
      const firstStart = performance.now();
      operation();
      const firstMs = performance.now() - firstStart;
      const timing = measure(operation);
      const retainedSamples = [];
      for (let sample = 0; sample < 5; sample++) {
        global.gc();
        const before = process.memoryUsage().heapUsed;
        let retained = Array.from({ length: 16 }, operation);
        global.gc();
        retainedSamples.push(
          (process.memoryUsage().heapUsed - before) / retained.length,
        );
        retained = null;
      }
      results.push({
        name: item.name,
        phase: measuredPhase,
        ...(measuredPhase === "execute" ? { setupMs } : {}),
        firstMs,
        ...timing,
        retainedSamples,
        retainedBytesPerResult: quantile(retainedSamples, 0.5),
      });
    }
  }
  // File IPC avoids synchronous child-process pipe stalls on macOS. Serialization
  // is outside the timed sections. Installed runtimes can keep GC timers alive.
  writeFileSync(
    option("--result"),
    JSON.stringify({ loadMs, loadHeapBytes, cases: results }) + "\n",
  );
  process.exit(0);
} else {
  assert.ok(
    (option("--original") || option("--optimizer")) &&
      option("--adapter") &&
      option("--direct") &&
      option("--parser") &&
      option("--stdlib") &&
      option("--output"),
    "Use --adapter <js> --direct <js> --parser <core.js> --stdlib <js> --output <json> and either --original <js> or --optimizer <js> [--compile-only | --execute-only] [--rounds 3]",
  );
  const optimizer = option("--optimizer")
    ? resolve(option("--optimizer"))
    : null;
  const engines = (
    optimizer ? ["adapter", "direct"] : ["original", "adapter", "direct"]
  ).flatMap((name) => {
    const engine = {
      name,
      kind: name,
      path: resolve(option(`--${name}`)),
      ...(name === "adapter" ? { parser: resolve(option("--parser")) } : {}),
    };
    return optimizer
      ? [engine, { ...engine, name: "optimized-" + name, optimizer }]
      : [engine];
  });
  if (option("--baseline-parser") || option("--baseline-direct")) {
    assert.ok(
      !optimizer,
      "Do not combine parser artifact and optimizer comparisons",
    );
    assert.ok(
      option("--baseline-parser") && option("--baseline-direct"),
      "Provide both baseline artifacts for paired comparisons",
    );
    engines.splice(1, 0, {
      name: "baseline-adapter",
      kind: "adapter",
      path: resolve(option("--adapter")),
      parser: resolve(option("--baseline-parser")),
    });
    engines.splice(3, 0, {
      name: "baseline-direct",
      kind: "direct",
      path: resolve(option("--baseline-direct")),
    });
  }
  const moduleSource = (count, unicode = false) =>
    Array.from(
      { length: count },
      (_, i) =>
        `def f${i}(x, y=${i}):\n    label = ${unicode ? "'café 雪 😀'" : "'label'"}\n    return [x + y + j for j in range(3)]\n`,
    ).join("\n") + `\nprint(f${count - 1}(2))\n`;
  const cases = option("--cases")
    ? JSON.parse(readFileSync(option("--cases"), "utf8")).map(
        ({ name, source }) => ({ name, source }),
      )
    : [
        { name: "small", source: "x = 1 + 2\nprint(x)\n" },
        { name: "medium-50-functions", source: moduleSource(50) },
        { name: "large-200-functions", source: moduleSource(200) },
        { name: "unicode-50-functions", source: moduleSource(50, true) },
        {
          name: "multiline-expression",
          source: "value = (\n 1 +\n 2\n)\nprint(value)\n",
        },
        // Checked-in execution fixture, independent of the generated workloads.
        {
          name: "list-method-fixture",
          source: readFileSync("test/run/t43.py", "utf8"),
        },
      ];
  const compileOnly = args.includes("--compile-only");
  const executeOnly = args.includes("--execute-only");
  const phase = option("--phase", null);
  assert.ok(
    phase === null || ["parse", "compile"].includes(phase),
    "Use --phase parse|compile",
  );
  assert.ok(
    !executeOnly || phase === null,
    "Execution mode has no parse/compile phase",
  );
  assert.ok(
    !(compileOnly && executeOnly),
    "Choose compilation acceptance or execution validation",
  );
  const python = option("--python", "python3.14");
  assert.equal(
    spawnSync(python, ["-c", "import sys; print(sys.version_info[:3])"], {
      encoding: "utf8",
    }).stdout.trim(),
    "(3, 14, 3)",
  );
  const run = (engine, validation) => {
    const directory = mkdtempSync(resolve(tmpdir(), "skulpt-benchmark-"));
    const input = resolve(directory, "input.json");
    const result = resolve(directory, "result.json");
    try {
      writeFileSync(
        input,
        JSON.stringify({
          engine,
          cases,
          validation,
          stdlib: resolve(option("--stdlib")),
          executeOnly,
          phase,
        }),
      );
      const child = spawnSync(
        process.execPath,
        [
          "--expose-gc",
          fileURLToPath(import.meta.url),
          "--worker",
          "--input",
          input,
          "--result",
          result,
        ],
        {
          encoding: "utf8",
          stdio: ["ignore", "ignore", "pipe"],
          timeout: 180_000,
        },
      );
      assert.equal(child.status, 0, child.error?.message || child.stderr);
      return JSON.parse(readFileSync(result, "utf8"));
    } finally {
      rmSync(directory, { recursive: true });
    }
  };
  if (compileOnly) {
    const directory = mkdtempSync(resolve(tmpdir(), "skulpt-cpython-"));
    const input = resolve(directory, "cases.json");
    try {
      writeFileSync(input, JSON.stringify(cases));
      const acceptance = spawnSync(
        python,
        [
          "-c",
          "import ast,json,sys; [ast.parse(c['source'], filename=c['name']) for c in json.load(open(sys.argv[1]))]",
          input,
        ],
        { encoding: "utf8", timeout: 180_000 },
      );
      assert.equal(
        acceptance.status,
        0,
        acceptance.error?.message || acceptance.stderr,
      );
    } finally {
      rmSync(directory, { recursive: true });
    }
  }
  // Validate all runtime results before any measured process starts.
  const expected = compileOnly
    ? null
    : cases.map((item) => {
        const result = spawnSync(python, ["-c", item.source], {
          encoding: "utf8",
        });
        assert.equal(result.status, 0, result.stderr);
        return { name: item.name, stdout: result.stdout };
      });
  const verification = engines.map((engine) => ({
    engine: engine.name,
    cases: run(engine, compileOnly ? "compile" : true).cases,
  }));
  if (compileOnly) {
    // Full app modules can require their consumer's network/UI environment.
    // Verify compilation without executing imports; paired compiler output
    // must remain identical before timing those candidate artifacts.
    for (const name of ["adapter", "direct"]) {
      const baseline = verification.find(
        (item) => item.engine === "baseline-" + name,
      );
      if (baseline)
        assert.deepEqual(
          verification.find((item) => item.engine === name).cases,
          baseline.cases,
          name,
        );
    }
  } else {
    for (const item of verification)
      assert.deepEqual(item.cases, expected, item.engine);
  }
  const report = {
    revision: spawnSync("git", ["rev-parse", "HEAD"], {
      encoding: "utf8",
    }).stdout.trim(),
    environment: {
      node: process.version,
      cpu: cpus()[0].model,
      platform: platform(),
      release: release(),
      arch: arch(),
      logicalCpus: cpus().length,
      memoryBytes: totalmem(),
      hardware:
        platform() === "darwin"
          ? spawnSync("sysctl", ["-n", "hw.model"], {
              encoding: "utf8",
            }).stdout.trim()
          : null,
    },
    manifest: option("--manifest")
      ? JSON.parse(readFileSync(option("--manifest"), "utf8"))
      : null,
    validation: compileOnly
      ? optimizer
        ? "CPython source acceptance and both compiler paths; optimized JavaScript may differ. No app execution."
        : "CPython source acceptance and compilation; paired generated JavaScript must match. No app execution."
      : "Execution compared with CPython 3.14.3.",
    verification,
    phase: executeOnly ? "execute" : (phase ?? "parse+compile"),
    parser: {
      path: resolve(option("--parser")),
      sha256: hash(readFileSync(option("--parser"))),
    },
    optimizer: optimizer
      ? {
          path: optimizer,
          sha256: hash(readFileSync(optimizer)),
          bytes: readFileSync(optimizer).length,
          gzip: gzipSync(readFileSync(optimizer)).length,
          brotli: brotliCompressSync(readFileSync(optimizer)).length,
        }
      : null,
    stdlib: {
      path: resolve(option("--stdlib")),
      sha256: hash(readFileSync(option("--stdlib"))),
    },
    cases: cases.map((item) => ({
      ...item,
      bytes: Buffer.byteLength(item.source),
      sha256: hash(item.source),
    })),
    engines: engines.map((engine) => {
      const bytes = readFileSync(engine.path);
      return {
        ...engine,
        sha256: hash(bytes),
        size: {
          raw: bytes.length,
          gzip: gzipSync(bytes).length,
          brotli: brotliCompressSync(bytes).length,
        },
      };
    }),
    runs: [],
  };
  writeFileSync(option("--output"), JSON.stringify(report));
  for (
    let round = 0;
    round < Number(option("--rounds", optimizer ? "5" : "3"));
    round++
  ) {
    const order = round % 2 ? [...engines].reverse() : engines;
    for (const engine of order) {
      report.runs.push({ engine: engine.name, round, ...run(engine, false) });
      writeFileSync(option("--output"), JSON.stringify(report));
      console.error(round + 1, engine.name);
    }
  }
}
