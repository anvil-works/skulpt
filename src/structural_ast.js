/* Parse source into the modern AST using the configured Python compatibility mode. */

const { parseExpression, parseModule, scan } = require("@anvil-works/skulpt-parser/dist-core/index.js");
Sk["$scanSource"] = scan;

/**
 * Parse a module into plain AST nodes with UTF-8 byte columns.
 * Uses Sk.configure's Python mode and raises Skulpt syntax errors.
 * @param {string} source
 * @param {string} filename
 */
function parseSource(source, filename, expression) {
    try {
        return (expression ? parseExpression : parseModule)(source, {
            filename,
            pythonVersion: Sk.__future__.python3 ? 3 : 2,
            asyncAwaitAsIdentifiers: true,
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
}

Sk.parseModule = function (source, filename) {
    return parseSource(source, filename, false);
};
Sk.parseExpression = function (source, filename) {
    return parseSource(source, filename, true);
};
Sk.exportSymbol("Sk.parseModule", Sk.parseModule);
Sk.exportSymbol("Sk.parseExpression", Sk.parseExpression);
