const { transformSync } = require("esbuild");

module.exports = function (source) {
    // Parser integer literals use the same native or JSBI backend as the runtime.
    const result = transformSync("const BigInt = JSBI.BigInt;\n" + source, {
        target: "es2019", format: "cjs", sourcemap: true, sourcefile: this.resourcePath
    });
    this.callback(null, result.code, JSON.parse(result.map));
};
