# CPython 3.14 Lib/test/test_exceptions.py at 18ef0f0cb52.
import unittest


class ExceptionMetadataTests(unittest.TestCase):


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
