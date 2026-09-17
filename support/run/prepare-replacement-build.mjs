// Prepare an isolated size/compatibility experiment. Never edits the main checkout.
import assert from "node:assert/strict";
import fs from "node:fs";
import { resolve, join } from "node:path";
import { spawnSync } from "node:child_process";

const withoutTokenizer = process.argv.includes("--without-tokenizer");
const [directory, dependencies, revision = "HEAD"] = process.argv.slice(2).filter((arg) => arg !== "--without-tokenizer");
assert.ok(directory && dependencies, "Usage: node support/run/prepare-replacement-build.mjs <new-worktree> <node_modules> [revision] [--without-tokenizer]");
const destination = resolve(directory);
assert.ok(!fs.existsSync(destination), "The experiment directory must not already exist");
assert.ok(fs.statSync(dependencies).isDirectory(), "Expected an installed node_modules directory");
const added = spawnSync("git", ["worktree", "add", "--detach", destination, revision], { stdio: "inherit" });
assert.equal(added.status, 0, "Could not create experiment worktree");
fs.symlinkSync(resolve(dependencies), join(destination, "node_modules"), "dir");

const entry = join(destination, "src/main.js");
let source = fs.readFileSync(entry, "utf8");
for (const module of ["../gen/parse_tables.js", "./parser.js", "./ast.js", ...(withoutTokenizer ? ["./tokenize.js"] : [])]) {
    const line = `require("${module}");\n`;
    assert.ok(source.includes(line), `Missing expected entry: ${module}`);
    source = source.replace(line, "");
}
fs.writeFileSync(entry, source);

const bridge = join(destination, "src/structural_ast.js");
source = fs.readFileSync(bridge, "utf8");
const fallback = `        const parsed = Sk.parse(filename, source);
        return { ast: Sk.astFromParse(parsed.cst, filename, parsed.flags), flags: parsed.flags };`;
assert.ok(source.includes(fallback), "Missing expected old-frontend fallback");
source = source.replace(fallback, '        throw new Error("This experimental build requires sourceParser");');
fs.writeFileSync(bridge, source);

// This hook only changes the old AST builder's token-to-operator map.
const environment = join(destination, "src/env.js");
source = fs.readFileSync(environment, "utf8");
for (const hook of ["Sk.setupOperators", ...(withoutTokenizer ? ["Sk.token.setupTokens"] : [])]) {
    const setup = `    ${hook}(Sk.__future__.python3);\n`;
    assert.ok(source.includes(setup), `Missing expected old-frontend hook: ${hook}`);
    source = source.replace(setup, "");
}
fs.writeFileSync(environment, source);

if (withoutTokenizer) {
    assert.ok(fs.existsSync(join(destination, "src/identifier.js")), "Revision must contain the extracted identifier helper");
    const module = join(destination, "src/lib/tokenize.js");
    source = fs.readFileSync(module, "utf8");
    const modern = source.indexOf("// CPython v3.14.3 Lib/tokenize.py contracts");
    assert.ok(modern > 0, "Missing expected modern tokenize module boundary");
    source = source.slice(modern);
    const fallback = "return legacyTokenizeModule(name);";
    assert.ok(source.includes(fallback), "Missing expected legacy tokenize fallback");
    fs.writeFileSync(module, source.replace(fallback, 'throw new Error("This experimental build requires sourceTokenizer");'));
}
console.log(`Prepared ${destination}. Old tokenizer ${withoutTokenizer ? "removed" : "retained"}.`);
console.log("Build there with NODE_OPTIONS=--openssl-legacy-provider npm run build.");
