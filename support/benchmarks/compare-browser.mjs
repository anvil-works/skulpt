// Headless test browsers use temporary profiles, separate from user sessions.
import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { spawnSync } from "node:child_process";
import { readFileSync, writeFileSync } from "node:fs";
import { createHash } from "node:crypto";
import { resolve } from "node:path";
import { cpus } from "node:os";
import { cases } from "./cases.mjs";

const args = process.argv.slice(2);
const option = (name, fallback) => args.includes(name) ? args[args.indexOf(name) + 1] : fallback;
const playwright = createRequire(import.meta.url)(resolve(option("--playwright")));
const browserName = option("--browser", "chromium");
// Anvil production builds split library sources into JSON groups. Preload
// the requested groups before importing; neither loading nor setup is timed.
const stdlibGroups = option("--stdlib-groups", "").split(",").filter(Boolean).map(path => resolve(path));
const libraryFiles = Object.assign({}, ...stdlibGroups.map(path => JSON.parse(readFileSync(path, "utf8"))));
const stdlibEvidence = [resolve(option("--stdlib", "dist/skulpt-stdlib.js")), ...stdlibGroups]
    .map(path => ({ path, sha256: createHash("sha256").update(readFileSync(path)).digest("hex") }));
const rounds = Number(option("--rounds", "5"));
assert.ok(Number.isInteger(rounds) && rounds > 0);
const engines = ["baseline", "candidate"].map(name => ({ name, path: resolve(option("--" + name)) }));
const caseNames = option("--case")?.split(",");
const selected = caseNames ? cases.filter(item => caseNames.includes(item.name))
    : cases.filter(item => item.name !== "many-constants" && !item.longRunning);
assert.ok(selected.length);
const median = values => [...values].sort((a, b) => a - b)[Math.floor(values.length / 2)];
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
const python = option("--python", "python3");
const pythonVersion = spawnSync(python, ["--version"], { encoding: "utf8" });
assert.equal(pythonVersion.status, 0, pythonVersion.stderr);
const validation = {};
for (const item of selected) {
    const result = spawnSync(python, ["-c", item.source + "\nimport json\nprint(json.dumps(benchmark()))"], { encoding: "utf8", timeout: 60000 });
    assert.equal(result.status, 0, result.stderr);
    validation[item.name] = JSON.parse(result.stdout.trim().split("\n").pop());
}
const runs = [];
let browserVersion;
for (let round = 0; round < rounds; round++) {
    for (const item of selected) {
        for (const engine of round % 2 ? [...engines].reverse() : engines) {
            const browser = await playwright[browserName].launch({ headless: true });
            try {
                browserVersion = browser.version();
                const page = await browser.newPage();
                await page.addScriptTag({ path: engine.path });
                await page.addScriptTag({ path: resolve(option("--stdlib", "dist/skulpt-stdlib.js")) });
                await page.evaluate(files => Object.assign(Sk.builtinFiles.files, files), libraryFiles);
                const result = await page.evaluate(async ({ source, longRunning }) => {
                    const { Sk } = globalThis;
                    Sk.configure({ __future__: Sk.python3, output: () => {}, execLimit: null, yieldLimit: null,
                        read: name => {
                            if (!(name in Sk.builtinFiles.files)) throw new Error("Missing file: " + name);
                            return Sk.builtinFiles.files[name];
                        } });
                    const module = await Sk.misceval.asyncToPromise(() => Sk.importMainWithBody("benchmark", false, source, true));
                    const run = () => {
                        const result = Sk.misceval.callsimArray(module.$d.benchmark);
                        if (result instanceof Sk.misceval.Suspension) throw new Error("Expected synchronous workload");
                        return result;
                    };
                    const value = Sk.ffi.remapToJs(run());
                    const warmups = longRunning ? 1 : 5;
                    const calibrationRuns = longRunning ? 1 : 3;
                    const batches = longRunning ? 3 : 7;
                    for (let i = 0; i < warmups; i++) run();
                    let start = performance.now();
                    for (let i = 0; i < calibrationRuns; i++) run();
                    const iterations = Math.max(1, Math.min(1000, Math.ceil(75 / ((performance.now() - start) / calibrationRuns))));
                    const samplesMs = [];
                    for (let batch = 0; batch < batches; batch++) {
                        start = performance.now();
                        for (let i = 0; i < iterations; i++) run();
                        samplesMs.push((performance.now() - start) / iterations);
                    }
                    return { value, iterations, warmups, calibrationRuns, batches, samplesMs,
                        medianMs: [...samplesMs].sort((a, b) => a - b)[Math.floor(batches / 2)] };
                }, item);
                equal(result.value, validation[item.name]);
                runs.push({ round, name: item.name, engine: engine.name, ...result });
            } finally {
                await browser.close();
            }
        }
        console.log(`Round ${round + 1}/${rounds}: ${item.name}`);
    }
}
const summary = selected.map(item => {
    const timings = Object.fromEntries(engines.map(engine => [engine.name,
        median(runs.filter(run => run.name === item.name && run.engine === engine.name).map(run => run.medianMs))]));
    return { name: item.name, ...timings, executionSpeedup: timings.baseline / timings.candidate };
});
writeFileSync(resolve(option("--output", "/tmp/skulpt-browser-runtime.json")), JSON.stringify({
    measuredAt: new Date().toISOString(), browser: browserName, browserVersion, cpu: cpus()[0].model,
    python: { executable: python, version: pythonVersion.stdout.trim() || pythonVersion.stderr.trim() }, rounds,
    stdlib: stdlibEvidence,
    engines: engines.map(engine => ({ ...engine, sha256: createHash("sha256").update(readFileSync(engine.path)).digest("hex") })),
    method: "Fresh headless browser with temporary profile for every engine/case/round; alternating engine order; normally 5 warmups, 3 calibration calls and 7 batches targeting 75ms. Opt-in long-running fixtures use 1 warmup, 1 calibration call and 3 batches. Module/import setup and compilation untimed. Natural allocation/GC included. CPython output validation (1e-9 tolerance).",
    sources: selected, validation, summary, runs,
}, null, 2) + "\n");
console.table(summary.map(row => ({ name: row.name, "baseline ms": row.baseline.toFixed(3),
    "candidate ms": row.candidate.toFixed(3), speedup: row.executionSpeedup.toFixed(2) + "x" })));
