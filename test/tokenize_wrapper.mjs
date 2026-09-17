// Exercise Python's real token/tokenize modules against CPython 3.14.3.
import assert from "node:assert/strict";
import {createRequire} from "node:module";
import {resolve, dirname, join} from "node:path";
import {pathToFileURL} from "node:url";
import {spawnSync} from "node:child_process";
const require = createRequire(import.meta.url);
const bundle = resolve(process.argv[3] || "dist/skulpt.min.js");
require(bundle);
require(join(dirname(bundle), "skulpt-stdlib.js"));
assert.ok(process.argv[2], "Usage: node test/tokenize_wrapper.mjs <core-bundle> [skulpt-bundle]");
const {parseModule, scan} = await import(pathToFileURL(resolve(process.argv[2])).href);
const python = process.env.PYTHON314 || "python3.14";
const version = spawnSync(python, ["-c", "import sys; print(sys.version_info[:3])"], {encoding: "utf8"});
assert.equal(version.status, 0, version.stderr);
assert.equal(version.stdout.trim(), "(3, 14, 3)");
const prelude = `import token, tokenize

def reader(source):
    lines = iter(source.splitlines(True))
    return lambda: next(lines)
`;
const cases = [
    `print(tokenize.__name__, tokenize.TokenInfo.__module__)
print(sorted(token.tok_name.items()))
print(sorted(token.EXACT_TOKEN_TYPES.items()))
print(sorted(token.__all__))
for name in ['OP', 'ENCODING', 'COMMENT', 'NL', 'COLONEQUAL', 'FSTRING_START', 'TSTRING_START', 'NT_OFFSET', 'N_TOKENS']:
    n = getattr(token, name)
    print(name, n, token.tok_name[n])
print(token.EXACT_TOKEN_TYPES[':='], token.EXACT_TOKEN_TYPES['!'])
print(token.ISTERMINAL(token.OP), token.ISNONTERMINAL(token.NT_OFFSET), token.ISEOF(token.ENDMARKER))`,
    `for source in ['', '# comment', 'é = 𝒙 + 1\\n', 'if x:\\n    pass\\n', 'x = [1,\\n # hi\\n 2]\\n', 'f"{x!r:>10}"', 't"{x}"', 'x=1\\r\\n']:
    for t in tokenize.generate_tokens(reader(source)):
        print(token.tok_name[t.type], tuple(t), t.exact_type)`,
    `t = next(tokenize.generate_tokens(reader('abc + 1')))
print(t._fields, t.type, t.string, t.start, t.end, t.line, isinstance(t, tuple))
print(t._replace(string='def').string)
print(tokenize.TokenInfo._make(t) == t)
print(tokenize.TokenInfo(type=t.type, string=t.string, start=t.start, end=t.end, line=t.line) == t)`,
    `for source in [b'', b'x = 1\\n', b'\\xef\\xbb\\xbfx = 1\\n', b'# coding: utf-8\\nx = 1\\n', b'"\\xef\\xbf\\xbd"\\n', b'x=1\\n# \\xef\\xbb\\xbf\\n']:
    print([(t.type, [ord(c) for c in t.string], t.start, t.end, [ord(c) for c in t.line]) for t in tokenize.tokenize(reader(source))])`,
    `for source in ['(', "'''hello", 'if x:\\n  pass\\n pass\\n']:
    try:
        list(tokenize.generate_tokens(reader(source)))
    except tokenize.TokenError as e:
        print(type(e).__name__, e.args)
    except IndentationError as e:
        print(type(e).__name__, e.msg, e.lineno, e.offset)`,
    `calls = []
def readline():
    calls.append(1)
    return ''
g = tokenize.generate_tokens(readline)
print(calls, iter(g) is g)
print(list(g), calls)
print(list(g))`,
    `def bad():
    raise ValueError('reader failed')
try:
    list(tokenize.generate_tokens(bad))
except ValueError as e:
    print(str(e))
for r in [lambda: 42, lambda: b'x']:
    try:
        next(tokenize.generate_tokens(r))
    except TypeError:
        print('TypeError')`,
];
async function run(source, python3=true, sourceTokenizer=scan) {
    let output = "";
    Sk.configure({sourceParser: parseModule, sourceTokenizer, __future__: {...(python3 ? Sk.python3 : Sk.python2)},
        read: (name) => {if (!(name in Sk.builtinFiles.files)) throw new Error(name); return Sk.builtinFiles.files[name];},
        output: (text) => {output += text;}});
    await Sk.misceval.asyncToPromise(() => Sk.importMainWithBody("tokenize_wrapper", false, source, true));
    return output;
}
for (const body of cases) {
    const source = prelude + "\n" + body + "\n";
    const expected = spawnSync(python, ["-c", source], {encoding: "utf8"});
    assert.equal(expected.status, 0, expected.stderr);
    assert.equal(await run(source), expected.stdout, source);
}
// Existing Skulpt extension: decoded text passed to tokenize, including Python 2 syntax.
const legacy = prelude + `
print([t.string for t in tokenize.tokenize(reader('print 0755L <> 1\\n'))])
`;
assert.equal(await run(legacy, false), "['UTF-8', 'print', '0755L', '<>', '1', '\\n', '']\n");
const unsupported = prelude + `
try:
    list(tokenize.tokenize(reader(b'# coding: latin-1\\nx=1\\n')))
except SyntaxError as e:
    print(e.msg)
`;
assert.equal(await run(unsupported), 'tokenize currently supports only UTF-8 byte input\n');
console.log(`${cases.length} CPython module comparisons and two Skulpt compatibility checks passed`);
