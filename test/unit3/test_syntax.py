# Selected unchanged CPython3.14 Lib/test/test_syntax.py methods at18ef0f0cb52.
import re
import unittest

class SyntaxTestCase(unittest.TestCase):
    def _check_error(self, code, errtext,
                     filename="<testcase>", mode="exec", subclass=None,
                     lineno=None, offset=None, end_lineno=None, end_offset=None):
        """Check that compiling code raises SyntaxError with errtext.

        errtest is a regular expression that must be present in the
        text of the exception raised.  If subclass is specified it
        is the expected subclass of SyntaxError (e.g. IndentationError).
        """
        try:
            compile(code, filename, mode)
        except SyntaxError as err:
            if subclass and not isinstance(err, subclass):
                self.fail("SyntaxError is not a %s" % subclass.__name__)
            mo = re.search(errtext, str(err))
            if mo is None:
                self.fail("SyntaxError did not contain %r" % (errtext,))
            self.assertEqual(err.filename, filename)
            if lineno is not None:
                self.assertEqual(err.lineno, lineno)
            if offset is not None:
                self.assertEqual(err.offset, offset)
            if end_lineno is not None:
                self.assertEqual(err.end_lineno, end_lineno)
            if end_offset is not None:
                self.assertEqual(err.end_offset, end_offset)

        else:
            self.fail("compile() did not raise SyntaxError")

    def test_return_outside_function(self):
        self._check_error("if 0: return",                "outside function")
        self._check_error("if 0: return\nelse:  x=1",    "outside function")
        self._check_error("if 1: pass\nelse: return",    "outside function")
        self._check_error("while 0: return",             "outside function")
        self._check_error("class C:\n  if 0: return",    "outside function")
        self._check_error("class C:\n  while 0: return", "outside function")
        self._check_error("class C:\n  while 0: return\n  else:  x=1",
                          "outside function")
        self._check_error("class C:\n  if 0: return\n  else: x= 1",
                          "outside function")
        self._check_error("class C:\n  if 1: pass\n  else: return",
                          "outside function")

    def test_break_outside_loop(self):
        msg = "outside loop"
        self._check_error("break", msg, lineno=1)
        self._check_error("if 0: break", msg, lineno=1)
        self._check_error("if 0: break\nelse:  x=1", msg, lineno=1)
        self._check_error("if 1: pass\nelse: break", msg, lineno=2)
        self._check_error("class C:\n  if 0: break", msg, lineno=2)
        self._check_error("class C:\n  if 1: pass\n  else: break",
                          msg, lineno=3)
        self._check_error("with object() as obj:\n break",
                          msg, lineno=2)

    def test_continue_outside_loop(self):
        msg = "not properly in loop"
        self._check_error("if 0: continue", msg, lineno=1)
        self._check_error("if 0: continue\nelse:  x=1", msg, lineno=1)
        self._check_error("if 1: pass\nelse: continue", msg, lineno=2)
        self._check_error("class C:\n  if 0: continue", msg, lineno=2)
        self._check_error("class C:\n  if 1: pass\n  else: continue",
                          msg, lineno=3)
        self._check_error("with object() as obj:\n    continue",
                          msg, lineno=2)

if __name__ == '__main__':
    unittest.main()
