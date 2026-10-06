# CPython 3.14 Lib/test/test_sys.py at 18ef0f0cb52.
# Method bodies and assertions unchanged. Local support context managers replace
# CPython's test.support dependency; StringIO fallback supplies Skulpt's stream.
import unittest
import sys
import builtins
try:
    from io import StringIO
except ImportError:
    from StringIO import StringIO

class _SwapAttr:
    def __init__(self, obj, attr, value):
        self.obj, self.attr, self.value = obj, attr, value
    def __enter__(self):
        self.old = getattr(self.obj, self.attr)
        setattr(self.obj, self.attr, self.value)
        return self.old
    def __exit__(self, *exc):
        setattr(self.obj, self.attr, self.old)

class _CapturedStdout(_SwapAttr):
    def __init__(self):
        super().__init__(sys, 'stdout', StringIO())
    def __enter__(self):
        super().__enter__()
        return self.value

class support:
    swap_attr = _SwapAttr
    captured_stdout = _CapturedStdout

class DisplayHookTest(unittest.TestCase):
    # Portable spelling of the unittest 3.14 assertion used by upstream.
    def assertNotHasAttr(self, obj, name):
        self.assertFalse(hasattr(obj, name))

    def test_original_displayhook(self):
        dh = sys.__displayhook__

        with support.captured_stdout() as out:
            dh(42)

        self.assertEqual(out.getvalue(), "42\n")
        self.assertEqual(builtins._, 42)

        del builtins._

        with support.captured_stdout() as out:
            dh(None)

        self.assertEqual(out.getvalue(), "")
        self.assertNotHasAttr(builtins, "_")

        # sys.displayhook() requires arguments
        self.assertRaises(TypeError, dh)

        stdout = sys.stdout
        try:
            del sys.stdout
            self.assertRaises(RuntimeError, dh, 42)
        finally:
            sys.stdout = stdout

    def test_lost_displayhook(self):
        displayhook = sys.displayhook
        try:
            del sys.displayhook
            code = compile("42", "<string>", "single")
            self.assertRaises(RuntimeError, eval, code)
        finally:
            sys.displayhook = displayhook

    def test_custom_displayhook(self):
        def baddisplayhook(obj):
            raise ValueError

        with support.swap_attr(sys, 'displayhook', baddisplayhook):
            code = compile("42", "<string>", "single")
            self.assertRaises(ValueError, eval, code)

if __name__ == "__main__":
    unittest.main()
