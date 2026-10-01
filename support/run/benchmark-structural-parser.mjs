// Paired, fresh-process measurements of the temporary compiler adapter.
import fs from "node:fs";
import os from "node:os";
import { resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { createRequire } from "node:module";
import { createHash } from "node:crypto";
import { spawnSync } from "node:child_process";
import { performance } from "node:perf_hooks";
import { gzipSync, brotliCompressSync } from "node:zlib";
import assert from "node:assert/strict";

const [parserArg, output, worker, frontend, phase, caseIndex] = process.argv.slice(2);
if (!parserArg || !output) throw new Error("Usage: node support/run/benchmark-structural-parser.mjs <core-bundle> <report.json>");
const parserPath = resolve(parserArg);
const skulptPath = resolve("dist/skulpt.min.js");
const hash = (bytes) => createHash("sha256").update(bytes).digest("hex");
const median = (xs) => [...xs].sort((a, b) => a - b)[Math.floor(xs.length / 2)];
function moduleSource(count, unicode = false) {
    return Array.from({length: count}, (_, i) =>
        `def f${i}(x, y=${i}):\n    label = ${unicode ? "'café 雪 😀'" : "'label'"}\n    return [x + y + j for j in range(3)]\n`
    ).join("\n") + `\nprint(f${count - 1}(2))\n`;
}
const cases = [
    {name: "small", source: "x = 1 + 2\nprint(x)\n"},
    {name: "medium-50-functions", source: moduleSource(50)},
    {name: "large-200-functions", source: moduleSource(200)},
    {name: "unicode-50-functions", source: moduleSource(50, true)},
    {name: "legacy-50-functions", python2: true, source:
        Array.from({length: 50}, (_, i) => `def f${i}(x):\n    return x + 0755L\n`).join("\n") + "print f49(2)\n"},
];

if (worker === "--worker") {
    globalThis.gc();
    const beforeHeap = process.memoryUsage().heapUsed;
    const start = performance.now();
    createRequire(import.meta.url)(skulptPath);
    const { Sk } = globalThis;
    const parseModule = frontend === "adapter" ? (await import(pathToFileURL(parserPath).href)).parseModule : null;
    const item = cases[Number(caseIndex)];
    Sk.configure({sourceParser: parseModule, __future__: {...(item.python2 ? Sk.python2 : Sk.python3)}});
    const loadMs = performance.now() - start;
    globalThis.gc();
    const loadHeapBytes = process.memoryUsage().heapUsed - beforeHeap;
    const operation = phase === "parse"
        ? () => Sk.parseCompilerModule(item.source, "benchmark.py").ast
        : () => { Sk.resetCompiler(); return Sk.compile(item.source, "benchmark.py", "exec", true); };
    const firstStart = performance.now();
    operation();
    const firstMs = performance.now() - firstStart;
    for (let i = 0; i < 30; i++) operation();
    const calibration = performance.now();
    for (let i = 0; i < 10; i++) operation();
    const iterations = Math.max(1, Math.min(1000, Math.ceil(100 / ((performance.now() - calibration) / 10))));
    const samples = [];
    for (let batch = 0; batch < 7; batch++) {
        const begin = performance.now();
        for (let i = 0; i < iterations; i++) operation();
        samples.push((performance.now() - begin) / iterations);
    }
    globalThis.gc();
    const beforeRetained = process.memoryUsage().heapUsed;
    const retained = Array.from({length: 16}, operation);
    globalThis.gc();
    const heapDeltaBytesPerResult = (process.memoryUsage().heapUsed - beforeRetained) / retained.length;
    console.log(JSON.stringify({name: item.name, frontend, phase, loadMs, loadHeapBytes, firstMs, iterations,
        samples, medianMs: median(samples), heapDeltaBytesPerResult, maxRSSKiB: process.resourceUsage().maxRSS}));
} else {
    // Validate execution before timing, in a different process from measured workers.
    const python = process.env.PYTHON314 || "python3.14";
    const version = spawnSync(python, ["-c", "import sys; print(sys.version_info[:3])"], {encoding: "utf8"});
    assert.equal(version.status, 0, version.stderr || String(version.error));
    assert.equal(version.stdout.trim(), "(3, 14, 3)");
    createRequire(import.meta.url)(skulptPath);
    const { Sk } = globalThis;
    const { parseModule } = await import(pathToFileURL(parserPath).href);
    createRequire(import.meta.url)(resolve("dist/skulpt-stdlib.js"));
    for (const item of cases) {
        const outputs = [];
        for (const parser of [null, parseModule]) {
            let stdout = "";
            Sk.configure({sourceParser: parser, __future__: {...(item.python2 ? Sk.python2 : Sk.python3)},
                output: (text) => { stdout += text; }, read: (name) => Sk.builtinFiles.files[name], execLimit: null, yieldLimit: null});
            await Sk.misceval.asyncToPromise(() => Sk.importMainWithBody("benchmark", false, item.source, true));
            outputs.push(stdout);
        }
        assert.equal(outputs[0], outputs[1], item.name);
        if (!item.python2) {
            const oracle = spawnSync(python, ["-c", item.source], {encoding: "utf8"});
            assert.equal(oracle.status, 0, oracle.stderr);
            assert.equal(outputs[1], oracle.stdout, item.name);
        }
    }
    const results = [];
    for (let round = 0; round < 3; round++) {
        for (const operation of ["parse", "compile"]) {
            for (let i = 0; i < cases.length; i++) {
                for (const engine of (round % 2 ? ["adapter", "old"] : ["old", "adapter"])) {
                    const result = spawnSync(process.execPath, ["--expose-gc", fileURLToPath(import.meta.url),
                        parserPath, output, "--worker", engine, operation, String(i)], {encoding: "utf8"});
                    assert.equal(result.status, 0, result.stderr);
                    results.push({round, ...JSON.parse(result.stdout)});
                }
            }
        }
        process.stderr.write(`Round ${round + 1}/3 complete\n`);
    }
    const bundles = [skulptPath, parserPath].map((path) => {
        const bytes = fs.readFileSync(path);
        return {name: path === skulptPath ? "dual-frontend-skulpt" : "lean-parser", sha256: hash(bytes),
            raw: bytes.length, gzip: gzipSync(bytes).length, brotli: brotliCompressSync(bytes).length};
    });
    const report = {environment: {node: process.version, platform: process.platform, arch: process.arch,
        cpu: os.cpus()[0].model}, bundles,
        cases: cases.map((item) => ({...item, bytes: Buffer.byteLength(item.source), sha256: hash(item.source)})), results};
    fs.writeFileSync(output, JSON.stringify(report, null, 2) + "\n");
    for (const operation of ["parse", "compile"]) {
        for (const item of cases) {
            const time = (engine) => median(results.filter((r) => r.name === item.name && r.phase === operation && r.frontend === engine).map((r) => r.medianMs));
            console.log(operation, item.name, JSON.stringify({old: time("old"), adapter: time("adapter"), ratio: time("adapter") / time("old")}));
        }
    }
}
