"""Compiler-created typing objects; further typing APIs remain unimplemented."""
import _typing_legacy as _legacy
from _typing_legacy import *
from _typing import TypeAliasType
from types import GenericAlias, UnionType

def get_args(tp):
    if isinstance(tp, (GenericAlias, UnionType)):
        return tp.__args__
    return _legacy.get_args(tp)

def get_origin(tp):
    if isinstance(tp, (GenericAlias, UnionType)):
        return tp.__origin__
    return _legacy.get_origin(tp)
