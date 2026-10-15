import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { resolve } from "node:path";

createRequire(import.meta.url)(resolve(process.argv[2] || "dist/skulpt.min.js"));
const { Sk } = globalThis;
function pause(value) {
    const suspension = new Sk.misceval.Suspension();
    suspension.optional = true;
    suspension.resume = () => value;
    return suspension;
}
const finish = value => Sk.misceval.retryOptionalSuspensionOrThrow(value);

// Input and callback can each suspend repeatedly, including at exhaustion.
let index = 0;
const values = [pause(pause(2)), 3, pause(undefined)];
const seen = [];
const result = Sk.misceval.iterFor({ tp$iternext: () => values[index++] }, (value, previous) => {
    seen.push([value, previous]);
    return pause(pause(previous + value));
}, 10);
assert.equal(finish(result), 15);
assert.deepEqual(seen, [[2, 10], [3, 12]]);
assert.equal(index, 3);

// A suspended early exit must not request another input item.
index = 0;
const stopped = Sk.misceval.iterFor({ tp$iternext: () => ++index }, value =>
    pause(new Sk.misceval.Break(value)));
assert.equal(finish(stopped), 1);
assert.equal(index, 1);
assert.equal(Sk.misceval.iterFor({ tp$iternext: () => undefined }, () => assert.fail(), 7), 7);

// Errors after resuming propagate, rather than skipping ahead in the iterator.
index = 0;
const failed = Sk.misceval.iterFor({ tp$iternext: () => ++index }, () => {
    const suspension = pause(undefined);
    suspension.resume = () => { throw new Error("callback failed"); };
    return suspension;
});
assert.throws(() => finish(failed), /callback failed/);
assert.equal(index, 1);

// Iterator adaptors also support hosts that request synchronous completion.
const input = () => {
    const values = [pause(pause(new Sk.builtin.int_(3))), new Sk.builtin.int_(4), pause(undefined)];
    let index = 0;
    return { tp$iternext: () => values[index++] };
};
const enumerated = new Sk.builtin.enumerate(input(), 7);
assert.deepEqual(enumerated.tp$iternext(false).v.map(value => value.v), [7, 3]);
assert.deepEqual(finish(enumerated.tp$iternext(true)).v.map(value => value.v), [8, 4]);
assert.equal(finish(enumerated.tp$iternext(true)), undefined);
const zipped = new Sk.builtin.zip_([input(), input()]);
assert.deepEqual(zipped.tp$iternext(false).v.map(value => value.v), [3, 3]);
assert.deepEqual(finish(zipped.tp$iternext(true)).v.map(value => value.v), [4, 4]);
assert.equal(finish(zipped.tp$iternext(true)), undefined);
const mapped = new Sk.builtin.map_(new Sk.builtin.func(value => pause(value)), [input()]);
assert.equal(mapped.tp$iternext(false).v, 3);
assert.equal(finish(mapped.tp$iternext(true)).v, 4);
assert.equal(finish(mapped.tp$iternext(true)), undefined);

// The in-place slot must retain its receiver when a generic source suspends.
const extended = new Sk.builtin.list([new Sk.builtin.int_(1)]);
const source = { tp$iter: input };
assert.equal(finish(Sk.abstr.numberInplaceBinOp(extended, source, "Add")), extended);
assert.deepEqual(extended.v.map(value => value.v), [1, 3, 4]);

let predicateCalls = 0;
const filtered = new Sk.builtin.filter_(new Sk.builtin.func(value => {
    predicateCalls++;
    return pause(pause(new Sk.builtin.bool(value.v === 4)));
}), input());
assert.equal(filtered.tp$iternext(false).v, 4);
assert.equal(predicateCalls, 2);
assert.equal(finish(filtered.tp$iternext(true)), undefined);

// Array traversal preserves accumulator state across suspended inputs/callbacks.
const arraySeen = [];
assert.equal(finish(Sk.misceval.iterArray([pause(pause(2)), 3, pause(undefined), 99], (value, previous) => {
    arraySeen.push([value, previous]);
    return pause(pause(previous + value));
}, 10)), 15);
assert.deepEqual(arraySeen, [[2, 10], [3, 12]]);
const array = [1, 2];
assert.equal(finish(Sk.misceval.iterArray(array, value => {
    array.push(99);
    return pause(new Sk.misceval.Break(value));
})), 1);
assert.deepEqual(array, [1, 2, 99]);
assert.equal(Sk.misceval.iterArray([undefined, 99], () => assert.fail(), 7), 7);
assert.equal(Sk.misceval.iterArray([1, , 99], value => value), 1);
const growing = [1];
assert.equal(Sk.misceval.iterArray(growing, (value, previous) => {
    if (value === 1) growing.push(2);
    return previous + value;
}, 10), 13);
assert.throws(() => finish(Sk.misceval.iterArray([1, 2], () => {
    const suspension = pause(undefined);
    suspension.resume = () => { throw new Error("array callback failed"); };
    return suspension;
})), /array callback failed/);
console.log("Iteration suspension checks passed");
