// Preserve Python str.isidentifier behavior when extracting the old tokenizer.
import assert from "node:assert/strict";
import {spawnSync} from "node:child_process";
import {resolve} from "node:path";
const [baseline, candidate, parser] = process.argv.slice(2);
assert.ok(baseline && candidate && parser, "Usage: node test/identifier_compat.mjs <baseline-runtime> <candidate-runtime> <core-bundle>");
const values = ["", "_", "abc", "a1", "1a", "é", "a\u0301", "K", "𝒙", "²", "a²", "\u037a", "a·", "a b", "\ud800", "await", "print", "ᢅ", "变量"];
const source = `values = ${JSON.stringify(values)}\nfor value in values:\n    print(value.isidentifier())\n`;
const program = `const {pathToFileURL} = require('node:url');
require(process.argv[1]);
(async () => {
    const core = process.argv[2] ? await import(pathToFileURL(process.argv[2]).href) : {};
    let output = '';
    Sk.configure({sourceParser: core.parseModule || null, sourceTokenizer: core.scan || null,
        __future__: {...Sk.python3}, output: text => {output += text;}});
    await Sk.misceval.asyncToPromise(() => Sk.importMainWithBody('identifiers', false, ${JSON.stringify(source)}, true));
    process.stdout.write(output);
})().catch(error => {console.error(error); process.exitCode = 1;});`;
function run(command, args) {
    const result = spawnSync(command, args, {encoding: "utf8"});
    assert.equal(result.status, 0, result.stderr);
    return result.stdout.trim().split("\n");
}
const old = run(process.execPath, ["-e", program, resolve(baseline), ""]);
const current = run(process.execPath, ["-e", program, resolve(candidate), resolve(parser)]);
assert.deepEqual(current, old);
const python = process.env.PYTHON314 || "python3.14";
assert.deepEqual(run(python, ["-c", "import sys; print(sys.version_info[:3])"]), ["(3, 14, 3)"]);
const reference = run(python, ["-c", source]);
console.log(`${values.length} identifier results match the existing runtime`);
console.log(JSON.stringify({existingCPythonDifferences: values.flatMap((value, i) =>
    current[i] === reference[i] ? [] : [{value, skulpt: current[i], cpython: reference[i]}])}, null, 2));
