import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";

const context = { console, setTimeout, clearTimeout };
context.window = context; context.self = context;
vm.createContext(context);
vm.runInContext(fs.readFileSync(process.argv[2] ?? "dist/skulpt.min.js", "utf8"), context);
// A source overlay permits focused compiler iteration without rebuilding bundles.
for (const overlay of process.argv.slice(3)) vm.runInContext(fs.readFileSync(overlay, "utf8"), context);
const Sk = context.Sk;
Sk.configure({ __future__: Sk.python3 });
Sk.python3.super_args = true;
const load = source => Sk.misceval.asyncToPromise(() => Sk.importMainWithBody("live_test", false, source, true));
const get = (obj, name) => Sk.abstr.gattr(obj, new Sk.builtin.str(name));
const call = (fn, ...args) => Sk.ffi.remapToJs(Sk.misceval.callsimArray(fn, args.map(Sk.ffi.remapToPy)));

// Captured callbacks and from-import-like references survive; defaults and mutable
// globals are not initialized a second time. Adding a definition is visible too.
const before = `
def default():
    global initialized
    initialized += 1
    return 3
initialized = 0
state = [5]
def helper(x=default()):
    return x + state[0]
class Form:
    def click(self):
        return helper()
form = Form()
callback = form.click
imported = helper
`;
const after = before.replace("x + state[0]", "x * state[0]").replace("return helper()", "return helper() + 10") + "\ndef added():\n    return 9\n";
const module = await load(before);
const form = module.$d.form, helper = module.$d.helper;
Sk.globals = {__name__: new Sk.builtin.str("other_repl_module")};
const update = Sk.prepareModuleUpdate(before, after, "live_test.py", {globals: module.$d});
assert.equal(call(module.$d.callback), 8);
update.apply();
assert.equal(call(module.$d.callback), 25);

// Definition provenance and initialization ordering matter even when the bound
// object is another Python function. Reject without changing either callable.
const rebound = "def one():\n    return 1\ndef two():\n    return 2\none = two\n";
const reboundModule = await load(rebound);
assert.throws(() => Sk.prepareModuleUpdate(rebound, rebound.replace("return 1", "return 3"), "live_test.py", {globals: reboundModule.$d}), /callable was rebound/);
assert.equal(call(reboundModule.$d.two), 2);
const ordered = "def helper():\n    return 1\nalias = helper\n";
const orderedModule = await load(ordered);
assert.throws(() => Sk.prepareModuleUpdate(ordered, "alias = helper\ndef helper():\n    return 1\n", "live_test.py", {globals: orderedModule.$d}), /initialization or imports/);
const duplicates = "def f(x=1):\n    return x+10\ndef f(x=2):\n    return x+20\ncaptured=f\n";
const duplicateModule = await load(duplicates);
assert.throws(() => Sk.prepareModuleUpdate(duplicates, "def f(x=1):\n    return x+11\ncaptured=f\n", "live_test.py", {globals: duplicateModule.$d}), /multiple definitions/);
assert.equal(call(duplicateModule.$d.captured), 22);
assert.equal(call(module.$d.imported), 15);
assert.equal(module.$d.helper, helper);
assert.equal(module.$d.form, form);
assert.equal(Sk.ffi.remapToJs(module.$d.initialized), 1);
assert.equal(call(module.$d.added), 9);
assert.equal(module.$d.added.$module.v, module.$d.__name__.v);

// Class context (private names and zero-argument super) is retained without
// recreating a class or running __init_subclass__.
const classes = `
class Base:
    def value(self):
        return 2
class Child(Base):
    def __init__(self):
        self.__value = 4
    def value(self):
        return super().value() + self.__value
child = Child()
captured = child.value
`;
const childModule = await load(classes);
Sk.prepareModuleUpdate(classes, classes.replace("+ self.__value", "* self.__value"), "live_test.py", {globals: childModule.$d}).apply();
assert.equal(call(childModule.$d.captured), 8);

// Nested functions created by the replacement use its new code and original
// closure cells. A closure created by an older invocation stays an older object.
const closures = "def make():\n    value = 3\n    def inner():\n        return value + 1\n    return inner\nold = make()\n";
const closureModule = await load(closures);
Sk.prepareModuleUpdate(closures, closures.replace("value + 1", "value + 2"), "live_test.py", {globals: closureModule.$d}).apply();
assert.equal(call(closureModule.$d.old), 4);
assert.equal(call(Sk.misceval.callsimArray(closureModule.$d.make, [])), 5);

const reserved = "def constructor():\n    return 1\ncaptured = constructor\n";
const reservedModule = await load(reserved);
Sk.prepareModuleUpdate(reserved, reserved.replace("return 1", "return 2"), "live_test.py", {globals: reservedModule.$d}).apply();
assert.equal(call(reservedModule.$d.captured), 2);

// Rejected batches do not install an otherwise-compatible earlier definition.
assert.throws(() => Sk.prepareModuleUpdate(after, after.replace("x * state[0]", "x - state[0]").replace("state = [5]", "state = [7]"), "live_test.py", {globals: module.$d}));
assert.equal(call(module.$d.imported), 15);
assert.throws(() => Sk.prepareModuleUpdate(after, after.replace("x=default()", "x=default()+1"), "live_test.py", {globals: module.$d}), /literal defaults/);
assert.throws(() => Sk.prepareModuleUpdate(after, after + "\ndef invalid(:\n", "live_test.py", {globals: module.$d}));
assert.equal(call(module.$d.callback), 25);
assert.throws(() => Sk.prepareModuleUpdate(after, after + "\ndef annotated(x: missing):\n    return x\n", "live_test.py", {globals: module.$d}));

// An old suspended invocation completes its old body; a subsequent invocation
// sees the new body. No active frame is rewritten by an update.
const suspendedSource = "def work():\n    pause()\n    return 1\n";
const suspended = await load(suspendedSource);
let resume;
suspended.$d.pause = new Sk.builtin.func(() => Sk.misceval.promiseToSuspension(new Promise(r => { resume = r; })));
const inFlight = Sk.misceval.asyncToPromise(() => Sk.misceval.callsimOrSuspendArray(suspended.$d.work, []));
Sk.prepareModuleUpdate(suspendedSource, suspendedSource.replace("return 1", "return 2"), "live_test.py", {globals: suspended.$d}).apply();
resume(Sk.builtin.none.none$);
assert.equal(Sk.ffi.remapToJs(await inFlight), 1);
suspended.$d.pause = new Sk.builtin.func(() => Sk.builtin.none.none$);
assert.equal(call(suspended.$d.work), 2);
console.log("Live updates: captured references, initialization, class context, rejection and suspension checks passed");

// Docstring metadata allocates constants in the enclosing module/class scope.
// Updating documented functions and captured methods must retain that setup.
const documented = `
def message():
    """Module function documentation."""
    return 1
class Form:
    def click(self):
        """Click handler documentation."""
        return message() + 10
form = Form()
captured = form.click
`;
const documentedModule = await load(documented);
Sk.prepareModuleUpdate(documented, documented.replace('return 1', 'return 2').replace('+ 10', '+ 20'), 'live_test.py', {globals: documentedModule.$d}).apply();
assert.equal(call(documentedModule.$d.message), 2);
assert.equal(call(documentedModule.$d.captured), 22);
assert.equal(get(documentedModule.$d.message, '__doc__').v, 'Module function documentation.');
assert.equal(get(get(documentedModule.$d.Form, 'click'), '__doc__').v, 'Click handler documentation.');
console.log('Documented function and captured method updates passed');

// Constructor edits require an explicit Form reset, without rerunning module
// initialization or changing existing instances during preparation.
const constructorSource = "class Form:\n    def __init__(self):\n        self.value = 1\n    def click(self):\n        return self.value\nform = Form()\n";
const constructorModule = await load(constructorSource);
const constructorEdit = constructorSource.replace("self.value = 1", "self.value = 2");
assert.throws(() => Sk.prepareModuleUpdate(constructorSource, constructorEdit, "live_test.py", {globals: constructorModule.$d}));
const reset = Sk.prepareModuleUpdate(constructorSource, constructorEdit, "live_test.py", {globals: constructorModule.$d, formClass: "Form"});
assert.equal(JSON.stringify(reset.resetClasses), '["Form"]');
assert.equal(call(get(constructorModule.$d.form, "click")), 1);
reset.apply();
assert.equal(call(get(constructorModule.$d.form, "click")), 1);
assert.equal(call(get(Sk.misceval.callsimArray(constructorModule.$d.Form, []), "click")), 2);
console.log("Live updates: explicit Form constructor boundary checks passed");

// Property descriptors and extracted accessors keep their identities, including
// setter/deleter changes, so existing instances and captures see the new bodies.
const properties = `
class Model:
    def __init__(self):
        self.value = 2
    @property
    def amount(self):
        return self.value + 1
    @amount.setter
    def amount(self, value):
        self.value = value + 2
    @amount.deleter
    def amount(self):
        self.value = 0
model = Model()
get_amount = Model.amount.fget
set_amount = Model.amount.fset
del_amount = Model.amount.fdel
`;
const propertyModule = await load(properties);
const descriptor = get(propertyModule.$d.Model, 'amount');
const changedProperties = properties.replace('self.value + 1', 'self.value + 10').replace('value + 2', 'value + 20').replace('self.value = 0', 'self.value = 100');
Sk.prepareModuleUpdate(properties, changedProperties, 'live_test.py', {globals: propertyModule.$d}).apply();
assert.equal(get(propertyModule.$d.Model, 'amount'), descriptor);
assert.equal(Sk.ffi.remapToJs(Sk.misceval.callsimArray(propertyModule.$d.get_amount, [propertyModule.$d.model])), 12);
Sk.misceval.callsimArray(propertyModule.$d.set_amount, [propertyModule.$d.model, new Sk.builtin.int_(3)]);
assert.equal(get(propertyModule.$d.model, 'amount').v, 33);
Sk.misceval.callsimArray(propertyModule.$d.del_amount, [propertyModule.$d.model]);
assert.equal(get(propertyModule.$d.model, 'amount').v, 110);
assert.throws(() => Sk.prepareModuleUpdate(changedProperties, changedProperties.replace('@amount.setter', '@amount.getter'), 'live_test.py', {globals: propertyModule.$d}), /Restart required/);

// Compilation captures a source version once. A suspended old frame and its
// traceback keep that version after a replacement is compiled and installed.
const versionBefore = 'def work():\n    pause()\n    raise ValueError("old")\n';
const versionAfter = versionBefore.replace('"old"', '"new"');
Sk.getSourceVersion = (_filename, source) => source === versionBefore ? 'old-source' : 'new-source';
const versionModule = await load(versionBefore);
let versionResume;
versionModule.$d.pause = new Sk.builtin.func(() => Sk.misceval.promiseToSuspension(new Promise(r => { versionResume = r; })));
const oldSuspension = Sk.misceval.callsimOrSuspendArray(versionModule.$d.work, []);
assert.equal(oldSuspension.sourceVersion, 'old-source');
Sk.prepareModuleUpdate(versionBefore, versionAfter, 'live_test.py', {globals: versionModule.$d}).apply();
versionResume(Sk.builtin.none.none$);
await assert.rejects(Sk.misceval.asyncToPromise(() => oldSuspension), error => {
    assert.equal(error.traceback.at(-1).sourceVersion, 'old-source');
    return true;
});
const newSuspension = Sk.misceval.callsimOrSuspendArray(versionModule.$d.work, []);
assert.equal(newSuspension.sourceVersion, 'new-source');
versionResume(Sk.builtin.none.none$);
await assert.rejects(Sk.misceval.asyncToPromise(() => newSuspension), error => {
    assert.equal(error.traceback.at(-1).sourceVersion, 'new-source');
    return true;
});
delete Sk.getSourceVersion;
console.log('Property identity and compiled source version checks passed');

const batchModule = (name, source, module, isPackage = false) => ({name, source, filename: name + '.py', globals: module.$d, isPackage});
const constantSource = 'RATE = 2\ndef price():\n    return RATE * 10\n';
const constantModule = await load(constantSource);
const constantFunction = constantModule.$d.price;
Sk.prepareModuleUpdates([{name: 'live_test', after: constantSource.replace('RATE = 2', 'RATE = 3')}], {
    modules: [batchModule('live_test', constantSource, constantModule)]
}).apply();
assert.equal(call(constantFunction), 30);
assert.equal(constantModule.$d.price, constantFunction);
const extractedSource = constantSource + 'saved = RATE\n';
const extractedModule = await load(extractedSource);
assert.throws(() => Sk.prepareModuleUpdates([{name: 'live_test', after: extractedSource.replace('RATE = 2', 'RATE = 3')}], {
    modules: [batchModule('live_test', extractedSource, extractedModule)]
}), /captured during initialization/);
assert.equal(extractedModule.$d.RATE.v, 2);

// Real imports expose the stale from-import boundary. Both provider and dependent
// initialization can rerun only when explicitly marked; order is provider first.
const providerSource = '# anvil: live-update-safe\nRATE = 2\ndef price():\n    return RATE * 10\n';
const consumerSource = '# anvil: live-update-safe\nfrom provider import RATE, price\nruns = globals().get("runs", 0) + 1\ntotal = RATE + 1\ndef value():\n    return total + price()\n';
const previousRead = Sk.read;
Sk.read = filename => filename.endsWith('/provider.py') || filename === 'provider.py' ? providerSource : previousRead(filename);
const consumerModule = await load(consumerSource);
const providerModule = Sk.sysmodules.quick$lookup(new Sk.builtin.str('provider'));
const capturedPrice = consumerModule.$d.price, capturedValue = consumerModule.$d.value;
const importedBatch = Sk.prepareModuleUpdates([{name: 'provider', after: providerSource.replace('RATE = 2', 'RATE = 4')}], {
    modules: [batchModule('live_test', consumerSource, consumerModule), batchModule('provider', providerSource, providerModule)]
});
await Sk.misceval.asyncToPromise(importedBatch.apply);
assert.equal(consumerModule.$d.runs.v, 2);
assert.equal(call(capturedValue), 45);
assert.equal(providerModule.$d.price, capturedPrice);
assert.equal(consumerModule.$d.value, capturedValue);
assert.throws(() => Sk.prepareModuleUpdates([{name: 'provider', after: providerSource.replace('RATE = 2', 'RATE = 5')}], {
    modules: [batchModule('live_test', consumerSource.replace('# anvil: live-update-safe\n', ''), consumerModule), batchModule('provider', providerSource, providerModule)]
}), /imported constants were captured/);
Sk.read = previousRead;

// Opaque module aliases and recreated class identities deliberately fall back.
const opaqueSource = 'import provider\nmodules = [provider]\n';
Sk.read = filename => filename.endsWith('/provider.py') || filename === 'provider.py' ? providerSource : previousRead(filename);
const opaqueModule = await load(opaqueSource);
const opaqueProvider = Sk.sysmodules.quick$lookup(new Sk.builtin.str('provider'));
assert.throws(() => Sk.prepareModuleUpdates([{name: 'provider', after: providerSource.replace('RATE = 2', 'RATE = 6')}], {
    modules: [batchModule('live_test', opaqueSource, opaqueModule), batchModule('provider', providerSource, opaqueProvider)]
}), /module reference escapes/);
Sk.read = previousRead;
const rerunClasses = '# anvil: live-update-safe\nstate = [1]\nclass Model:\n    pass\n';
const rerunClassModule = await load(rerunClasses);
assert.throws(() => Sk.prepareModuleUpdates([{name: 'live_test', after: rerunClasses.replace('[1]', '[2]')}], {
    modules: [batchModule('live_test', rerunClasses, rerunClassModule)]
}), /replace live classes/);
console.log('Literal constants, imported captures and explicit ordered module reruns passed');

const defaultConstant = 'RATE = 2\ndef price(value=RATE):\n    return value + 1\n';
const defaultModule = await load(defaultConstant);
assert.throws(() => Sk.prepareModuleUpdates([{name: 'live_test', after: defaultConstant.replace('RATE = 2', 'RATE = 3')}], {
    modules: [batchModule('live_test', defaultConstant, defaultModule)]
}), /captured during initialization/);
const markedDefault = '# anvil: live-update-safe\n' + defaultConstant;
const markedDefaultModule = await load(markedDefault);
const defaultFunction = markedDefaultModule.$d.price;
await Sk.misceval.asyncToPromise(Sk.prepareModuleUpdates([{name: 'live_test', after: markedDefault.replace('RATE = 2', 'RATE = 3')}], {
    modules: [batchModule('live_test', markedDefault, markedDefaultModule)]
}).apply);
assert.equal(markedDefaultModule.$d.price, defaultFunction);
assert.equal(call(defaultFunction), 4);

const cycleProvider = '# anvil: live-update-safe\nRATE = 2\nfrom consumer import B\n';
const cycleConsumer = '# anvil: live-update-safe\nB = 5\nfrom provider import RATE\n';
Sk.read = filename => filename.endsWith('/provider.py') || filename === 'provider.py' ? cycleProvider : filename.endsWith('/consumer.py') || filename === 'consumer.py' ? cycleConsumer : previousRead(filename);
await load('import consumer\n');
const cycleProviderModule = Sk.sysmodules.quick$lookup(new Sk.builtin.str('provider'));
const cycleConsumerModule = Sk.sysmodules.quick$lookup(new Sk.builtin.str('consumer'));
assert.throws(() => Sk.prepareModuleUpdates([{name: 'provider', after: cycleProvider.replace('RATE = 2', 'RATE = 3')}], {
    modules: [batchModule('provider', cycleProvider, cycleProviderModule), batchModule('consumer', cycleConsumer, cycleConsumerModule)]
}), /dependency cycle/);
Sk.read = previousRead;
console.log('Captured defaults and dependency cycle fallback passed');

const reboundConstant = 'RATE = 2\nRATE = [99][0]\ndef rate():\n    return RATE\n';
const reboundConstantModule = await load(reboundConstant);
assert.throws(() => Sk.prepareModuleUpdates([{name: 'live_test', after: reboundConstant.replace('RATE = 2', 'RATE = 3')}], {
    modules: [batchModule('live_test', reboundConstant, reboundConstantModule)]
}), /multiple source bindings/);
assert.equal(call(reboundConstantModule.$d.rate), 99);
const markedRebound = '# anvil: live-update-safe\n' + reboundConstant;
const markedReboundModule = await load(markedRebound);
await Sk.misceval.asyncToPromise(Sk.prepareModuleUpdates([{name: 'live_test', after: markedRebound.replace('RATE = 2', 'RATE = 3')}], {
    modules: [batchModule('live_test', markedRebound, markedReboundModule)]
}).apply);
assert.equal(call(markedReboundModule.$d.rate), 99);
console.log('Ambiguous constant bindings reject or explicitly rerun passed');

const freshConsumerBefore = '# anvil: live-update-safe\ncached = 0\ndef value():\n    return cached\n';
const freshConsumerAfter = freshConsumerBefore.replace('cached = 0', 'import provider as rates\ncached = rates.RATE');
Sk.read = filename => filename.endsWith('/provider.py') || filename === 'provider.py' ? constantSource : previousRead(filename);
const freshConsumer = await load(freshConsumerBefore);
const freshProvider = await Sk.misceval.asyncToPromise(() => Sk.importModule('provider', false, true));
await Sk.misceval.asyncToPromise(Sk.prepareModuleUpdates([
    {name: 'live_test', after: freshConsumerAfter},
    {name: 'provider', after: constantSource.replace('RATE = 2', 'RATE = 3')}
], {modules: [batchModule('live_test', freshConsumerBefore, freshConsumer), batchModule('provider', constantSource, freshProvider)]}).apply);
assert.equal(freshConsumer.$d.cached.v, 3);
assert.equal(call(freshConsumer.$d.value), 3);
Sk.read = previousRead;
console.log('New import alias observes provider update before dependent initialization passed');

const helperCapture = 'RATE = 2\ndef make():\n    value = RATE\n    return lambda: value\ncaptured = make()\n';
const helperCaptureModule = await load(helperCapture);
assert.throws(() => Sk.prepareModuleUpdates([{name: 'live_test', after: helperCapture.replace('RATE = 2', 'RATE = 3')}], {
    modules: [batchModule('live_test', helperCapture, helperCaptureModule)]
}), /initialization calls may capture/);
assert.equal(call(helperCaptureModule.$d.captured), 2);
console.log('Initialization helper capture falls back without executing app code');

for (const callableSource of [
    '# anvil: live-update-safe\ndef wrapper(fn):\n    return fn\n@wrapper\ndef work():\n    return 1\nstate = [1]\n',
    '# anvil: live-update-safe\nwork = lambda: 1\nstate = [1]\n'
]) {
    const callableModule = await load(callableSource);
    assert.throws(() => Sk.prepareModuleUpdates([{name: 'live_test', after: callableSource.replace('[1]', '[2]')}], {
        modules: [batchModule('live_test', callableSource, callableModule)]
    }), /rerun decorators|aliased or anonymous function/);
    assert.equal(Sk.ffi.remapToJs(callableModule.$d.state)[0], 1);
}
console.log('Rerun rejects callable identities that cannot be restored safely');

// Qualified future-call reads use the provider's current globals without
// rerunning consumers; module bindings and defaults are initialized captures.
const qualifiedDynamic = 'import provider\ndef value():\n    return provider.RATE\nclass View:\n    def value(self):\n        return provider.RATE\nview = View()\n';
Sk.read = filename => filename.endsWith('/provider.py') || filename === 'provider.py' ? constantSource : previousRead(filename);
const qualifiedModule = await load(qualifiedDynamic);
const qualifiedProvider = Sk.sysmodules.quick$lookup(new Sk.builtin.str('provider'));
const qualifiedFunction = qualifiedModule.$d.value, qualifiedView = qualifiedModule.$d.view;
await Sk.misceval.asyncToPromise(Sk.prepareModuleUpdates([{name: 'provider', after: constantSource.replace('RATE = 2', 'RATE = 7')}], {
    modules: [batchModule('live_test', qualifiedDynamic, qualifiedModule), batchModule('provider', constantSource, qualifiedProvider)]
}).apply);
assert.equal(qualifiedModule.$d.value, qualifiedFunction);
assert.equal(qualifiedModule.$d.view, qualifiedView);
assert.equal(call(qualifiedFunction), 7);
assert.equal(call(get(qualifiedView, 'value')), 7);
for (const capturedSource of [
    'import provider\ncached = provider.RATE\n',
    'import provider\ndef value(default=provider.RATE):\n    return default\n'
]) {
    const capturedModule = await load(capturedSource);
    const capturedProvider = Sk.sysmodules.quick$lookup(new Sk.builtin.str('provider'));
    assert.throws(() => Sk.prepareModuleUpdates([{name: 'provider', after: constantSource.replace('RATE = 2', 'RATE = 8')}], {
        modules: [batchModule('live_test', capturedSource, capturedModule), batchModule('provider', constantSource, capturedProvider)]
    }), /imported constants were captured/);
    assert.equal(capturedProvider.$d.RATE.v, 2);
}
Sk.read = previousRead;
console.log('Qualified dynamic function/method reads update; cached/default imports require rerun');

// Documentation is not opt-in permission to rerun initialization side effects.
const docstringMarker = '"""Example marker:\n# anvil: live-update-safe\n"""\ninitialized = 1\nstate = [1]\n';
const docstringMarkerModule = await load(docstringMarker);
assert.throws(() => Sk.prepareModuleUpdates([{name: 'live_test', after: docstringMarker.replace('initialized = 1', 'initialized = 2').replace('[1]', '[2]')}], {
    modules: [batchModule('live_test', docstringMarker, docstringMarkerModule)]
}), /initialization or imports changed/);
assert.equal(docstringMarkerModule.$d.initialized.v, 1);
assert.equal(Sk.ffi.remapToJs(docstringMarkerModule.$d.state)[0], 1);
console.log('Docstring marker does not authorize module initialization rerun');

// Signature edits update captured functions and bound methods, including Python
// keyword binding and immutable defaults, without running any module setup.
const signatureBefore = `
initialized = 0
def effect():
    global initialized
    initialized += 1
    return 7
def calculate(x=effect()):
    return x
class Form:
    def __init__(self, value=1):
        self.value = value
    def click(self, old=1):
        return old
form = Form()
captured = calculate
bound = form.click
`;
const signatureModule = await load(signatureBefore);
const signatureAfter = signatureBefore.replace("def calculate(x=effect()):\n    return x", "def calculate(value=3, *extra, scale=2, **kw):\n    return (value + sum(extra) + kw.get('offset', 0)) * scale")
    .replace("def click(self, old=1):\n        return old", "def click(self, amount=4, *, label='new'):\n        return label + str(amount)")
    + "\ndef added(value: 'number' = (1, -2), *, enabled=True) -> 'tuple':\n    return value if enabled else None\n";
const signaturePlan = Sk.prepareModuleUpdate(signatureBefore, signatureAfter, "live_test.py", {globals: signatureModule.$d});
assert.equal(call(signatureModule.$d.captured), 7);
assert.equal(signatureModule.$d.initialized.v, 1);
signaturePlan.apply();
assert.equal(signatureModule.$d.calculate, signatureModule.$d.captured);
assert.equal(call(signatureModule.$d.captured), 6);
assert.equal(call(signatureModule.$d.bound), 'new4');
const keywordCall = (fn, args, kw) => Sk.ffi.remapToJs(Sk.misceval.callsimArray(fn, args.map(Sk.ffi.remapToPy), Object.entries(kw).flatMap(([key, value]) => [key, Sk.ffi.remapToPy(value)])));
assert.equal(keywordCall(signatureModule.$d.captured, [1, 2, 3], {scale: 3, offset: 4}), 30);
assert.equal(keywordCall(signatureModule.$d.bound, [], {amount: 8, label: 'got'}), 'got8');
assert.throws(() => keywordCall(signatureModule.$d.bound, [], {old: 2}), /unexpected keyword/);
assert.deepEqual(Array.from(call(signatureModule.$d.added)), [1, -2]);
assert.equal(get(signatureModule.$d.added, '__annotations__').mp$subscript(new Sk.builtin.str('return')).v, 'tuple');
assert.equal(get(signatureModule.$d.added, '__annotations__').mp$subscript(new Sk.builtin.str('value')).v, 'number');
assert.equal(signatureModule.$d.initialized.v, 1);
// A later body edit keeps runtime changes made to __defaults__.
signatureModule.$d.calculate.tp$setattr(new Sk.builtin.str('__defaults__'), new Sk.builtin.tuple([new Sk.builtin.int_(9)]));
const signatureBodyAfter = signatureAfter.replace("* scale", "* scale + 1");
Sk.prepareModuleUpdate(signatureAfter, signatureBodyAfter, "live_test.py", {globals: signatureModule.$d}).apply();
assert.equal(call(signatureModule.$d.captured), 19);
for (const unsafe of [signatureBodyAfter.replace('value=3', 'value=effect()'), signatureBodyAfter + "\ndef unsafe(x: effect()):\n    return x\n"]) {
    assert.throws(() => Sk.prepareModuleUpdate(signatureBodyAfter, unsafe, "live_test.py", {globals: signatureModule.$d}), /requires literal/);
    assert.equal(signatureModule.$d.initialized.v, 1);
    assert.equal(call(signatureModule.$d.captured), 19);
}
const defaultsAfter = signatureBodyAfter.replace('value=3', 'value=6').replace("-> 'tuple'", "-> 'values'");
Sk.prepareModuleUpdate(signatureBodyAfter, defaultsAfter, 'live_test.py', {globals: signatureModule.$d}).apply();
assert.equal(call(signatureModule.$d.captured), 13);
assert.equal(get(signatureModule.$d.added, '__annotations__').mp$subscript(new Sk.builtin.str('return')).v, 'values');
const constructorPlan = Sk.prepareModuleUpdate(defaultsAfter, defaultsAfter.replace('__init__(self, value=1)', '__init__(self, value=2)'), "live_test.py", {globals: signatureModule.$d, formClass: 'Form'});
assert.deepEqual(Array.from(constructorPlan.resetClasses), ['Form']);
constructorPlan.apply();
assert.equal(get(signatureModule.$d.form, 'value').v, 1);
console.log('Signature edits preserve captured callable identity and safely refresh literal metadata');

// Dev-only executed reads distinguish deferred imports from actual captures,
// including helpers and nested class/function initialization.
Sk.trackModuleReads = true;
const trackedProviderSource = 'RATE = 2\nOTHER = 10\ndef current():\n    return RATE\n';
Sk.read = filename => filename.endsWith('/provider.py') || filename === 'provider.py' ? trackedProviderSource : previousRead(filename);
const deferredImportSource = 'state = [1]\ndef value():\n    from provider import RATE\n    return RATE\n';
const deferredImportModule = await load(deferredImportSource);
assert.equal(call(deferredImportModule.$d.value), 2);
const deferredProvider = Sk.sysmodules.quick$lookup(new Sk.builtin.str('provider'));
const deferredFunction = deferredImportModule.$d.value;
await Sk.misceval.asyncToPromise(Sk.prepareModuleUpdates([{name: 'provider', after: trackedProviderSource.replace('RATE = 2', 'RATE = 3')}], {
    modules: [batchModule('live_test', deferredImportSource, deferredImportModule), batchModule('provider', trackedProviderSource, deferredProvider)]
}).apply);
assert.equal(call(deferredFunction), 3);
assert.equal(deferredFunction, deferredImportModule.$d.value);
assert.equal(Sk.ffi.remapToJs(deferredImportModule.$d.state)[0], 1);
for (const captureSource of [
    'def outer():\n    def inner():\n        from provider import RATE\n        return RATE\n    return inner()\ncached = outer()\n',
    'def helper():\n    from provider import RATE\n    return RATE\nclass Model:\n    cached = helper()\n',
    'import provider\ncached = provider.current()\n'
]) {
    const captureModule = await load(captureSource);
    const captureProvider = Sk.sysmodules.quick$lookup(new Sk.builtin.str('provider'));
    assert.throws(() => Sk.prepareModuleUpdates([{name: 'provider', after: trackedProviderSource.replace('RATE = 2', 'RATE = 4')}], {
        modules: [batchModule('live_test', captureSource, captureModule), batchModule('provider', trackedProviderSource, captureProvider)]
    }), /imported constants were captured/);
    assert.equal(captureProvider.$d.RATE.v, 2);
}
// An unrelated initialization call is no longer assumed to read every constant.
const unrelatedCallSource = 'RATE = 2\ndef other():\n    return 10\ncached = other()\ndef value():\n    return RATE\n';
const unrelatedCallModule = await load(unrelatedCallSource);
Sk.prepareModuleUpdates([{name: 'live_test', after: unrelatedCallSource.replace('RATE = 2', 'RATE = 3')}], {
    modules: [batchModule('live_test', unrelatedCallSource, unrelatedCallModule)]
}).apply();
assert.equal(call(unrelatedCallModule.$d.value), 3);
const ownCaptureSource = 'RATE = 2\ndef helper():\n    return RATE\ncached = helper()\n';
const ownCaptureModule = await load(ownCaptureSource);
assert.throws(() => Sk.prepareModuleUpdates([{name: 'live_test', after: ownCaptureSource.replace('RATE = 2', 'RATE = 3')}], {
    modules: [batchModule('live_test', ownCaptureSource, ownCaptureModule)]
}), /captured during initialization/);
// An authorized rerun refreshes captures rather than retaining stale edges.
const trackedRerunBefore = '# anvil: live-update-safe\ndef read():\n    from provider import RATE\n    return RATE\ncached = read()\n';
const trackedRerunModule = await load(trackedRerunBefore);
const trackedRerunProvider = Sk.sysmodules.quick$lookup(new Sk.builtin.str('provider'));
const trackedRerunAfter = trackedRerunBefore.replace('cached = read()', 'cached = 0');
await Sk.misceval.asyncToPromise(Sk.prepareModuleUpdates([{name: 'live_test', after: trackedRerunAfter}], {
    modules: [batchModule('live_test', trackedRerunBefore, trackedRerunModule), batchModule('provider', trackedProviderSource, trackedRerunProvider)]
}).apply);
assert.equal(trackedRerunModule.$d.cached.v, 0);
await Sk.misceval.asyncToPromise(Sk.prepareModuleUpdates([{name: 'provider', after: trackedProviderSource.replace('RATE = 2', 'RATE = 4')}], {
    modules: [batchModule('live_test', trackedRerunAfter, trackedRerunModule), batchModule('provider', trackedProviderSource, trackedRerunProvider)]
}).apply);
assert.equal(trackedRerunModule.$d.cached.v, 0);
assert.equal(call(trackedRerunModule.$d.read), 4);
// Suspended initialization collects reads on resume, with no ambient collector
// attributing unrelated work while the initialization promise is waiting.
let resumeTrackedImport;
Sk.builtins.pause_tracking = new Sk.builtin.func(() => Sk.misceval.promiseToSuspension(new Promise(resolve => { resumeTrackedImport = resolve; })));
const trackedSuspensionSource = 'import provider\ndef read():\n    pause_tracking()\n    return provider.RATE\ncached = read()\n';
const trackedImportPromise = load(trackedSuspensionSource);
while (!resumeTrackedImport) await new Promise(resolve => setTimeout(resolve, 0));
const trackedSuspensionProvider = Sk.sysmodules.quick$lookup(new Sk.builtin.str('provider'));
assert.equal(get(trackedSuspensionProvider, 'OTHER').v, 10);
resumeTrackedImport(Sk.builtin.none.none$);
const trackedSuspensionModule = await trackedImportPromise;
assert.equal(trackedSuspensionModule.$d.cached.v, 2);
assert.throws(() => Sk.prepareModuleUpdates([{name: 'provider', after: trackedProviderSource.replace('RATE = 2', 'RATE = 5')}], {
    modules: [batchModule('live_test', trackedSuspensionSource, trackedSuspensionModule), batchModule('provider', trackedProviderSource, trackedSuspensionProvider)]
}), /imported constants were captured/);
Sk.prepareModuleUpdates([{name: 'provider', after: trackedProviderSource.replace('OTHER = 10', 'OTHER = 11')}], {
    modules: [batchModule('live_test', trackedSuspensionSource, trackedSuspensionModule), batchModule('provider', trackedProviderSource, trackedSuspensionProvider)]
}).apply();
assert.equal(trackedSuspensionProvider.$d.OTHER.v, 11);
delete Sk.builtins.pause_tracking;
// Reads through an untracked provider retain the static fallback; opaque module
// escapes retain their existing conservative boundary even with tracking on.
Sk.trackModuleReads = false;
const mixedProviderSource = 'RATE = 2\ndef value():\n    return RATE\n';
const mixedProvider = await load(mixedProviderSource);
Sk.sysmodules.mp$ass_subscript(new Sk.builtin.str('provider'), mixedProvider);
Sk.trackModuleReads = true;
const mixedConsumerSource = 'def value():\n    from provider import RATE\n    return RATE\n';
const mixedConsumer = await Sk.misceval.asyncToPromise(() => Sk.importModuleInternal_('consumer', false, 'consumer', mixedConsumerSource, undefined, false, true));
assert.throws(() => Sk.prepareModuleUpdates([{name: 'provider', after: mixedProviderSource.replace('RATE = 2', 'RATE = 3')}], {
    modules: [batchModule('consumer', mixedConsumerSource, mixedConsumer), batchModule('provider', mixedProviderSource, mixedProvider)]
}), /imported constants were captured/);
const trackedOpaqueSource = 'import provider\ndef value():\n    return provider\n';
const trackedOpaqueModule = await load(trackedOpaqueSource);
const trackedOpaqueProvider = Sk.sysmodules.quick$lookup(new Sk.builtin.str('provider'));
assert.throws(() => Sk.prepareModuleUpdates([{name: 'provider', after: trackedProviderSource.replace('RATE = 2', 'RATE = 3')}], {
    modules: [batchModule('live_test', trackedOpaqueSource, trackedOpaqueModule), batchModule('provider', trackedProviderSource, trackedOpaqueProvider)]
}), /module reference escapes/);
// Reciprocal real imports need no execution order for body-only patches.
// Captured from-imports and unrelated mutable state remain the same objects.
const cyclicDefinitionsProvider = 'state = [10]\ndef a():\n    return state[0]\nimport consumer\nfrom consumer import b\n';
const cyclicDefinitionsConsumer = 'state = [20]\ndef b():\n    return state[0]\nimport provider\nfrom provider import a\n';
Sk.read = filename => filename.endsWith('/provider.py') || filename === 'provider.py' ? cyclicDefinitionsProvider
    : filename.endsWith('/consumer.py') || filename === 'consumer.py' ? cyclicDefinitionsConsumer : previousRead(filename);
await load('import provider\n');
const cyclicProvider = Sk.sysmodules.quick$lookup(new Sk.builtin.str('provider'));
const cyclicConsumer = Sk.sysmodules.quick$lookup(new Sk.builtin.str('consumer'));
const capturedA = cyclicConsumer.$d.a, capturedB = cyclicProvider.$d.b;
const providerState = cyclicProvider.$d.state, consumerState = cyclicConsumer.$d.state;
await Sk.misceval.asyncToPromise(Sk.prepareModuleUpdates([
    {name: 'provider', after: cyclicDefinitionsProvider.replace('return state[0]', 'return state[0] + 1')},
    {name: 'consumer', after: cyclicDefinitionsConsumer.replace('return state[0]', 'return state[0] + 2')}
], {modules: [batchModule('provider', cyclicDefinitionsProvider, cyclicProvider), batchModule('consumer', cyclicDefinitionsConsumer, cyclicConsumer)]}).apply);
assert.equal(call(capturedA), 11);
assert.equal(call(capturedB), 22);
assert.equal(cyclicProvider.$d.a, capturedA);
assert.equal(cyclicConsumer.$d.b, capturedB);
assert.equal(cyclicProvider.$d.state, providerState);
assert.equal(cyclicConsumer.$d.state, consumerState);
Sk.read = filename => filename.endsWith('/provider.py') || filename === 'provider.py' ? cycleProvider : filename.endsWith('/consumer.py') || filename === 'consumer.py' ? cycleConsumer : previousRead(filename);
await load('import consumer\n');
const trackedCycleProvider = Sk.sysmodules.quick$lookup(new Sk.builtin.str('provider'));
const trackedCycleConsumer = Sk.sysmodules.quick$lookup(new Sk.builtin.str('consumer'));
assert.throws(() => Sk.prepareModuleUpdates([{name: 'provider', after: cycleProvider.replace('RATE = 2', 'RATE = 3')}], {
    modules: [batchModule('provider', cycleProvider, trackedCycleProvider), batchModule('consumer', cycleConsumer, trackedCycleConsumer)]
}), /dependency cycle/);
Sk.trackModuleReads = false;
Sk.read = previousRead;
console.log('Tracked initialization reads support deferred imports and retain helper/class/suspension capture boundaries');

// Module constant ownership follows Python scopes, so similarly named locals,
// nested definitions/imports and class attributes do not force a restart.
Sk.trackModuleReads = true;
const scopedConstantSource = `
RATE = 2
def local_assignment():
    RATE = 5
    return RATE
def local_definition():
    def RATE():
        return 6
    return RATE()
def local_import():
    import unrelated as RATE
    return RATE
def local_exception():
    try:
        raise ValueError()
    except ValueError as RATE:
        return 7
class Other:
    RATE = 8
    def RATE_method(self):
        RATE = 9
        return RATE
def value():
    return RATE
`;
const scopedConsumerSource = 'import provider\ndef value():\n    return provider.RATE\n';
Sk.read = filename => filename.endsWith('/provider.py') || filename === 'provider.py' ? scopedConstantSource : previousRead(filename);
const scopedConsumer = await load(scopedConsumerSource);
const scopedProvider = Sk.sysmodules.quick$lookup(new Sk.builtin.str('provider'));
const scopedProviderGlobals = scopedProvider.$d;
const scopedLocalFunction = scopedProvider.$d.local_assignment;
Sk.prepareModuleUpdates([{name: 'provider', after: scopedConstantSource.replace('RATE = 2', 'RATE = 3')}], {
    modules: [batchModule('live_test', scopedConsumerSource, scopedConsumer), batchModule('provider', scopedConstantSource, scopedProvider)]
}).apply();
assert.equal(call(scopedConsumer.$d.value), 3);
assert.equal(call(scopedProvider.$d.value), 3);
assert.equal(call(scopedLocalFunction), 5);
assert.equal(call(scopedProvider.$d.local_definition), 6);
assert.equal(call(scopedProvider.$d.local_exception), 7);
assert.equal(get(scopedProvider.$d.Other, 'RATE').v, 8);
assert.equal(scopedProvider.$d, scopedProviderGlobals);
assert.equal(scopedProvider.$d.local_assignment, scopedLocalFunction);
// Deferred global writes/deletes and global definition/import bindings remain
// ambiguous module ownership, even if the function has not yet been called.
for (const globalBinding of [
    'def mutate():\n    global RATE\n    RATE = 5\n',
    'del RATE\n',
    'def mutate():\n    global RATE\n    def RATE():\n        return 5\n',
    'def mutate():\n    global RATE\n    import unrelated as RATE\n',
    'class Other:\n    global RATE\n    RATE = 5\n'
]) {
    const globalBindingSource = 'RATE = 2\n' + globalBinding;
    Sk.read = filename => filename.endsWith('/provider.py') || filename === 'provider.py' ? globalBindingSource : previousRead(filename);
    const globalBindingConsumer = await load(scopedConsumerSource);
    const globalBindingProvider = Sk.sysmodules.quick$lookup(new Sk.builtin.str('provider'));
    const originalRate = globalBindingProvider.$d.RATE;
    assert.throws(() => Sk.prepareModuleUpdates([{name: 'provider', after: globalBindingSource.replace('RATE = 2', 'RATE = 3')}], {
        modules: [batchModule('live_test', scopedConsumerSource, globalBindingConsumer), batchModule('provider', globalBindingSource, globalBindingProvider)]
    }), /multiple source bindings/);
    assert.equal(globalBindingProvider.$d.RATE, originalRate);
}
Sk.trackModuleReads = false;
Sk.read = previousRead;
console.log('Constant binding ownership distinguishes local/class names from real module writes');
