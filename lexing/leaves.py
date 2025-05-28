from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, replace
from typing import Optional
import greenery as grn

EPS = grn.rxelems.from_fsm(grn.EPSILON)


class Leaf[T](ABC):
    @abstractmethod
    def update(self, other: T) -> Optional[Leaf]:
        """
        Updates the leaf with a value.
        May return None if the value is incompatible."""
        pass


@dataclass(frozen=True)
class IntLeaf[int](Leaf):
    value: int
    matched: bool = False

    def update(self, other) -> Optional[IntLeaf]:
        if self.value == other:
            return replace(self, matched=True)
        return None


@dataclass(frozen=True)
class StringLeaf[str](Leaf):
    value: str
    matched: bool = False

    def update(self, other: str) -> Optional[StringLeaf]:
        if self.value == other:
            return replace(self, matched=True)
        return None


@dataclass(frozen=True)
class RegexLeaf(Leaf):
    sort: str
    remainder: grn.Pattern
    prefix: str = ""

    # TODO: If we introduce support for put, we will need to generalize update.
    def update(self, other: RegexLeaf) -> Optional[RegexLeaf]:
        if self.sort == other.sort:
            return other
        return None

    def nullable(self) -> bool:
        return self.remainder.matches("")

    def nonempty(self) -> bool:
        return not self.remainder.empty()

    def deriv(self, string: str) -> RegexLeaf:
        return RegexLeaf(self.sort, self.remainder.derive(string), self.prefix + string)
