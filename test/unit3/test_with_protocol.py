# CPython 3.14 Lib/test/test_with.py at 18ef0f0cb52.
# Synchronous CPython protocol-failure methods and helpers; async cases are separate.
import re
import unittest

def do_with(obj):
    with obj:
        pass


class FailureTestCase(unittest.TestCase):
    def testEnterAttributeError(self):
        class LacksEnter:
            def __exit__(self, type, value, traceback): ...

        with self.assertRaisesRegex(TypeError, re.escape((
            "object does not support the context manager protocol "
            "(missed __enter__ method)"
        ))):
            do_with(LacksEnter())


    def testExitAttributeError(self):
        class LacksExit:
            def __enter__(self): ...

        msg = re.escape((
            "object does not support the context manager protocol "
            "(missed __exit__ method)"
        ))
        # a missing __exit__ is reported missing before a missing __enter__
        with self.assertRaisesRegex(TypeError, msg):
            do_with(object())
        with self.assertRaisesRegex(TypeError, msg):
            do_with(LacksExit())








    def test_qualified_owner_names(self):
        # LOAD_SPECIAL uses %T, preserving the heap type's module/qualname.
        class Outer:
            class Missing: pass
        cls = Outer.Missing
        name = cls.__qualname__
        if cls.__module__ not in ('builtins', '__main__'):
            name = cls.__module__ + '.' + name
        for operation in (do_with,):
            with self.assertRaises(TypeError) as cm:
                operation(cls())
            self.assertTrue(str(cm.exception).startswith("'" + name + "' object"))
        cls.__module__ = 'custom'
        with self.assertRaises(TypeError) as cm: do_with(cls())
        self.assertTrue(str(cm.exception).startswith("'custom." + cls.__qualname__ + "' object"))

if __name__ == '__main__': unittest.main()
