from __future__ import annotations
from dataclasses import dataclass, replace
from typing import Any, Optional
from regex import Pattern
from core.grammar import TreeGrammar


# TODO: should make seperate TokenDef class for ConstantParsers
@dataclass(frozen=True)
class Token(TreeGrammar):
    token_type: Any
    token_regex: Pattern
    prefix: str = ""
    is_complete: bool = False

    def update(self, other: Token) -> Optional[Token]:
        return other if self.token_type == other.token_type else None

    def nullable(self) -> bool:
        return bool(self.token_regex.fullmatch(self.prefix))

    def nonempty(self) -> bool:
        return bool(self.token_regex.fullmatch(self.prefix, partial=True))

    def extend(self, string: str) -> Token:
        return Token(self.token_type, self.token_regex, self.prefix + string)

    def complete(self) -> Token:
        return replace(self, is_complete=True)

    def __str__(self) -> str:
        return f"({self.token_type}, {self.prefix})"
