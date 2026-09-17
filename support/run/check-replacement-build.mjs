// Check the isolated replacement build, including actual standard-library loading.
import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { resolve, dirname, join } from "node:path";
import { pathToFileURL } from "node:url";
import { spawnSync } from "node:child_process";

const [bundle, parser] = process.argv.slice(2);
assert.ok(bundle && parser, "Usage: node support/run/check-replacement-build.mjs <skulpt-bundle> <core-bundle> [--without-tokenizer]");
const require = createRequire(import.meta.url);
require(resolve(bundle));
require(join(dirname(resolve(bundle)), "skulpt-stdlib.js"));
const { Sk } = globalThis;
for (const name of ["parse", "Parser", "astFromParse", "astDump", "parseTreeDump", "ParseTables", "OpMap", "setupOperators"]) {
    assert.equal(typeof Sk[name], "undefined", `${name} still present`);
}
assert.equal(typeof Sk._tokenize, process.argv.includes("--without-tokenizer") ? "undefined" : "function");
assert.equal(typeof Sk.token.isIdentifier, "function");
Sk.configure({ __future__: { ...Sk.python3 } });
assert.throws(() => Sk.compile("x = 1", "missing.py", "exec", true), /requires sourceParser/);

const { parseModule, scan } = await import(pathToFileURL(resolve(parser)).href);
const python = process.env.PYTHON314 || "python3.14";
const version = spawnSync(python, ["-c", "import sys; print(sys.version_info[:3])"], {encoding: "utf8"});
assert.equal(version.status, 0, version.stderr || String(version.error));
assert.equal(version.stdout.trim(), "(3, 14, 3)");
const sources = [
    "import textwrap\nprint(textwrap.fill('alpha beta gamma delta', width=10))\nprint(textwrap.dedent('  a\\n  b'))\n",
    "x = 'café'\nprint(eval(\"f'{x!r}'\"))\nexec('y = 5')\nprint(y)\n",
];
for (const source of sources) {
    let output = "";
    Sk.configure({sourceParser: parseModule, sourceTokenizer: scan, __future__: {...Sk.python3},
        read: (name) => Sk.builtinFiles.files[name], output: (text) => { output += text; }});
    await Sk.misceval.asyncToPromise(() => Sk.importMainWithBody("replacement", false, source, true));
    const reference = spawnSync(python, ["-c", source], {encoding: "utf8"});
    assert.equal(reference.status, 0, reference.stderr);
    assert.equal(output, reference.stdout);
}
console.log("Replacement API boundaries and two CPython execution comparisons passed");
