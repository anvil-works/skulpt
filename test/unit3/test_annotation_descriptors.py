# Unchanged CPython 3.14 annotation descriptor methods at 18ef0f0cb52.
import types
import unittest

class AnnotationDescriptorTests(unittest.TestCase):
    def test_lazy_create_annotations(self):
        # type objects lazy create their __annotations__ dict on demand.
        # the annotations dict is stored in type.__dict__ (as __annotations_cache__).
        # a freshly created type shouldn't have an annotations dict yet.
        foo = type("Foo", (), {})
        for i in range(3):
            self.assertFalse("__annotations_cache__" in foo.__dict__)
            d = foo.__annotations__
            self.assertTrue("__annotations_cache__" in foo.__dict__)
            self.assertEqual(foo.__annotations__, d)
            self.assertEqual(foo.__dict__['__annotations_cache__'], d)
            del foo.__annotations__

    def test_setting_annotations(self):
        foo = type("Foo", (), {})
        for i in range(3):
            self.assertFalse("__annotations_cache__" in foo.__dict__)
            d = {'a': int}
            foo.__annotations__ = d
            self.assertTrue("__annotations_cache__" in foo.__dict__)
            self.assertEqual(foo.__annotations__, d)
            self.assertEqual(foo.__dict__['__annotations_cache__'], d)
            del foo.__annotations__

    def test_annotations_getset_raises(self):
        # builtin types don't have __annotations__ (yet!)
        with self.assertRaises(AttributeError):
            print(float.__annotations__)
        with self.assertRaises(TypeError):
            float.__annotations__ = {}
        with self.assertRaises(TypeError):
            del float.__annotations__

        # double delete
        foo = type("Foo", (), {})
        foo.__annotations__ = {}
        del foo.__annotations__
        with self.assertRaises(AttributeError):
            del foo.__annotations__

    def test_explicitly_set_annotations(self):
        class C:
            __annotations__ = {"what": int}
        self.assertEqual(C.__annotations__, {"what": int})

    def test_del_annotations_and_annotate(self):
        # gh-132285
        called = False
        class A:
            def __annotate__(format):
                nonlocal called
                called = True
                return {'a': int}

        self.assertEqual(A.__annotations__, {'a': int})
        self.assertTrue(called)
        self.assertTrue(A.__annotate__)

        del A.__annotations__
        called = False

        self.assertEqual(A.__annotations__, {})
        self.assertFalse(called)
        self.assertIs(A.__annotate__, None)

    def test_descriptor_still_works(self):
        class C:
            def __init__(self, name=None, bases=None, d=None):
                self.my_annotations = None

            @property
            def __annotations__(self):
                if not hasattr(self, 'my_annotations'):
                    self.my_annotations = {}
                if not isinstance(self.my_annotations, dict):
                    self.my_annotations = {}
                return self.my_annotations

            @__annotations__.setter
            def __annotations__(self, value):
                if not isinstance(value, dict):
                    raise ValueError("can only set __annotations__ to a dict")
                self.my_annotations = value

            @__annotations__.deleter
            def __annotations__(self):
                if getattr(self, 'my_annotations', False) is None:
                    raise AttributeError('__annotations__')
                self.my_annotations = None

        c = C()
        self.assertEqual(c.__annotations__, {})
        d = {'a':'int'}
        c.__annotations__ = d
        self.assertEqual(c.__annotations__, d)
        with self.assertRaises(ValueError):
            c.__annotations__ = 123
        del c.__annotations__
        with self.assertRaises(AttributeError):
            del c.__annotations__
        self.assertEqual(c.__annotations__, {})


        class D(metaclass=C):
            pass

        self.assertEqual(D.__annotations__, {})
        d = {'a':'int'}
        D.__annotations__ = d
        self.assertEqual(D.__annotations__, d)
        with self.assertRaises(ValueError):
            D.__annotations__ = 123
        del D.__annotations__
        with self.assertRaises(AttributeError):
            del D.__annotations__
        self.assertEqual(D.__annotations__, {})

    def test_manual_class_and_module_annotate(self):
        class C: pass
        self.check_annotations(C)
        self.check_annotations(types.ModuleType('test_annotations'))

    def check_annotations(self, f):
        self.assertEqual(f.__annotations__, {})
        self.assertIs(f.__annotate__, None)

        with self.assertRaisesRegex(TypeError, "__annotate__ must be callable or None"):
            f.__annotate__ = 42
        f.__annotate__ = lambda: 42
        with self.assertRaisesRegex(TypeError, r"takes 0 positional arguments but 1 was given"):
            print(f.__annotations__)

        f.__annotate__ = lambda x: 42
        with self.assertRaisesRegex(TypeError, r"__annotate__ returned non-dict of type 'int'"):
            print(f.__annotations__)

        f.__annotate__ = lambda x: {"x": x}
        self.assertEqual(f.__annotations__, {"x": 1})

        # Setting annotate to None does not invalidate the cached __annotations__
        f.__annotate__ = None
        self.assertEqual(f.__annotations__, {"x": 1})

        # But setting it to a new callable does
        f.__annotate__ = lambda x: {"y": x}
        self.assertEqual(f.__annotations__, {"y": 1})

        # Setting f.__annotations__ also clears __annotate__
        f.__annotations__ = {"z": 43}
        self.assertIs(f.__annotate__, None)


    # CPython-checked cache isolation and partially initialized module cases.
    def test_class_cache_isolation_and_arbitrary_assignments(self):
        class Base: pass
        Base.__annotate__ = lambda format: {'base': format}
        class Child(Base): pass
        self.assertIsNone(Child.__annotate__)
        self.assertEqual(Child.__annotations__, {})
        self.assertEqual(Base.__annotations__, {'base': 1})
        Child.__annotations__ = 42
        self.assertEqual(Child.__annotations__, 42)
        Base.__annotate__ = None
        self.assertEqual(Base.__annotations__, {'base': 1})
        del Base.__annotations__
        with self.assertRaises(AttributeError): del Base.__annotations__

    def test_module_initializing_does_not_cache(self):
        module = types.ModuleType('annotations')
        class Spec: _initializing = True
        module.__spec__ = Spec()
        seen = []
        def annotate(format):
            seen.append(format)
            return {'x': len(seen)}
        module.__annotate__ = annotate
        self.assertEqual(module.__annotations__, {'x': 1})
        self.assertEqual(module.__annotations__, {'x': 2})
        self.assertNotIn('__annotations__', module.__dict__)
        module.__spec__._initializing = False
        self.assertEqual(module.__annotations__, {'x': 3})
        self.assertEqual(module.__annotations__, {'x': 3})
        self.assertEqual(seen, [1, 1, 1])
        module.__annotations__ = 42
        self.assertEqual(module.__annotations__, 42)
        self.assertIsNone(module.__annotate__)

if __name__ == '__main__': unittest.main()
