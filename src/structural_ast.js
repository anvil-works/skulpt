/* Parse source for the compiler without constructing an intermediate AST. */

const { parseModule, scan } = require("@anvil-works/skulpt-parser/dist-core/index.js");
Sk["$scanSource"] = scan;

Sk.parseCompilerModule = function (source, filename) {
    let tree;
    try {
        tree = parseModule(source, {
            filename,
            python2Compat: !Sk.__future__.python3,
            legacyAsyncNames: true,
            printFunction: Sk.__future__.print_function
        });
    } catch (error) {
        // Missing optional capabilities and implementation failures are not Python syntax errors.
        if (!["SyntaxError", "IndentationError", "TabError"].includes(error.name)) {
            throw error;
        }
        const converted = new Sk.builtin[error.name](error.message, filename, error.lineno);
        converted.$msg = new Sk.builtin.str(error.message);
        converted.$filename = new Sk.builtin.str(filename);
        converted.$lineno = new Sk.builtin.int_(error.lineno);
        converted.$offset = new Sk.builtin.int_(error.offset);
        converted.$text = error.text == null ? Sk.builtin.none.none$ : new Sk.builtin.str(error.text);
        throw converted;
    }
    return { ast: tree, flags: 0 };
};
