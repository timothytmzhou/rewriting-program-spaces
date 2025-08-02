from dataclasses import dataclass
from core.grammar import Application, TreeGrammar, Unary, Binary


@dataclass(frozen=True)
class Let(Application):
    var: TreeGrammar
    binding: TreeGrammar
    expr: TreeGrammar


class Var(Unary): ...


class Num(Unary): ...


class Neg(Unary): ...


class App(Binary): ...


class Add(Binary): ...


class Sub(Binary): ...


class Mul(Binary): ...


class Div(Binary): ...


constructors: list[type[Application]] = [Let, Var, Num, Neg, App, Add, Sub, Mul, Div]
