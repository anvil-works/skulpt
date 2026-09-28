const { transformSync } = require("esbuild");

module.exports = function (source) {
    const result = transformSync(source, {
        target: "es2019", format: "cjs", sourcemap: true, sourcefile: this.resourcePath
    });
    this.callback(null, result.code, JSON.parse(result.map));
};
