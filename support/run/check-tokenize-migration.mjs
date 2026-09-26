// Compare the published core lexer with CPython's public tokenize API.
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";

const [bundle] = process.argv.slice(2);
assert.ok(bundle, "Usage: node support/run/check-tokenize-migration.mjs <core-bundle>");
const { tokenize } = await import(pathToFileURL(resolve(bundle)).href);
const python = process.env.PYTHON314 || "python3.14";
function reference(program, source) {
    const result = spawnSync(python, ["-c", program], { input: JSON.stringify(source), encoding: "utf8" });
    assert.equal(result.status, 0, result.stderr || String(result.error));
    return JSON.parse(result.stdout);
}
assert.deepEqual(reference("import sys,json; print(json.dumps(list(sys.version_info[:3])))", ""), [3, 14, 3]);
const oracle = `import sys, io, tokenize, token, json
source = json.load(sys.stdin)
try:
    tokens = [dict(type=token.tok_name[t.type], string=t.string, start=t.start,
                   end=t.end, line=t.line)
              for t in tokenize.generate_tokens(io.StringIO(source).readline)]
    print(json.dumps(dict(tokens=tokens)))
except Exception as error:
    print(json.dumps(dict(error=dict(name=type(error).__name__, message=str(error)))))
`;
const sources = [
    "", "\n", "# comment", "x = 42", "é = 𝒙 + 1\n", "a\u0301 = K\n",
    "if x:\n\tpass\n", "x = [1,\n # hi\n 2]\n", 'f"{x!r:>10}"',
    't"{x}"', 'f"{{text}}{x=}"', "x=1\r\n",
];
for (const source of sources) {
    const actual = tokenize(source).map(({ type, string, start, end, line }) => ({ type, string, start, end, line }));
    assert.deepEqual({ tokens: actual }, reference(oracle, source), JSON.stringify(source));
}
console.log(`${sources.length} public generate_tokens comparisons passed`);
// Report raw-lexer/public-wrapper differences; this is not an error adapter.
for (const source of ["(", "'''hello", "if x:\n  pass\n pass\n"]) {
    let error;
    try {
        tokenize(source);
    } catch (caught) {
        error = { name: caught.name, message: caught.message, lineno: caught.lineno, offset: caught.offset };
    }
    assert.ok(error, `Expected a lexer error for ${JSON.stringify(source)}`);
    const expected = reference(oracle, source);
    assert.ok(expected.error);
    console.log(JSON.stringify({ source, cpython: expected.error, core: error }));
}
