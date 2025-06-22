from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, replace
from typing import Optional
import regex as re
from regex import Pattern


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
    terminal_regex: Pattern
    prefix: str = ""
    fixed: bool = False

    # TODO: If we introduce support for put, we will need to generalize update.
    def update(self, other: RegexLeaf) -> Optional[RegexLeaf]:
        if self.sort == other.sort:
            return other
        return None

    def nullable(self) -> bool:
        return re.fullmatch(self.terminal_regex, self.prefix)

    def nonempty(self) -> bool:
        return re.fullmatch(self.terminal_regex, self.prefix, partial=True)

    def deriv(self, string: str) -> RegexLeaf:
        return RegexLeaf(self.sort, self.terminal_regex, self.prefix + string)

    def fix(self) -> RegexLeaf:
        return replace(self, fixed=True)

    def __str__(self) -> str:
        return f"({self.sort}, {self.prefix})"
