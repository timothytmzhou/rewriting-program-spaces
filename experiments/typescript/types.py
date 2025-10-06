from __future__ import annotations
from dataclasses import dataclass
from abc import ABC

from core.utils import flatten

# TYPES

MAX_DEPTH = 3


class Type(ABC):
    """
    An ADT for simple sets of types.
    """
    pass

    def condense(self, depth: int = MAX_DEPTH) -> Type:
        """
        Returns EmptyType if self is empty.
        Else, returns a version of self cut off at depth `depth`.
        """
        return self if depth > 0 else TopType()

    def __contains__(self, contents) -> bool:
        return contains(self, contents)


@dataclass(frozen=True)
class NumberType(Type):
    pass


@dataclass(frozen=True)
class StringType(Type):
    pass


@dataclass(frozen=True)
class BooleanType(Type):
    pass


@dataclass(frozen=True)
class UnionType(Type):
    first: Type
    second: Type

    @classmethod
    def of(cls, first, second) -> Type:
        out = cls(first, second).condense()
        return out

    def condense(self, depth: int = 3) -> Type:
        # Condense children
        condensed_first = self.first.condense(depth)
        condensed_second = self.second.condense(depth)
        # Check if empty
        if (isinstance(condensed_first, EmptyType)):
            return condensed_second
        if (isinstance(condensed_second, EmptyType)):
            return condensed_first
        if condensed_first == condensed_second:
            return condensed_first
        # Return accordingly
        return (UnionType(condensed_first, condensed_second))


@dataclass(frozen=True)
class ProdType(Type):
    """
    ProdType with no types=() represents the void type.
    This is distinct from EmptySet()
    """
    types: tuple[Type, ...]
    # If extensible == True, then the product type may match
    # any possibly longer prodtype as long as the type containment
    # holds up to the length of types.
    extensible: bool = False

    @classmethod
    def of(
        cls, *typesets, extensible: bool = False
    ) -> ProdType | EmptyType:
        out = cls(flatten(typesets, tuple), extensible=extensible).condense()
        assert not isinstance(out, TopType)
        return out

    def condense(self, depth: int = 3) -> ProdType | TopType | EmptyType:
        # Condense children
        condensed = tuple(typ.condense(depth - 1) for typ in self.types)
        # Check if empty
        if any(isinstance(child, EmptyType) for child in condensed):
            return EmptyType()
        # Return accordingly
        if depth == 0:
            return TopType()
        return ProdType(condensed, extensible=self.extensible)


@dataclass(frozen=True)
class FuncType(Type):
    params: ProdType
    return_type: Type

    @classmethod
    def of(
        cls, params: ProdType | EmptyType, return_type: Type
    ) -> FuncType | EmptyType:
        if isinstance(params, EmptyType):
            return EmptyType()
        out = FuncType(params, return_type).condense()
        assert not isinstance(out, TopType)
        return out

    def condense(self, depth: int = MAX_DEPTH) -> FuncType | EmptyType | TopType:
        condensed_params = self.params.condense(depth)
        condensed_return = self.return_type.condense(depth - 1)
        if (
            isinstance(condensed_params, EmptyType)
            or isinstance(condensed_return, EmptyType)
        ):
            return EmptyType()
        if depth == 0:
            return TopType()
        assert not isinstance(condensed_params, TopType)
        return FuncType(condensed_params, condensed_return)


@dataclass(frozen=True)
class TopType(Type):
    """Either Top or Top - void"""
    contains_void: bool = True

    def condense(self, depth: int = MAX_DEPTH) -> TopType:
        return self


@dataclass(frozen=True)
class EmptyType(Type):
    """A type with no inhabitants -- the empty type"""
    def condense(self, depth: int = MAX_DEPTH) -> EmptyType:
        return self


# Singleton instances for primitive types
NUMBERTYPE = NumberType()
STRINGTYPE = StringType()
BOOLEANTYPE = BooleanType()
VOIDTYPE = ProdType.of()


def contains(big: Type, little: Type) -> bool:
    match big, little:
        case UnionType(first, second), _:
            return contains(first, little) or contains(second, little)
        case TopType(contains_void), _:
            return True if contains_void or little != VOIDTYPE else False
        case _, EmptyType():
            return True
        case ((NumberType(), NumberType())
              | (StringType(), StringType())
              | (BooleanType(), BooleanType())):
            return True
        case (ProdType(children1, extensible=extensible1),
              ProdType(children2, extensible=extensible2)):
            # Compare possible lengths.
            # If type1 can be extended, then type1 must not be too long to match type2.
            if extensible1 and len(children1) > len(children2):
                return False
            # If type2 is arbitrarily long and won't fit in type 1, return False.
            if not extensible1 and extensible2:
                return False
            # If neither is extensible, they must be the same length.
            if not extensible1 and not extensible2 and len(children1) != len(children2):
                return False

            # All children of type2 must fit inside type1, unless they match to top
            # when type1 is too short.
            return all(
                contains(child1, child2)
                for child1, child2 in zip(children1, children2[:len(children1)])
            )
        case FuncType(params1, ret1), FuncType(params2, ret2):
            return contains(params1, params2) and contains(ret1, ret2)
        case ProdType(children1, extensible=extensible1), _:
            if len(children1) == 1:
                return contains(children1[0], little)
            if extensible1 and len(children1) == 0:
                return True
            return False
        case _, ProdType(children2, extensible=extensible2):
            if len(children2) == 1 and not extensible2:
                return contains(big, children2[0])
            return False
        case _:
            return False


def get_non_void(typ: Type) -> Type:
    match typ:
        case TopType(_):
            return TopType(contains_void=False)
        case ProdType(types, extensible=extensible):
            if len(types) == 0:
                if extensible:
                    return ProdType.of(TopType(), extensible=extensible)
                return EmptyType()
            return typ
        case _:
            return typ
