const assert = require("assert");
const fs = require("fs");
require("../support/run/require-skulpt").requireSkulpt(false);

async function test() {
    const source = fs.readFileSync("test/unittest_runner.py", "utf8");
    for (const pythonVersion of [Sk.python2, Sk.python3]) {
        let output = "";
        Sk.configure({
            read: (filename) => fs.readFileSync(filename, "utf8"),
            output: (text) => { output += text; },
            __future__: pythonVersion,
        });
        await Sk.misceval.asyncToPromise(() => Sk.importMainWithBody("<unittest runner>", false, source, true));
        assert(output.includes("Unittest runner checks passed"));
        assert(output.includes("body failure"));
        assert(output.includes("teardown failure"));
    }
    console.log("Unittest runner checks passed in Python 2 and Python 3");
}
test().catch((error) => {
    console.error(error.toString());
    process.exitCode = 1;
});
