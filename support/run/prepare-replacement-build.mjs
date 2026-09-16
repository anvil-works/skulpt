// Prepare an isolated size/compatibility experiment. Never edits the main checkout.
import assert from "node:assert/strict";
import fs from "node:fs";
import { resolve, join } from "node:path";
import { spawnSync } from "node:child_process";

const [directory, dependencies, revision = "HEAD"] = process.argv.slice(2);
assert.ok(directory && dependencies, "Usage: node support/run/prepare-replacement-build.mjs <new-worktree> <node_modules> [revision]");
const destination = resolve(directory);
assert.ok(!fs.existsSync(destination), "The experiment directory must not already exist");
assert.ok(fs.statSync(dependencies).isDirectory(), "Expected an installed node_modules directory");
const added = spawnSync("git", ["worktree", "add", "--detach", destination, revision], { stdio: "inherit" });
assert.equal(added.status, 0, "Could not create experiment worktree");
fs.symlinkSync(resolve(dependencies), join(destination, "node_modules"), "dir");

const entry = join(destination, "src/main.js");
let source = fs.readFileSync(entry, "utf8");
for (const module of ["../gen/parse_tables.js", "./parser.js", "./ast.js"]) {
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
const setup = "    Sk.setupOperators(Sk.__future__.python3);\n";
assert.ok(source.includes(setup), "Missing expected old-frontend operator hook");
fs.writeFileSync(environment, source.replace(setup, ""));

console.log(`Prepared ${destination}. The old tokenizer remains for Python token/tokenize modules.`);
console.log("Build there with NODE_OPTIONS=--openssl-legacy-provider npm run build.");
