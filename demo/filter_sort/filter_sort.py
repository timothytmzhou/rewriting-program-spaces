from core.grammar import Unary, Binary


class Var(Unary): ...


class App(Binary): ...


constructors = [Var, App]
