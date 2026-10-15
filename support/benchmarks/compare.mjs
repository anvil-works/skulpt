// Fresh-process production-bundle comparison. Module/import setup is untimed.
import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import { readFileSync, writeFileSync, mkdtempSync, rmSync } from "node:fs";
import { tmpdir, cpus, platform, arch } from "node:os";
import { resolve, join } from "node:path";
import { fileURLToPath } from "node:url";
import { cases } from "./cases.mjs";

const args = process.argv.slice(2);
const option = (key, fallback) => args.includes(key) ? args[args.indexOf(key) + 1] : fallback;
// Anvil production builds split library sources into JSON groups. Preload
// the requested groups before importing; neither loading nor setup is timed.
const stdlibGroups = option("--stdlib-groups", "").split(",").filter(Boolean).map(path => resolve(path));
const libraryFiles = Object.assign({}, ...stdlibGroups.map(path => JSON.parse(readFileSync(path, "utf8"))));
const stdlibEvidence = [resolve(option("--stdlib", "dist/skulpt-stdlib.js")), ...stdlibGroups]
    .map(path => ({ path, sha256: createHash("sha256").update(readFileSync(path)).digest("hex") }));
const executionOnly = args.includes("--execution-only");
const phases = executionOnly ? ["execution"] : ["execution", "compile"];
const median = values => [...values].sort((a, b) => a - b)[Math.floor(values.length / 2)];
function measure(operation, longRunning) {
    const warmups = longRunning ? 1 : 5;
    const calibrationRuns = longRunning ? 1 : 3;
    const batches = longRunning ? 3 : 7;
    for (let i = 0; i < warmups; i++) operation();
    let start = performance.now();
    for (let i = 0; i < calibrationRuns; i++) operation();
    const iterations = Math.max(1, Math.min(1000, Math.ceil(75 / ((performance.now() - start) / calibrationRuns))));
    const samplesMs = [];
    for (let batch = 0; batch < batches; batch++) {
        start = performance.now();
        for (let i = 0; i < iterations; i++) operation();
        samplesMs.push((performance.now() - start) / iterations);
    }
    return { iterations, warmups, calibrationRuns, batches, samplesMs, medianMs: median(samplesMs) };
}
function equal(actual, expected) {
    if (Array.isArray(expected)) {
        assert.equal(actual.length, expected.length);
        actual.forEach((value, i) => equal(value, expected[i]));
    } else if (typeof expected === "number") {
        assert.ok(Math.abs(actual - expected) <= 1e-9 * Math.max(1, Math.abs(expected)), `${actual} != ${expected}`);
    } else {
        assert.equal(actual, expected);
    }
}
if (args.includes("--worker")) {
    const item = cases.find(item => item.name === option("--case"));
    const require = createRequire(import.meta.url);
    require(resolve(option("--bundle")));
    require(resolve(option("--stdlib", "dist/skulpt-stdlib.js")));
    const { Sk } = globalThis;
    Object.assign(Sk.builtinFiles.files, libraryFiles);
    Sk.configure({
        __future__: Sk.python3, output: () => {}, execLimit: null, yieldLimit: null,
        read: name => {
            assert.ok(name in Sk.builtinFiles.files, "Missing standard library file: " + name);
            return Sk.builtinFiles.files[name];
        },
    });
    const module = await Sk.misceval.asyncToPromise(() => Sk.importMainWithBody("benchmark", false, item.source, true));
    const run = () => {
        const result = Sk.misceval.callsimArray(module.$d.benchmark);
        assert.ok(!(result instanceof Sk.misceval.Suspension), "Expected synchronous workload");
        return result;
    };
    const value = Sk.ffi.remapToJs(run());
    const execution = measure(run, item.longRunning);
    const compile = executionOnly ? undefined : measure(() => {
        Sk.resetCompiler();
        return Sk.compile(item.source, "benchmark.py", "exec", true);
    });
    Sk.resetCompiler();
    const emitted = Sk.compile(item.source, "benchmark.py", "exec", true).code;
    writeFileSync(option("--result"), JSON.stringify({ value, execution, compile,
        compiledSha256: createHash("sha256").update(emitted).digest("hex"),
        compiledBytes: Buffer.byteLength(emitted) }));
} else {
    const engines = ["baseline", "candidate"].map(name => ({ name, path: resolve(option("--" + name)) }));
    const caseNames = option("--case")?.split(",");
    const selected = caseNames ? cases.filter(item => caseNames.includes(item.name))
        : cases.filter(item => !item.longRunning && (!executionOnly || item.name !== "many-constants"));
    assert.ok(selected.length, "Unknown case");
    const rounds = Number(option("--rounds", "5"));
    assert.ok(Number.isInteger(rounds) && rounds > 0);
    const pythonExecutable = option("--python", "python3");
    const pythonVersion = spawnSync(pythonExecutable, ["--version"], { encoding: "utf8" });
    assert.equal(pythonVersion.status, 0, pythonVersion.stderr);
    const runs = [], validation = {};
    const directory = mkdtempSync(join(tmpdir(), "skulpt-performance-"));
    try {
        for (const item of selected) {
            const python = spawnSync(pythonExecutable, ["-c", item.source + "\nimport json\nprint(json.dumps(benchmark()))"], { encoding: "utf8", timeout: 60000 });
            assert.equal(python.status, 0, python.stderr);
            validation[item.name] = JSON.parse(python.stdout.trim().split("\n").pop());
        }
        for (let round = 0; round < rounds; round++) {
            for (const item of selected) {
                for (const engine of round % 2 ? [...engines].reverse() : engines) {
                    const result = join(directory, "result.json");
                    const worker = spawnSync(process.execPath, [fileURLToPath(import.meta.url), "--worker",
                        "--bundle", engine.path, "--stdlib", resolve(option("--stdlib", "dist/skulpt-stdlib.js")),
                        "--stdlib-groups", stdlibGroups.join(","),
                        "--case", item.name, "--result", result, ...(executionOnly ? ["--execution-only"] : [])], { encoding: "utf8", timeout: 60000 });
                    assert.equal(worker.status, 0, worker.stderr || String(worker.error));
                    const data = JSON.parse(readFileSync(result, "utf8"));
                    equal(data.value, validation[item.name]);
                    runs.push({ round, engine: engine.name, name: item.name, ...data });
                }
                console.log(`Round ${round + 1}/${rounds}: ${item.name}`);
            }
        }
    } finally {
        rmSync(directory, { recursive: true });
    }
    const summary = selected.map(item => {
        const timings = Object.fromEntries(engines.map(engine => {
            const rows = runs.filter(row => row.name === item.name && row.engine === engine.name);
            return [engine.name, Object.fromEntries(phases.map(phase => [phase, median(rows.map(row => row[phase].medianMs))]))];
        }));
        return { name: item.name, ...timings,
            executionSpeedup: timings.baseline.execution / timings.candidate.execution,
            ...(executionOnly ? {} : { compileSpeedup: timings.baseline.compile / timings.candidate.compile }) };
    });
    writeFileSync(resolve(option("--output", "support/benchmarks/results.json")), JSON.stringify({
        measuredAt: new Date().toISOString(), node: process.version,
        python: { executable: pythonExecutable, version: pythonVersion.stdout.trim() || pythonVersion.stderr.trim() },
        machine: { cpu: cpus()[0].model, platform: platform(), arch: arch() }, rounds, phases,
        stdlib: stdlibEvidence,
    engines: engines.map(engine => ({ ...engine, sha256: createHash("sha256").update(readFileSync(engine.path)).digest("hex") })),
        method: "Fresh worker per case/engine/round; alternating order; normally 5 warmups, 3 calibration calls and 7 batches targeting 75ms. Opt-in long-running fixtures use 1 warmup, 1 calibration call and 3 batches. Median of worker medians. Imports and module setup untimed. Normal suspendable compilation; yield/exec limits disabled. CPython checks every result (relative/absolute tolerance 1e-9). No forced GC in timing: allocation/GC costs included.",
        validation, sources: selected, summary, runs,
    }, null, 2) + "\n");
    console.table(summary.map(row => ({ name: row.name,
        "baseline ms": row.baseline.execution.toFixed(3), "candidate ms": row.candidate.execution.toFixed(3),
        "execution speedup": row.executionSpeedup.toFixed(2) + "x",
        ...(executionOnly ? {} : { "compile speedup": row.compileSpeedup.toFixed(2) + "x" }) })));
}
