// Capture V8 CPU samples in a separate headless Chromium profile.
import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { createHash } from "node:crypto";
import { readFileSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";
import { cases } from "./cases.mjs";

const args = process.argv.slice(2);
const option = (name, fallback) => args.includes(name) ? args[args.indexOf(name) + 1] : fallback;
// Anvil production builds split library sources into JSON groups. Preload
// the requested groups before importing; neither loading nor setup is timed.
const stdlibGroups = option("--stdlib-groups", "").split(",").filter(Boolean).map(path => resolve(path));
const libraryFiles = Object.assign({}, ...stdlibGroups.map(path => JSON.parse(readFileSync(path, "utf8"))));
const stdlibEvidence = [resolve(option("--stdlib", "dist/skulpt-stdlib.js")), ...stdlibGroups]
    .map(path => ({ path, sha256: createHash("sha256").update(readFileSync(path)).digest("hex") }));
const require = createRequire(import.meta.url);
const playwright = require(resolve(option("--playwright")));
const selected = option("--case", "field").split(",").map(name => {
    const item = cases.find(item => item.name === name);
    assert.ok(item, "Unknown case: " + name);
    return item;
});
const output = resolve(option("--output", "/tmp/skulpt-v8-profile.json"));
const bundle = resolve(option("--bundle", "dist/skulpt.min.js"));
const sourceMap = option("--source-map")
    ? new (require("source-map").SourceMapConsumer)(JSON.parse(readFileSync(option("--source-map"), "utf8"))) : null;
const reports = [];
for (const item of selected) {
    const browser = await playwright.chromium.launch({ headless: true,
        args: args.includes("--trace-v8") ? ["--js-flags=--trace-opt --trace-deopt"] : [] });
    try {
        const page = await browser.newPage();
        await page.addScriptTag({ path: bundle });
        await page.addScriptTag({ path: resolve(option("--stdlib", "dist/skulpt-stdlib.js")) });
        await page.evaluate(files => Object.assign(Sk.builtinFiles.files, files), libraryFiles);
        const warmups = item.longRunning ? 1 : 10;
        await page.evaluate(async ({ source, warmups }) => {
            const { Sk } = globalThis;
            Sk.configure({ __future__: Sk.python3, output: () => {}, execLimit: null, yieldLimit: null,
                read: name => Sk.builtinFiles.files[name] });
            const module = await Sk.misceval.asyncToPromise(() => Sk.importMainWithBody("benchmark", false, source, true));
            globalThis.runBenchmark = () => Sk.misceval.callsimArray(module.$d.benchmark);
            for (let i = 0; i < warmups; i++) runBenchmark();
        }, { source: item.source, warmups });
        const session = await page.context().newCDPSession(page);
        await session.send("Profiler.enable");
        await session.send("Profiler.setSamplingInterval", { interval: 500 });
        await session.send("Profiler.start");
        const { invocations, elapsedMs, value } = await page.evaluate(({ seconds, longRunning }) => {
            const start = performance.now();
            const until = start + seconds * 1000;
            let count = 0;
            let result;
            do {
                const value = runBenchmark();
                if (value && value.$isSuspension) throw new Error("Expected synchronous benchmark");
                count++;
                result = value;
            } while (!longRunning && performance.now() < until);
            return { invocations: count, elapsedMs: performance.now() - start, value: Sk.ffi.remapToJs(result) };
        }, { seconds: Number(option("--seconds", "3")), longRunning: !!item.longRunning });
        const { profile } = await session.send("Profiler.stop");
        const profilePath = output.replace(/\.json$/, "") + "-" + item.name + ".cpuprofile";
        writeFileSync(profilePath, JSON.stringify(profile));
        const totals = new Map();
        const bundleScripts = new Set(profile.nodes.filter(node => node.callFrame.url === bundle)
            .map(node => node.callFrame.scriptId));
        for (const node of profile.nodes) {
            if (!node.hitCount) continue;
            const frame = node.callFrame;
            const pos = sourceMap && bundleScripts.has(frame.scriptId)
                ? sourceMap.originalPositionFor({ line: frame.lineNumber + 1, column: frame.columnNumber }) : null;
            const location = pos && pos.source ? `${pos.source}:${pos.line}` : frame.url || "generated/native";
            const label = `${pos && pos.name || frame.functionName || "(anonymous)"} ${location}`;
            totals.set(label, (totals.get(label) || 0) + node.hitCount);
        }
        const samples = profile.samples.length;
        const hot = [...totals].sort((a, b) => b[1] - a[1]).slice(0, 30)
            .map(([frame, hits]) => ({ frame, hits, selfPercent: 100 * hits / samples }));
        reports.push({ name: item.name, browserVersion: browser.version(), warmups, invocations, elapsedMs, value, samples, profilePath, hot });
        console.log(item.name);
        console.table(hot.slice(0, 12).map(row => ({ frame: row.frame, selfPercent: row.selfPercent.toFixed(1) })));
    } finally {
        await browser.close();
    }
}
writeFileSync(output, JSON.stringify({ measuredAt: new Date().toISOString(), stdlib: stdlibEvidence, bundle,
    v8Tracing: args.includes("--trace-v8"),
    sha256: createHash("sha256").update(readFileSync(bundle)).digest("hex"),
    sourceMap: option("--source-map"),
    method: "V8 CDP CPU sampling at 500 microseconds; normally 10 warmup invocations and a 3-second window, finishing the final invocation in full. Opt-in long-running fixtures use 1 warmup and profile 1 fixed-work invocation. Fresh headless Chromium per case. Self-sample attribution includes inlined callees. Profiles are separate from benchmark comparisons.",
    reports }, null, 2) + "\n");
