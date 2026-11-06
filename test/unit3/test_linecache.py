# CPython linecache cache/loader contracts with a Skulpt virtual-source fixture.
import linecache
import unittest

try:
    jseval
except NameError:
    jseval = None


if jseval is not None:
    class TestHostSource(unittest.TestCase):
        def setUp(self):
            linecache.clearcache()
            jseval('''
                globalThis.linecacheTestState = { read: Sk.read, source: "first\\r\\nsecond" };
                Sk.read = function (filename) {
                    if (filename === "virtual-source.py") return globalThis.linecacheTestState.source;
                    return globalThis.linecacheTestState.read(filename);
                };
            ''')

        def tearDown(self):
            jseval('''
                Sk.read = globalThis.linecacheTestState.read;
                delete globalThis.linecacheTestState;
            ''')
            linecache.clearcache()

        def test_lines_cache_and_explicit_refresh(self):
            self.assertEqual(linecache.getlines('virtual-source.py'), ['first\n', 'second\n'])
            self.assertEqual(linecache.getline('virtual-source.py', 2), 'second\n')
            self.assertEqual(linecache.getline('virtual-source.py', 0), '')
            self.assertEqual(linecache.getline('virtual-source.py', 3), '')
            jseval('globalThis.linecacheTestState.source = "changed"')
            self.assertEqual(linecache.getline('virtual-source.py', 1), 'first\n')
            linecache.checkcache('virtual-source.py')
            self.assertEqual(linecache.getline('virtual-source.py', 1), 'first\n')
            self.assertEqual(linecache.updatecache('virtual-source.py'), ['changed\n'])
            linecache.clearcache()
            self.assertEqual(linecache.getline('virtual-source.py', 1), 'changed\n')

        def test_suspending_source_reader(self):
            jseval('''Sk.read = function () {
                return Sk.misceval.promiseToSuspension(Promise.resolve("delayed source"));
            };''')
            self.assertEqual(linecache.getline('delayed.py', 1), 'delayed source\n')


class TestSourceFallback(unittest.TestCase):
    def tearDown(self):
        linecache.clearcache()

    def test_unavailable_and_registered_source(self):
        self.assertEqual(linecache.getlines('missing-source-for-linecache.py'), [])
        self.assertEqual(linecache.getline('<unknown>', 1), '')
        lines = ['registered source\n']
        linecache.cache['<generated>'] = (18, None, lines, '<generated>')
        self.assertEqual(linecache.getline('<generated>', 1), lines[0])

    def test_lazy_module_loader(self):
        calls = []

        class Loader:
            def get_source(self, name):
                calls.append(name)
                return 'loaded source'

        namespace = {'__name__': 'test_module', '__loader__': Loader()}
        filename = 'loader-only-source.py'
        self.assertTrue(linecache.lazycache(filename, namespace))
        self.assertEqual(calls, [])
        self.assertEqual(linecache.getline(filename, 1), 'loaded source\n')
        self.assertEqual(calls, ['test_module'])
        self.assertEqual(linecache.getline(filename, 1), 'loaded source\n')
        self.assertEqual(calls, ['test_module'])


if __name__ == '__main__':
    unittest.main()
