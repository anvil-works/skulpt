import { readFileSync } from "node:fs";

const fieldSource = readFileSync(new URL("field.py", import.meta.url), "utf8");

export const cases = [
    ...["list", "tuple"].flatMap(type => [
        { name: type + "-slice-long", source: `
source = ${type}(range(10000))
def benchmark():
    total = 0
    for repeat in range(100):
        copied = source[100:9900]
        total += len(copied) + copied[0] + copied[-1]
    return total
` },
        { name: type + "-slice-short", source: `
source = ${type}(range(8))
def benchmark():
    total = 0
    for repeat in range(10000):
        copied = source[1:7]
        total += len(copied) + copied[0]
    return total
` },
        { name: type + "-slice-consumed", source: `
source = ${type}(range(10000))
def benchmark():
    total = 0
    for repeat in range(100):
        copied = source[100:9900]
        total += sum(copied)
    return total
` },
        { name: type + "-slice-strided", source: `
source = ${type}(range(10000))
def benchmark():
    total = 0
    for repeat in range(100):
        copied = source[::-2]
        total += len(copied) + copied[0] + copied[-1]
    return total
` },
    ]),
    { name: "slice-custom-index-control", source: `
class Index:
    def __index__(self):
        return 1
index = Index()
source = list(range(8))
def benchmark():
    total = 0
    for repeat in range(1000):
        total += len(source[index:])
    return total
` },
    { name: "set-multi-update", source: `
first, second, third, fourth = {1, 2}, {2, 3}, {3, 4}, {4, 5}
def benchmark():
    total = 0
    for repeat in range(1000):
        values = set()
        values.update(first, second, third, fourth)
        total += len(values)
    return total
` },
    ...[["forward", "::2"], ["reverse", "::-2"]].map(([name, slice]) => ({
        name: "list-extended-assign-" + name, source: `
source = list(range(10000))
replacement = list(range(5000))
def benchmark():
    values = source.copy()
    for repeat in range(20):
        values[${slice}] = replacement
    return [len(values), values[0], values[-1], sum(values)]
` })),
    { name: "list-extended-assign-short", source: `
replacement = [4, 3, 2, 1]
def benchmark():
    values = list(range(8))
    for repeat in range(1000):
        values[::2] = replacement
    return values
` },
    { name: "list-contiguous-assign-control", source: `
source = list(range(1000))
replacement = list(range(100))
def benchmark():
    values = source.copy()
    for repeat in range(100):
        values[100:200] = replacement
    return [len(values), sum(values)]
` },
    ...[["add", "+"], ["subtract", "-"], ["multiply", "*"], ["divide", "/"]].map(([name, operator]) => ({
        name: "float-variable-" + name, source: `
pairs = [(i / 1000 + 1.0, i / 2000 + 0.1) for i in range(10000)]
def benchmark():
    total = 0.0
    for left, right in pairs:
        total += left ${operator} right
    return total
` })),
    { name: "integer-variable-subtract-control", source: `
pairs = [(i + 1000, i // 2) for i in range(10000)]
def benchmark():
    total = 0
    for left, right in pairs:
        total += left - right
    return total
` },
    { name: "power-generic-control", source: `
values = [i / 1000 for i in range(10000)]
def benchmark():
    total = 0.0
    for value in values:
        total += value ** 0.5
    return total
` },
    { name: "minmax-pairs", source: `
values = [i / 1000 for i in range(10000)]
def benchmark():
    total = 0.0
    for value in values:
        total += max(value, 0.001) + min(value, 5.0)
    return total
` },
    { name: "minmax-key-control", source: `
values = list(range(-5000, 5000))
def benchmark():
    total = 0
    for value in values:
        total += max(value, -value, key=abs)
    return total
` },
    { name: "square-floats", source: `
values = [i / 1000 for i in range(10000)]
def benchmark():
    total = 0.0
    for value in values:
        total += value ** 2
    return total
` },
    { name: "square-integers", source: `
values = list(range(10000))
def benchmark():
    total = 0
    for value in values:
        total += value ** 2
    return total
` },
    { name: "dict-copy-integers", source: `
source = dict((i, i) for i in range(1000))
def benchmark():
    total = 0
    for i in range(100):
        copied = dict(source)
        total += len(copied) + copied[999]
    return total
` },
    { name: "dict-copy-method", source: `
source = dict((str(i), i) for i in range(1000))
def benchmark():
    total = 0
    for i in range(100):
        copied = source.copy()
        total += len(copied) + copied['999']
    return total
` },
    { name: "dict-merge-control", source: `
source = dict((str(i), i) for i in range(1000))
def benchmark():
    total = 0
    for i in range(100):
        copied = {'existing': -1}
        copied.update(source)
        total += len(copied) + copied['999']
    return total
` },
    { name: "dict-copy-small", source: `
source = {'first': 1, 'second': 2, 'third': 3}
def benchmark():
    total = 0
    for i in range(10000):
        copied = dict(source)
        total += copied['third']
    return total
` },
    { name: "range-count-index", source: `
values = range(20000, 0, -2)
def benchmark():
    total = 0
    for i in range(100):
        total += values.count(2) + values.count(3) + values.index(2)
    return total
` },
    { name: "range-generic-control", source: `
values = range(0, 2000, 2)
def benchmark():
    total = 0
    for i in range(10):
        total += 1998.0 in values
        total += values.count(1999.0)
    return total
` },
    { name: "filter-bool", source: `
values = [0, 1, 0, 2] * 2500
def benchmark():
    return list(filter(bool, values))[-1]
` },
    { name: "filter-predicate", source: `
values = list(range(-5000, 5000))
def benchmark():
    return list(filter(abs, values))[-1]
` },
    { name: "sum-short", source: `
values = [1000, 2, 3]
def benchmark():
    total = 0
    for i in range(10000):
        total += sum(values)
    return total
` },
    { name: "sum-overflow", source: `
values = [9007199254740991, 1, -1] * 100
def benchmark():
    return str(sum(values))
` },
    { name: "sum-float-control", source: `
values = [1.25, 2.5, 3.75, 5.0] * 2500
def benchmark():
    return sum(values)
` },
    { name: "list-inplace-tuple", source: `
source = tuple(range(100))
def benchmark():
    result = []
    for i in range(1000):
        result += source
    return len(result), result[-1]
` },
    { name: "list-inplace-extend", source: `
source = list(range(100))
def benchmark():
    result = []
    for i in range(1000):
        result += source
    return len(result), result[-1]
` },
    { name: "range-membership", source: `
values = range(0, 20000, 2)
def benchmark():
    total = 0
    for i in range(100):
        total += 19998 in values
        total += 19999 in values
    return total
` },
    { name: "hash-tuple", source: `
key = tuple(range(64))
def benchmark():
    result = 0
    for i in range(2000):
        result += hash(key) == hash(key)
    return result
` },
    { name: "hash-bytes", source: `
key = bytes(range(256)) * 16
def benchmark():
    result = 0
    for i in range(1000):
        result += hash(key) == hash(key)
    return result
` },
    { name: "dict-copy", source: `
source = dict((str(i), i) for i in range(1000))
def benchmark():
    result = 0
    for i in range(100):
        copied = dict(source)
        result += len(copied) + copied['999']
    return result
` },
    { name: "keyword-unpack", source: `
kwargs = {'first': 1, 'second': 2, 'third': 3}
def target(first, second, third):
    return first + second + third
def benchmark():
    total = 0
    for i in range(10000):
        total += target(**kwargs)
    return total
` },
    { name: "keyword-unpack-many", source: `
kwargs = {"k" + str(i): i for i in range(100)}
def target(**kwargs):
    return len(kwargs) + kwargs["k99"]
def benchmark():
    total = 0
    for repeat in range(1000):
        total += target(**kwargs)
    return total
` },
    ...["mapping", "subclass"].map(kind => ({ name: "keyword-unpack-" + kind + "-control", source: `
${kind === "mapping" ? `class Mapping:
    def keys(self):
        return ["first", "second", "third"]
    def __getitem__(self, key):
        return {"first": 1, "second": 2, "third": 3}[key]
kwargs = Mapping()` : `class Mapping(dict):
    pass
kwargs = Mapping(first=1, second=2, third=3)`}
def target(first, second, third):
    return first + second + third
def benchmark():
    total = 0
    for repeat in range(1000):
        total += target(**kwargs)
    return total
` })),
    { name: "bytes-list", source: `
data = bytes(range(256)) * 16
def benchmark():
    total = 0
    for i in range(100):
        result = list(data)
        total += result[i] + len(result)
    return total
` },
    { name: "bytes-search", source: `
data = b'abc' * 1000 + b'abz'
def benchmark():
    total = 0
    for i in range(100):
        total += data.find(b'abz') + data.rfind(b'xyz')
    return total
` },
    { name: "lookup-globals", source: `
VALUE = 123
def benchmark():
    total = 0
    for i in range(10000):
        total += VALUE + VALUE + VALUE + VALUE
    return total
` },
    { name: "lookup-locals", source: `
def benchmark():
    value = 123
    total = 0
    for i in range(10000):
        total += value + value + value + value
    return total
` },
    { name: "lookup-attributes", source: `
class Value:
    def __init__(self):
        self.value = 123
        self.other = 456
obj = Value()
def benchmark():
    total = 0
    for i in range(10000):
        total += obj.value + obj.other
    return total
` },
    { name: "lookup-methods", source: `
class Value:
    def __init__(self):
        self.value = 123
    def get(self):
        return self.value
obj = Value()
def benchmark():
    total = 0
    for i in range(10000):
        total += obj.get()
    return total
` },
    { name: "lookup-bound-methods", source: `
class Value:
    def __init__(self):
        self.value = 123
    def get(self):
        return self.value
obj = Value()
def benchmark():
    total = 0
    for i in range(10000):
        method = obj.get
        total += method()
    return total
` },
    { name: "lookup-property-call", source: `
def get_value():
    return 123
class Value:
    @property
    def method(self):
        return get_value
obj = Value()
def benchmark():
    total = 0
    for i in range(10000):
        total += obj.method()
    return total
` },
    { name: "iteration-list", source: `
values = list(range(10000))
def benchmark():
    total = 0
    for value in values:
        total += value
    return total
` },
    { name: "iteration-tuples", source: `
rows = [(1, 2, 3, 4)] * 2500
def benchmark():
    total = 0
    for row in rows:
        for value in row:
            total += value
    return total
` },
    { name: "iteration-sum", source: `
values = list(range(10000))
def benchmark():
    return sum(values)
` },
    { name: "iteration-enumerate", source: `
values = list(range(10000))
def benchmark():
    total = 0
    for index, value in enumerate(values):
        total += index + value
    return total
` },
    { name: "iteration-zip", source: `
values = list(range(10000))
def benchmark():
    total = 0
    for left, right in zip(values, values):
        total += left + right
    return total
` },
    { name: "iteration-zip-four", source: `
values = list(range(10000))
def benchmark():
    rows = list(zip(values, values, values, values))
    return [len(rows), rows[-1]]
` },
    { name: "iteration-map-two", source: `
values = list(range(10000))
def add(left, right):
    return left + right
def benchmark():
    return sum(map(add, values, values))
` },
    { name: "iteration-map", source: `
values = list(range(-5000, 5000))
def benchmark():
    return sum(map(abs, values))
` },
    { name: "iteration-filter", source: `
values = [0, 1, 0, 2, 0, 3, 0, 4] * 1250
def benchmark():
    return sum(filter(None, values))
` },
    { name: "iteration-comprehension", source: `
values = list(range(10000))
def benchmark():
    return sum([value for value in values])
` },
    { name: "iteration-generator", source: `
values = list(range(10000))
def benchmark():
    return sum(value for value in values)
` },
    { name: "list-pop", source: `
def benchmark():
    values = list(range(10000))
    total = 0
    while values:
        total += values.pop()
    return total
` },
    { name: "list-extend", source: `
def benchmark():
    source = list(range(100))
    values = []
    for i in range(1000):
        values.extend(source)
    return len(values), values[-1]
` },
    { name: "list-self-extend", source: `
def benchmark():
    total = 0
    for i in range(10000):
        values = [1, 2, 3, 4]
        values.extend(values)
        total += len(values)
    return total
` },
    { name: "tuple-extend", source: `
def benchmark():
    source = tuple(range(100))
    values = []
    for i in range(1000):
        values.extend(source)
    return len(values), values[-1]
` },
    { name: "builtin-defaults", source: `
def benchmark():
    values = [1, 2, 3]
    total = 0
    for i in range(10000):
        total += sum(values)
    return total
` },
    { name: "string-processing", source: `
def benchmark():
    text = "  alpha,beta,gamma  "
    total = 0
    for i in range(10000):
        total += len(text.strip().split(","))
    return total
` },
    { name: "field", source: fieldSource },
    { name: "field-long", longRunning: true, source: fieldSource + "\nbenchmark = benchmark_long\n" },
    { name: "methods", source: `
class Counter:
    def __init__(self):
        self.value = 0
    def add(self, value):
        self.value += value
        return self.value
def benchmark():
    counter = Counter()
    total = 0
    for i in range(10000):
        total += counter.add(i % 7)
    return total
` },
    { name: "arithmetic", source: `
def benchmark():
    x = 0.25
    for i in range(10000):
        x = (x + i % 17) * 0.999 - 0.125
    return x
` },
    { name: "int-arithmetic", source: `
def benchmark():
    value = 12345
    for i in range(10000):
        value = (value * 17 + 13) % 1000000007
    return value
` },
    { name: "list-indexing", source: `
def benchmark():
    values = [1.25, 2.5, 3.75, 5.0]
    total = 0.0
    for i in range(10000):
        total += values[0] + values[1] + values[2] + values[3]
    return total
` },
    { name: "overloaded-arithmetic", source: `
class Value:
    def __init__(self, value):
        self.value = value
    def __add__(self, other):
        return Value(self.value + other.value)
def benchmark():
    value = Value(0)
    step = Value(1)
    for i in range(5000):
        value = value + step
    return value.value
` },
    { name: "binary-trees", source: `
# The make/check recursion from test/bench/binary-trees.py, at a practical size.
def make_tree(item, depth):
    if not depth:
        return item, None, None
    item2 = item + item
    depth -= 1
    return item, make_tree(item2 - 1, depth), make_tree(item2, depth)
def check_tree(node):
    item, left, right = node
    if not left:
        return item
    return item + check_tree(left) - check_tree(right)
def benchmark():
    check = 0
    for i in range(40):
        check += check_tree(make_tree(i, 7))
    return check
` },
    { name: "literal-membership", source: `
def benchmark():
    total = 0
    for i in range(10000):
        if i % 10 in [1, 3, 5, 7, 9]:
            total += 1
        for step in [1, 2, 3]:
            total += step
    return total
` },
    { name: "constants", source: `
def benchmark():
    total = 0
    for i in range(10000):
        total += (2 + 3 * 4) + (1 << 8) + 2 ** 10
    return total
` },
    { name: "many-constants", source:
        Array.from({ length: 1000 }, (_, i) => `value_${i} = "constant_${i}"`).join("\n") +
        "\ndef benchmark():\n    return value_999\n" },
];
