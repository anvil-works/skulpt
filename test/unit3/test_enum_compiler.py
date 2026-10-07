# Selected complete CPython 3.14 test_enum.py methods and fixture.
import unittest
import enum
from enum import Enum, IntEnum, StrEnum, Flag, auto

class _EnumTests:
    values = None
    # Class-style portion of the upstream fixture, retaining only exercised objects.
    def setUp(self):
        class BaseEnum(self.enum_type):
            @enum.property
            def first(self):
                return '%s is first!' % self.name
        class MainEnum(BaseEnum):
            first = auto()
            second = auto()
            third = auto()
            if issubclass(self.enum_type, Flag):
                dupe = 3
            else:
                dupe = third
        self.MainEnum = MainEnum

        class LazyGNV(self.enum_type):
            def _generate_next_value_(name, start, last, values):
                pass
        self.LazyGNV = LazyGNV
        #
        class BusyGNV(self.enum_type):
            @staticmethod
            def _generate_next_value_(name, start, last, values):
                pass
        self.BusyGNV = BusyGNV
        self.is_flag = False
        self.names = ['first', 'second', 'third']
        self.values = [1, 2, 3]

    def test_basics(self):
        TE = self.MainEnum
        if self.is_flag:
            self.assertEqual(repr(TE), "<flag 'MainEnum'>")
            self.assertEqual(str(TE), "<flag 'MainEnum'>")
            self.assertEqual(format(TE), "<flag 'MainEnum'>")
            self.assertTrue(TE(5) is self.dupe2)
            self.assertTrue(7 in TE)
        else:
            self.assertEqual(repr(TE), "<enum 'MainEnum'>")
            self.assertEqual(str(TE), "<enum 'MainEnum'>")
            self.assertEqual(format(TE), "<enum 'MainEnum'>")
        self.assertEqual(list(TE), [TE.first, TE.second, TE.third])
        self.assertEqual(
                [m.name for m in TE],
                self.names,
                )
        self.assertEqual(
                [m.value for m in TE],
                self.values,
                )
        self.assertEqual(
                [m.first for m in TE],
                ['first is first!', 'second is first!', 'third is first!']
                )
        for member, name in zip(TE, self.names, strict=True):
            self.assertIs(TE[name], member)
        for member, value in zip(TE, self.values, strict=True):
            self.assertIs(TE(value), member)
        if issubclass(TE, StrEnum):
            self.assertTrue(TE.dupe is TE('third') is TE['dupe'])
        elif TE._member_type_ is str:
            self.assertTrue(TE.dupe is TE('3') is TE['dupe'])
        elif issubclass(TE, Flag):
            self.assertTrue(TE.dupe is TE(3) is TE['dupe'])
        else:
            self.assertTrue(TE.dupe is TE(self.values[2]) is TE['dupe'])


    def test_bool_is_true(self):
        class Empty(self.enum_type):
            pass
        self.assertTrue(Empty)
        #
        self.assertTrue(self.MainEnum)
        for member in self.MainEnum:
            self.assertTrue(member)


    def test_changing_member_fails(self):
        MainEnum = self.MainEnum
        with self.assertRaises(AttributeError):
            self.MainEnum.second = 'really first'


    def test_enum_in_enum_out(self):
        Main = self.MainEnum
        self.assertIs(Main(Main.first), Main.first)


    def test_gnv_is_static(self):
        lazy = self.LazyGNV
        busy = self.BusyGNV
        self.assertTrue(type(lazy.__dict__['_generate_next_value_']) is staticmethod)
        self.assertTrue(type(busy.__dict__['_generate_next_value_']) is staticmethod)


    def test_hash(self):
        MainEnum = self.MainEnum
        mapping = {}
        mapping[MainEnum.first] = '1225'
        mapping[MainEnum.second] = '0315'
        mapping[MainEnum.third] = '0704'
        self.assertEqual(mapping[MainEnum.second], '0315')


class TestPlainEnumClass(_EnumTests, unittest.TestCase):
    enum_type = Enum

class TestIntEnumClass(_EnumTests, unittest.TestCase):
    enum_type = IntEnum

if __name__ == '__main__': unittest.main()
