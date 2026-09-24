// Compare the original AST fixture sources through the two production frontends.
import assert from "node:assert/strict";
import fs from "node:fs";
import { createRequire } from "node:module";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";

const [parserPath, bundle = "dist/skulpt.js"] = process.argv.slice(2);
assert.ok(parserPath, "Usage: node test/ast_compat.mjs <parser-core-bundle> [skulpt-bundle]");
createRequire(import.meta.url)(resolve(bundle));
const { parseModule } = await import(pathToFileURL(resolve(parserPath)).href);
const { Sk } = globalThis;

// Compare declared AST fields, as the historical .trans dumps did, not locations
// or constructor identity. Normalize only these known equivalent old AST forms.
// In particular, keep Try.finalbody null distinct from an empty array: that
// difference changes compiler control flow and previously caused a regression.
function astFields(node) {
    if (node == null) return null;
    if (Array.isArray(node)) return node.map(astFields);
    if (node.prototype?._isenum) return node.prototype._astname;
    if (node._astname) {
        const result = { _type: node._astname };
        for (let i = 0; i < node._fields.length; i += 2) {
            result[node._fields[i]] = astFields(node._fields[i + 1](node));
        }
        if (node._astname === "comprehension") {
            result.ifs ??= [];
            result.is_async ??= 0;
        }
        if (node._astname === "arguments") {
            result.kwonlyargs ??= [];
            result.defaults ??= [];
        }
        if (node._astname === "Slice" && node.step?._astname === "NameConstant" &&
            node.step.value === Sk.builtin.none.none$) {
            result.step = null;
        }
        if (node._astname === "ExtSlice" && node.dims.every((dim) => dim._astname === "Index")) {
            return { _type: "Index", value: {
                _type: "Tuple", elts: node.dims.map((dim) => astFields(dim.value)), ctx: "Load"
            } };
        }
        return result;
    }
    if (node.ob$type) return { type: Sk.abstr.typeName(node), repr: Sk.misceval.objectRepr(node) };
    return node;
}

const sources = fs.readdirSync("test/run").filter((name) => name.endsWith(".py")).sort();
const failures = [];
let matched = 0;
let extensions = 0;
for (const name of sources) {
    const source = fs.readFileSync(`test/run/${name}`, "utf8");
    try {
        Sk.configure({ __future__: { ...Sk.python2 }, sourceParser: null });
        if (name === "t905.py") {
            // Existing policy: do not reject working syntax solely for Python 2.
            assert.throws(() => Sk.parseCompilerModule(source, name), (error) =>
                error instanceof Sk.builtin.SyntaxError &&
                String(error).includes("Annotated assignment is not supported in Python 2"));
            Sk.configure({ __future__: { ...Sk.python2 }, sourceParser: parseModule });
            assert.equal(Sk.parseCompilerModule(source, name).ast.body[0]._astname, "AnnAssign");
            assert.doesNotThrow(() => Sk.compile(source, name, "exec", true));
            extensions++;
            continue;
        }
        const expected = astFields(Sk.parseCompilerModule(source, name).ast);
        Sk.configure({ __future__: { ...Sk.python2 }, sourceParser: parseModule });
        const actual = astFields(Sk.parseCompilerModule(source, name).ast);
        assert.deepEqual(actual, expected);
        matched++;
    } catch (error) {
        failures.push(name);
        console.error(`${name}: ${error.stack || error}`);
    }
}
console.log(JSON.stringify({ sources: sources.length, matched, extensions, failed: failures.length }));
assert.equal(failures.length, 0, `AST compatibility failures: ${failures.join(", ")}`);
