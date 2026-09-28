// Compare the legacy parse/astFromParse API against the replacement bundle.
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import {resolve, dirname, join} from "node:path";
import {pathToFileURL} from "node:url";

const [currentBundle, replacementBundle, parserPath] = process.argv.slice(2);
assert.ok(parserPath, "Usage: node test/repl_compat.mjs <current-bundle> <replacement-bundle> <parser-core>");
const {parseModule, scan} = await import(pathToFileURL(resolve(parserPath)).href);
function load(path, replacement) {
    const context = vm.createContext({console, setTimeout, clearTimeout, TextEncoder, TextDecoder});
    vm.runInContext(fs.readFileSync(path, "utf8"), context);
    vm.runInContext(fs.readFileSync(join(dirname(replacementBundle), "skulpt-stdlib.js"), "utf8"), context);
    context.Sk.configure({read: path => context.Sk.builtinFiles.files[path]});
    if (replacement) context.Sk.configure({sourceParser: parseModule, sourceTokenizer: scan});
    return context.Sk;
}
const current = load(currentBundle, false);
const replacement = load(replacementBundle, true);
// This is the existing console's parse pair and final-expression rewrite.
function prepare(Sk, code) {
    let source = code.trimEnd() || "None";
    const parsed = Sk.parse("<repl>", source);
    const ast = Sk.astFromParse(parsed.cst, "?", parsed.flags);
    const last = ast.body[ast.body.length - 1];
    if (last instanceof Sk.astnodes.Expr) {
        const lines = source.split("\n");
        const line = lines[last.lineno - 1];
        lines[last.lineno - 1] = line.slice(0, last.col_offset) + "__last_ret__ = " + line.slice(last.col_offset);
        source = lines.join("\n");
    }
    return source;
}
for (const python2 of [false, true]) {
    for (const Sk of [current, replacement]) Sk.configure({__future__: {...(python2 ? Sk.python2 : Sk.python3)}});
    for (const source of ["", "value = 4\nvalue + 1", "é = 4; é + 1", "s = '😀'; len(s)",
        python2 ? "print 7\n42" : "print(7)\n42", "value = 4"]) {
        for (const Sk of [current, replacement]) Sk.configure({__future__: {...(python2 ? Sk.python2 : Sk.python3)}});
        const expected = prepare(current, source);
        const actual = prepare(replacement, source);
        assert.equal(actual, expected, source);
        async function execute(Sk, code) {
            let output = "";
            Sk.configure({__future__: {...(python2 ? Sk.python2 : Sk.python3)}, output: text => { output += text; }});
            const result = await Sk.misceval.asyncToPromise(() => Sk.importMainWithBody("repl", false, code, true));
            const value = result.$d.__last_ret__;
            return {output, value: value === undefined ? null : Sk.misceval.objectRepr(value)};
        }
        assert.deepEqual(await execute(replacement, actual), await execute(current, expected));
    }
}
console.log("Legacy REPL API and execution match across both runtimes, including Unicode columns and Python 2.");
