from __future__ import annotations
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional, TypeVar, Generic

K = TypeVar('K')


@dataclass
class Pair:
    first: float
    second: float

    def __add__(self, other: Pair) -> Pair:
        return Pair(self.first + other.first, self.second + other.second)

    def avg(self) -> float:
        if self.second == 0:
            return 0
        return self.first / self.second

    def __repr__(self):
        return f"({self.first}, {self.second})"


@dataclass
class Totaler(Generic[K]):
    # prompt_id, run_number, key -> [total , num_totaled]
    dct: defaultdict[tuple[int, int, K], Pair] = field(
        default_factory=lambda: defaultdict(lambda: Pair(0, 0))
    )
    curr_prompt_num = 0
    curr_run_num = 0

    def clear(self):
        self.dct = defaultdict(lambda: Pair(0, 0))

    def set_indices(self, prompt_num, run_num):
        self.curr_prompt_num = prompt_num
        self.curr_run_num = run_num

    def get_prompt_num(self):
        return self.curr_prompt_num

    def get_run_num(self):
        return self.curr_run_num

    # Functions to compute sums and averages
    # Treat None arguments as accepting any
    def sum(
        self,
        pnum: Optional[int] = None,
        rnum: Optional[int] = None,
        k: Optional[K] = None
    ):
        total = Pair(0.0, 0.0)
        for key in self.dct:
            if (
                (pnum is None or key[0] == pnum)
                and (rnum is None or key[1] == rnum)
                and (k is None or key[2] == k)
            ):
                total += self.dct[key]
        return total

    def avg(
        self,
        pnum: Optional[int] = None,
        rnum: Optional[int] = None,
        k: Optional[K] = None
    ):
        total = self.sum(pnum=pnum, rnum=rnum, k=k)
        return total.avg()

    # Functions to update totaler
    def add_from(self, other: Totaler[K]):
        for key in other.dct:
            self.dct[key] = self.dct[key] + other.dct[key]

    def incr(self, k: K, val: float):
        self.dct[(self.curr_prompt_num, self.curr_run_num, k)] += Pair(val, 1)

    def decr(self, k: K, val: float):
        self.dct[(self.curr_prompt_num, self.curr_run_num, k)] += Pair(-val, -1)
