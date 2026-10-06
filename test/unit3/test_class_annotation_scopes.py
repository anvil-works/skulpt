# CPython 3.14 test_type_annotations.py method at 18ef0f0cb52.
import textwrap
import unittest

# Harness adapter for test.support.run_code.
def run_code(code):
    ns = {}
    exec(textwrap.dedent(code), ns)
    return ns

class ClassAnnotationScopeTests(unittest.TestCase):
    def test_name_clash_with_format(self):
        # this test would fail if __annotate__'s parameter was called "format"
        # during symbol table construction
        code = """
        class format: pass

        def f(x: format): pass
        """
        ns = run_code(code)
        f = ns["f"]
        self.assertEqual(f.__annotations__, {"x": ns["format"]})

        code = """
        class Outer:
            class format: pass

            def meth(self, x: format): ...
        """
        ns = run_code(code)
        self.assertEqual(ns["Outer"].meth.__annotations__, {"x": ns["Outer"].format})

        code = """
        def f(format):
            def inner(x: format): pass
            return inner
        res = f("closure var")
        """
        ns = run_code(code)
        self.assertEqual(ns["res"].__annotations__, {"x": "closure var"})

        code = """
        def f(x: format):
            pass
        """
        ns = run_code(code)
        # picks up the format() builtin
        self.assertEqual(ns["f"].__annotations__, {"x": format})

        code = """
        def outer():
            def f(x: format):
                pass
            if False:
                class format: pass
            return f
        f = outer()
        """
        ns = run_code(code)
        with self.assertRaisesRegex(
            NameError,
            "cannot access free variable 'format' where it is not associated with a value in enclosing scope",
        ):
            ns["f"].__annotations__

    # CPython-checked class cell, lookup and construction regressions.
    def test_late_class_bindings_and_live_dictionary(self):
        class Outer:
            def method(self, x: Nested) -> value: pass
            class Nested: pass
            value = 1
        method = Outer.method
        annotate = method.__annotate__
        self.assertEqual(method.__annotations__, {'x': Outer.Nested, 'return': 1})
        self.assertEqual(annotate.__code__.co_freevars, ('__classdict__',))
        cell = annotate.__closure__[0]
        self.assertEqual(cell.cell_contents, dict(Outer.__dict__))
        self.assertNotIn('__classdictcell__', Outer.__dict__)
        Outer.value = 2
        self.assertEqual(annotate(1)['return'], 2)
        self.assertEqual(method.__annotations__['return'], 1)
        del Outer.value
        with self.assertRaises(NameError): annotate(1)

    def test_class_bindings_override_outer_cells(self):
        ns = run_code("""
        value = 'global'
        def outer():
            value = 'outer'
            free = 'free'
            class C:
                def f(self, x: value, y: free): pass
                value = 'class'
            return C
        C = outer()
        """)
        cls = ns['C']
        self.assertEqual(cls.f.__annotations__, {'x': 'class', 'y': 'free'})
        cls.free = 'class free'
        self.assertEqual(cls.f.__annotate__(1), {'x': 'class', 'y': 'class free'})
        del cls.value
        self.assertEqual(cls.f.__annotate__(1)['x'], 'global')
        ns = run_code("""
        value = 'global'
        class C:
            global value
            def f(self, x: value): pass
        """)
        ns['C'].value = 'class'
        self.assertEqual(ns['C'].f.__annotations__, {'x': 'global'})

    def test_class_dictionary_is_ready_for_construction_callbacks(self):
        seen = []
        class Descriptor:
            def __set_name__(self, owner, name):
                seen.append(owner.f.__annotations__)
        class Base:
            def __init_subclass__(cls):
                seen.append(cls.f.__annotate__(1))
        class C(Base):
            marker = Descriptor()
            def f(self, x: value) -> __class__: pass
            value = 42
        self.assertEqual(seen, [{'x': 42, 'return': C}] * 2)
        self.assertEqual(set(C.f.__annotate__.__code__.co_freevars), {'__classdict__', '__class__'})
        with self.assertRaisesRegex(TypeError, '__classdictcell__ must be a nonlocal cell'):
            type('Invalid', (), {'__classdictcell__': 42})

    def test_class_dictionary_cell_tracks_the_body_then_the_type(self):
        seen = []
        def decorator(f):
            with self.assertRaisesRegex(NameError, "name 'value' is not defined"):
                f.__annotate__(1)
            seen.append(f)
            return f
        class C:
            @decorator
            def f(self, x: value): pass
            value = 42
            self.assertEqual(f.__annotate__(1), {'x': 42})
        C.value = 43
        self.assertEqual(seen[0].__annotations__, {'x': 43})

    def test_annotation_children_keep_ordinary_scope_rules(self):
        ns = run_code("""
        value = 'global'
        class C:
            value = 'class'
            items = [1, 2]
            def f(self, a: (lambda: value), b: [value for i in items]): pass
        """)
        annos = ns['C'].f.__annotations__
        self.assertEqual(annos['a'](), 'global')
        self.assertEqual(annos['b'], ['global', 'global'])

if __name__ == '__main__': unittest.main()
