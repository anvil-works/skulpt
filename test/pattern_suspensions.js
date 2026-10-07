const assert = require("assert");
const fs = require("fs");
require("../support/run/require-skulpt").requireSkulpt(false);
const events = [];
Sk.builtins.pattern_probe = new Sk.builtin.func(function (phase, result) {
    events.push(phase.v);
    const suspension = new Sk.misceval.Suspension();
    suspension.data = { type: "pattern test" };
    suspension.resume = () => result;
    return suspension;
});
Sk.configure({ read: file => fs.readFileSync(file, "utf8"), __future__: Sk.python3 });
const source = `
from collections.abc import Sequence, Mapping
class Seq(Sequence):
    def __len__(self): return pattern_probe('len', 2)
    def __getitem__(self, i):
        if i >= 2: raise IndexError
        return pattern_probe('item', i + 1)
class Map(Mapping):
    def __len__(self): return pattern_probe('map len', 2)
    def __iter__(self): return iter(('a', 'b'))
    def __getitem__(self, key): return pattern_probe('map item', {'a': 1, 'b': 2}[key])
class Point:
    __match_args__ = ('x', 'y')
    def __getattr__(self, name): return pattern_probe(name, {'x': 1, 'y': 2}[name])
class Meta(type):
    def __instancecheck__(self, value): return pattern_probe('instance', True)
class Virtual(metaclass=Meta): pass
class Value:
    def __eq__(self, other): return pattern_probe('eq', other == 1)
class Left:
    def __eq__(self, other): return pattern_probe('left', NotImplemented)
class Right:
    def __eq__(self, other): return pattern_probe('right', True)
class Constants:
    value = Value()
    right = Right()
def run(subject):
    old = 'unchanged'
    match subject:
        case None: return None
        case [old, 99]: raise AssertionError('failed pattern stored a capture')
        case [a, b] | Point(a, b) | {'a': a, **b} if pattern_probe('guard', True):
            assert old == 'unchanged'
            return a, b
assert run(Seq()) == (1, 2)
assert run(Point()) == (1, 2)
assert run(Map()) == (1, {'b': 2})
match 1:
    case Virtual(): pass
    case _: raise AssertionError('instance check did not resume')
match 1:
    case Constants.value: pass
    case _: raise AssertionError('equality did not resume')
match Left():
    case Constants.right: pass
    case _: raise AssertionError('reflected equality did not resume')
`;
let result = Sk.importMainWithBody("<pattern suspension test>", false, source, true);
let resumes = 0;
while (result instanceof Sk.misceval.Suspension) {resumes++; result = result.resume();}
assert.strictEqual(resumes, events.length);
assert.deepStrictEqual(events, ["len", "item", "item", "len", "item", "item", "guard",
    "x", "y", "guard", "map len", "map item", "map item", "map item", "guard", "instance", "eq", "left", "right"]);
console.log("Pattern suspension tests passed");
