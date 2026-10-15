// Isolate loop syntax before changing production code. Use an external Playwright install.
import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { resolve } from "node:path";
import { readFileSync, writeFileSync } from "node:fs";
import { createHash } from "node:crypto";
import { cpus } from "node:os";

const args = process.argv.slice(2);
const option = (name, fallback) => args.includes(name) ? args[args.indexOf(name) + 1] : fallback;
const playwright = createRequire(import.meta.url)(resolve(option("--playwright")));
const rounds = Number(option("--rounds", "5"));
const bundle = resolve(option("--bundle", "dist/skulpt.min.js"));
assert.ok(Number.isInteger(rounds) && rounds > 0);
const median = values => [...values].sort((a, b) => a - b)[Math.floor(values.length / 2)];
const scenarios = {
    "three-item-literal": {
        setup: "const a = {v: 1}, b = {v: 2}, c = {v: 3};",
        prefix: "let total = seed; for (let j = 0; j < 10000; j++) { a.v = j & 255;",
        variants: {
            forEach: "[a, b, c].forEach(x => { total = (total + x.v) | 0; });",
            indexed: "const items = [a, b, c]; for (let i = 0; i < items.length; i++) total = (total + items[i].v) | 0;",
            forOf: "for (const x of [a, b, c]) total = (total + x.v) | 0;",
            direct: "total = (total + a.v) | 0; total = (total + b.v) | 0; total = (total + c.v) | 0;",
        },
        suffix: "} return total;",
    },
    "packed-array": {
        setup: "const items = []; for (let i = 0; i < 1024; i++) items.push(i & 255);",
        prefix: "let total = seed; for (let j = 0; j < 100; j++) {",
        variants: {
            forEach: "items.forEach(x => { total = (total + x) | 0; });",
            indexed: "for (let i = 0; i < items.length; i++) total = (total + items[i]) | 0;",
            forOf: "for (const x of items) total = (total + x) | 0;",
        },
        suffix: "} return total;",
    },
    "typed-array": {
        setup: "const items = new Uint8Array(1024); for (let i = 0; i < items.length; i++) items[i] = i & 255;",
        prefix: "let total = seed; for (let j = 0; j < 100; j++) {",
        variants: {
            forEach: "items.forEach(x => { total = (total + x) | 0; });",
            indexed: "for (let i = 0; i < items.length; i++) total = (total + items[i]) | 0;",
            forOf: "for (const x of items) total = (total + x) | 0;",
        },
        suffix: "} return total;",
    },
    "skulpt-byte-boxing": {
        bundle: true,
        setup: "const items = new Uint8Array(1024); for (let i = 0; i < items.length; i++) items[i] = i & 255;",
        prefix: "let total = seed; for (let j = 0; j < 20; j++) { const ret = [];",
        variants: {
            forEach: "items.forEach(x => { ret.push(new Sk.builtin.int_(x)); });",
            indexed: "for (let i = 0; i < items.length; i++) ret.push(new Sk.builtin.int_(items[i]));",
            forOf: "for (const x of items) ret.push(new Sk.builtin.int_(x));",
        },
        suffix: "total += ret[(j + seed) & 1023].v + ret.length; } return total;",
    },
};
const runs = [];
let browserVersion;
for (let round = 0; round < rounds; round++) {
    for (const [name, scenario] of Object.entries(scenarios)) {
        const variants = Object.entries(scenario.variants);
        if (round % 2) variants.reverse();
        for (const [variant, body] of variants) {
            const browser = await playwright.chromium.launch({ headless: true });
            try {
                browserVersion = browser.version();
                const page = await browser.newPage();
                if (scenario.bundle) await page.addScriptTag({ path: bundle });
                const result = await page.evaluate(({ setup, source }) => {
                    const run = new Function(setup + "return function(seed) {" + source + "}")();
                    const value = run(7);
                    let checksum = 0;
                    for (let i = 0; i < 100; i++) checksum ^= run(i);
                    let start = performance.now();
                    for (let i = 0; i < 20; i++) checksum ^= run(i);
                    const iterations = Math.max(1, Math.min(100000, Math.ceil(75 / ((performance.now() - start) / 20 || .001))));
                    const samplesMs = [];
                    for (let batch = 0; batch < 7; batch++) {
                        start = performance.now();
                        for (let i = 0; i < iterations; i++) checksum ^= run(i);
                        samplesMs.push((performance.now() - start) / iterations);
                    }
                    return { value, checksum, iterations, samplesMs, medianMs: [...samplesMs].sort((a,b) => a-b)[3] };
                }, { setup: scenario.setup, source: scenario.prefix + body + scenario.suffix });
                const previous = runs.find(run => run.name === name);
                if (previous) assert.equal(result.value, previous.value);
                runs.push({ round, name, variant, ...result });
            } finally {
                await browser.close();
            }
        }
        console.log(`Round ${round + 1}/${rounds}: ${name}`);
    }
}
const summary = Object.entries(scenarios).flatMap(([name, scenario]) =>
    Object.keys(scenario.variants).map(variant => ({ name, variant,
        medianMs: median(runs.filter(run => run.name === name && run.variant === variant).map(run => run.medianMs)),
    })));
writeFileSync(resolve(option("--output", "/tmp/skulpt-javascript-loops.json")), JSON.stringify({
    measuredAt: new Date().toISOString(), browserVersion, cpu: cpus()[0].model, rounds,
    bundle: { path: bundle, sha256: createHash("sha256").update(readFileSync(bundle)).digest("hex") },
    method: "Fresh headless Chromium per scenario/variant/round, reversed variant order on alternate rounds; 100 warmups; 7 calibrated batches targeting 75ms; checksums consume results; setup excluded. Syntax microbenchmarks, not whole-program speedup predictions.",
    scenarios, summary, runs,
}, null, 2) + "\n");
console.table(summary);
