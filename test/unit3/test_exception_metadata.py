# CPython 3.14 Lib/test/test_exceptions.py at 18ef0f0cb52.
import unittest

class SubTest:
    def __enter__(self): return self
    def __exit__(self, *args): return False

class ExceptionMetadataTests(unittest.TestCase):
    def subTest(self, *args, **kwargs): return SubTest()
    def assertNotHasAttr(self, obj, name): self.assertFalse(hasattr(obj, name))

    def test_notes(self):
        for e in [BaseException(1), Exception(2), ValueError(3)]:
            with self.subTest(e=e):
                self.assertNotHasAttr(e, '__notes__')
                e.add_note("My Note")
                self.assertEqual(e.__notes__, ["My Note"])

                with self.assertRaises(TypeError):
                    e.add_note(42)
                self.assertEqual(e.__notes__, ["My Note"])

                e.add_note("Your Note")
                self.assertEqual(e.__notes__, ["My Note", "Your Note"])

                del e.__notes__
                self.assertNotHasAttr(e, '__notes__')

                e.add_note("Our Note")
                self.assertEqual(e.__notes__, ["Our Note"])

                e.__notes__ = 42
                self.assertEqual(e.__notes__, 42)

                with self.assertRaises(TypeError):
                    e.add_note("will not work")
                self.assertEqual(e.__notes__, 42)

    def testChainingAttrs(self):
        e = Exception()
        self.assertIsNone(e.__context__)
        self.assertIsNone(e.__cause__)

        e = TypeError()
        self.assertIsNone(e.__context__)
        self.assertIsNone(e.__cause__)

        class MyException(OSError):
            pass

        e = MyException()
        self.assertIsNone(e.__context__)
        self.assertIsNone(e.__cause__)

    def testChainingDescriptors(self):
        try:
            raise Exception()
        except Exception as exc:
            e = exc

        self.assertIsNone(e.__context__)
        self.assertIsNone(e.__cause__)
        self.assertFalse(e.__suppress_context__)

        e.__context__ = NameError()
        e.__cause__ = None
        self.assertIsInstance(e.__context__, NameError)
        self.assertIsNone(e.__cause__)
        self.assertTrue(e.__suppress_context__)
        e.__suppress_context__ = False
        self.assertFalse(e.__suppress_context__)
        with self.assertRaisesRegex(TypeError,
                                    'attribute value type must be bool'):
            e.__suppress_context__ = 1
        with self.assertRaisesRegex(TypeError,
                                    "can't delete numeric/char attribute"):
            del e.__suppress_context__
        self.assertFalse(e.__suppress_context__)

class ExceptionNotesRegression(unittest.TestCase):
    def test_notes_descriptors_and_native_append(self):
        class Notes(list):
            def append(self, note):
                raise AssertionError('native append must bypass Python overrides')
        class Note(str):
            pass
        class Error(Exception):
            @property
            def __notes__(self):
                return self.storage
            @__notes__.setter
            def __notes__(self, value):
                self.storage = value
        error = Error()
        note = Note('first')
        self.assertIsNone(error.add_note(note))
        self.assertIs(error.storage[0], note)
        error.storage = Notes()
        error.add_note('second')
        self.assertEqual(error.storage, ['second'])
        class Broken(Exception):
            @property
            def __notes__(self):
                raise ValueError('getter')
        with self.assertRaisesRegex(ValueError, 'getter'):
            Broken().add_note('note')
        class ReadOnly(Exception):
            @property
            def __notes__(self):
                raise AttributeError('absent')
        with self.assertRaises(AttributeError):
            ReadOnly().add_note('note')
        error = Exception()
        with self.assertRaises(TypeError):
            error.__cause__ = 1
        with self.assertRaises(TypeError):
            del error.__cause__
        self.assertFalse(error.__suppress_context__)
        cause = ValueError()
        error.__cause__ = cause
        self.assertIs(error.__cause__, cause)
        self.assertTrue(error.__suppress_context__)

if __name__ == "__main__": unittest.main()
