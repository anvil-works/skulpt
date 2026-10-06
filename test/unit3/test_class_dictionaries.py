# CPython 3.14 dictionary proxy method and CPython-checked class namespace regressions.
import types
import unittest

class ClassDictionaryTests(unittest.TestCase):
    # Unchanged Lib/test/test_descr.py DictProxyTests method at 18ef0f0cb52.
    def test_dict_type_with_metaclass(self):
        # Testing type of __dict__ when metaclass set...
        class B(object):
            pass
        class M(type):
            pass
        class C(metaclass=M):
            # In 2.3a1, C.__dict__ was a real dict rather than a dict proxy
            pass
        self.assertEqual(type(C.__dict__), type(B.__dict__))

    def test_live_proxy_mutation_and_inheritance(self):
        class Base:
            value = 1
            def method(self): return 1
        class Child(Base): pass
        view = Base.__dict__
        self.assertIs(type(view), types.MappingProxyType)
        self.assertEqual(view['value'], 1)
        self.assertNotIn('value', Child.__dict__)
        Base.value = 2
        self.assertEqual(view['value'], 2)
        self.assertEqual(Child.value, 2)
        self.assertEqual(Child().value, 2)
        Child.value = 3
        self.assertEqual(Child().value, 3)
        del Child.value
        self.assertEqual(Child.value, 2)
        with self.assertRaises(AttributeError): del Child.value
        def method(self): return 4
        Base.method = method
        self.assertIs(view['method'], method)
        self.assertEqual(Child().method(), 4)
        del Base.method
        with self.assertRaises(AttributeError): Child().method
        with self.assertRaises(TypeError): view['value'] = 5

    def test_type_copies_input_and_preserves_nonstring_keys(self):
        class Key(str): pass
        key = Key('value')
        body = {key: 1, 42: 'nonstring', '__qualname__': 'Qualified'}
        cls = type('Name', (), body)
        body[key] = 2
        self.assertEqual(cls.value, 1)
        self.assertIs(next(k for k in cls.__dict__ if k == key), key)
        self.assertEqual(cls.__dict__[42], 'nonstring')
        self.assertNotIn('__qualname__', cls.__dict__)
        self.assertEqual(cls.__qualname__, 'Qualified')

    def test_module_doc_and_implicit_method_descriptors(self):
        class C:
            'original'
            def __new__(cls): return object.__new__(cls)
            def __init_subclass__(cls): pass
        view = C.__dict__
        C.__doc__ = 'updated'
        C.__module__ = 'elsewhere'
        self.assertEqual(view['__doc__'], 'updated')
        self.assertEqual(view['__module__'], 'elsewhere')
        self.assertIsInstance(view['__new__'], staticmethod)
        self.assertIsInstance(view['__init_subclass__'], classmethod)
        self.assertEqual(C.__doc__, 'updated')
        self.assertEqual(C.__module__, 'elsewhere')

if __name__ == '__main__': unittest.main()
