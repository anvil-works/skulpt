"""Compiler-created typing objects; further typing APIs remain unimplemented."""
from _typing import TypeAliasType, TypeVar, NoDefault
from types import GenericAlias, UnionType
Union = UnionType

def get_args(tp):
    if isinstance(tp, (GenericAlias, UnionType)):
        return tp.__args__
    return ()

def get_origin(tp):
    if isinstance(tp, (GenericAlias, UnionType)):
        return tp.__origin__
    return None
