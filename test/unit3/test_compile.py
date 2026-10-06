# CPython 3.14 Lib/test/test_compile.py at 18ef0f0cb52.
# Selected method bodies and assertions are unchanged.
import unittest

# Global fixture from CPython test_builtin.py.
A_GLOBAL_VALUE = 123

class TestSpecifics(unittest.TestCase):
    def test_exec_with_general_mapping_for_locals(self):

        class M:
            "Test mapping interface versus possible calls from eval()."
            def __getitem__(self, key):
                if key == 'a':
                    return 12
                raise KeyError
            def __setitem__(self, key, value):
                self.results = (key, value)
            def keys(self):
                return list('xyz')

        m = M()
        g = globals()
        exec('z = a', g, m)
        self.assertEqual(m.results, ('z', 12))
        try:
            exec('z = b', g, m)
        except NameError:
            pass
        else:
            self.fail('Did not detect a KeyError')
        exec('z = dir()', g, m)
        self.assertEqual(m.results, ('z', list('xyz')))
        exec('z = globals()', g, m)
        self.assertEqual(m.results, ('z', g))
        exec('z = locals()', g, m)
        self.assertEqual(m.results, ('z', m))
        self.assertRaises(TypeError, exec, 'z = b', m)

        class A:
            "Non-mapping"
            pass
        m = A()
        self.assertRaises(TypeError, exec, 'z = a', g, m)

        # Verify that dict subclasses work as well
        class D(dict):
            def __getitem__(self, key):
                if key == 'a':
                    return 12
                return dict.__getitem__(self, key)
        d = D()
        exec('z = a', g, d)
        self.assertEqual(d['z'], 12)

    # CPython test_builtin.py methods; assertions unchanged. The UserDict
    # fixture call is omitted because that stdlib class is not implemented.
    def test_eval_kwargs(self):
        data = {"A_GLOBAL_VALUE": 456}
        self.assertEqual(eval("globals()['A_GLOBAL_VALUE']", globals=data), 456)
        self.assertEqual(eval("globals()['A_GLOBAL_VALUE']", locals=data), 123)

    def test_general_eval(self):
        # Tests that general mappings can be used for the locals argument

        class M:
            "Test mapping interface versus possible calls from eval()."
            def __getitem__(self, key):
                if key == 'a':
                    return 12
                raise KeyError
            def keys(self):
                return list('xyz')

        m = M()
        g = globals()
        self.assertEqual(eval('a', g, m), 12)
        self.assertRaises(NameError, eval, 'b', g, m)
        self.assertEqual(eval('dir()', g, m), list('xyz'))
        self.assertEqual(eval('globals()', g, m), g)
        self.assertEqual(eval('locals()', g, m), m)
        self.assertRaises(TypeError, eval, 'a', m)
        class A:
            "Non-mapping"
            pass
        m = A()
        self.assertRaises(TypeError, eval, 'a', g, m)

        # Verify that dict subclasses work as well
        class D(dict):
            def __getitem__(self, key):
                if key == 'a':
                    return 12
                return dict.__getitem__(self, key)
            def keys(self):
                return list('xyz')

        d = D()
        self.assertEqual(eval('a', g, d), 12)
        self.assertRaises(NameError, eval, 'b', g, d)
        self.assertEqual(eval('dir()', g, d), list('xyz'))
        self.assertEqual(eval('globals()', g, d), g)
        self.assertEqual(eval('locals()', g, d), d)

        # Verify locals stores (used by list comps)
        eval('[locals() for i in (2,3)]', g, d)
        # collections.UserDict fixture is unavailable in Skulpt; deferred stdlib coverage.

        class SpreadSheet:
            "Sample application showing nested, calculated lookups."
            _cells = {}
            def __setitem__(self, key, formula):
                self._cells[key] = formula
            def __getitem__(self, key):
                return eval(self._cells[key], globals(), self)

        ss = SpreadSheet()
        ss['a1'] = '5'
        ss['a2'] = 'a1*6'
        ss['a3'] = 'a2*7'
        self.assertEqual(ss['a3'], 210)

        # Verify that dir() catches a non-list returned by eval
        # SF bug #1004669
        class C:
            def __getitem__(self, item):
                raise KeyError(item)
            def keys(self):
                return 1 # used to be 'a' but that's no longer an error
        self.assertRaises(TypeError, eval, 'dir()', globals(), C())

    def test_exec_kwargs(self):
        g = {}
        exec('global z\nz = 1', globals=g)
        if '__builtins__' in g:
            del g['__builtins__']
        self.assertEqual(g, {'z': 1})

        # if we only set locals, the global assignment will not
        # reach this locals dictionary
        g = {}
        exec('global z\nz = 1', locals=g)
        self.assertEqual(g, {})

if __name__ == "__main__":
    unittest.main()
