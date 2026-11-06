"""Tokenize and evaluate one line.

Grammar, loosest to tightest binding:

    assignment   name = expr
    conversion   expr to unit
    additive     + -
    multiplicative * /
    implicit multiplication   "5 km", "2 pi", "(1+2) m"
    unary        - +
    power        ^   (right-associative, binds tighter than unary minus: -2^2 = -4)
    postfix      %   (percent)
    atoms        numbers, names, units, function calls, parentheses

It's a Pratt parser that evaluates as it goes, so there's no separate AST.
"""

import math
import re

from .units import Quantity, UnitError, lookup, fmt_units

_TOKEN = re.compile(
    r"""
    (?P<num>\d+(?:_\d+)*(?:\.\d+)?(?:[eE][+-]?\d+)?|\.\d+)
  | (?P<name>[A-Za-z_][A-Za-z0-9_]*)
  | (?P<op>\*\*|[-+*/^%(),=])
  | (?P<ws>\s+)
  | (?P<bad>.)
    """,
    re.VERBOSE,
)


class CalcError(Exception):
    pass


def tokenize(text):
    out = []
    for m in _TOKEN.finditer(text):
        kind = m.lastgroup
        if kind == "ws":
            continue
        if kind == "bad":
            raise CalcError(f"unexpected character '{m.group()}'")
        val = m.group()
        if kind == "op" and val == "**":
            val = "^"
        if kind == "name" and val == "to":
            kind = "op"
        out.append((kind, val))
    out.append(("eof", ""))
    return out


FUNCTIONS = {
    "sqrt": lambda q: q ** Quantity(0.5),
    "abs": lambda q: Quantity(abs(q.value), dict(q.units)),
    "round": lambda q: Quantity(round(q.value), dict(q.units)),
    "floor": lambda q: Quantity(math.floor(q.value), dict(q.units)),
    "ceil": lambda q: Quantity(math.ceil(q.value), dict(q.units)),
}

_PLAIN = {
    "sin": math.sin, "cos": math.cos, "tan": math.tan, "asin": math.asin, "acos": math.acos, "atan": math.atan,
    "ln": math.log, "log": math.log10, "log2": math.log2, "exp": math.exp,
}

CONSTANTS = {"pi": math.pi, "e": math.e, "tau": math.tau}


def _plain_fn(name):
    f = _PLAIN[name]

    def wrapped(q):
        if name in ("sin", "cos", "tan") and q.units:
            q = q.to({"rad": 1})
        elif not q.dimensionless:
            raise CalcError(f"{name}() needs a plain number, got {fmt_units(q.units)}")
        return Quantity(f(q.value))

    return wrapped


for _n in _PLAIN:
    FUNCTIONS[_n] = _plain_fn(_n)


class Parser:
    def __init__(self, text, variables):
        self.toks = tokenize(text)
        self.i = 0
        self.vars = variables

    # -- token helpers ------------------------------------------------------

    def peek(self):
        return self.toks[self.i]

    def next(self):
        tok = self.toks[self.i]
        self.i += 1
        return tok

    def expect(self, kind, val=None):
        tok = self.next()
        if tok[0] != kind or (val is not None and tok[1] != val):
            want = val or kind
            got = tok[1] or "end of input"
            raise CalcError(f"expected '{want}' but found '{got}'")
        return tok

    # -- entry --------------------------------------------------------------

    def statement(self):
        # assignment?
        if self.peek()[0] == "name" and self.toks[self.i + 1] == ("op", "="):
            name = self.next()[1]
            self.next()
            if name in FUNCTIONS or name in CONSTANTS:
                raise CalcError(f"'{name}' is built in and can't be reassigned")
            value = self.conversion()
            self.expect("eof")
            self.vars[name] = value
            return value
        value = self.conversion()
        self.expect("eof")
        return value

    def conversion(self):
        value = self.additive()
        while self.peek() == ("op", "to"):
            self.next()
            target = self.unit_expr()
            try:
                value = value.to(target)
            except UnitError as e:
                raise CalcError(str(e))
        return value

    def unit_expr(self):
        """A unit after `to`: things like `km`, `m/s`, `kg*m/s^2`, `mph`."""
        units = self._unit_term()
        while self.peek()[0] == "op" and self.peek()[1] in ("*", "/"):
            op = self.next()[1]
            more = self._unit_term()
            for u, e in more.items():
                units[u] = units.get(u, 0) + (e if op == "*" else -e)
        return {u: e for u, e in units.items() if e != 0}

    def _unit_term(self):
        tok = self.next()
        if tok[0] != "name":
            raise CalcError(f"expected a unit after 'to', found '{tok[1] or 'end of input'}'")
        try:
            sym = lookup(tok[1])
        except UnitError as e:
            raise CalcError(str(e))
        exp = 1
        if self.peek() == ("op", "^"):
            self.next()
            sign = 1
            if self.peek() == ("op", "-"):
                self.next()
                sign = -1
            exp = sign * int(self.expect("num")[1])
        return {sym: exp}

    # -- binary levels ------------------------------------------------------

    def additive(self):
        left = self.multiplicative()
        while self.peek()[0] == "op" and self.peek()[1] in "+-":
            op = self.next()[1]
            right = self.multiplicative()
            try:
                left = left + right if op == "+" else left - right
            except UnitError as e:
                raise CalcError(str(e))
        return left

    def multiplicative(self):
        left = self.implicit()
        while self.peek()[0] == "op" and self.peek()[1] in "*/":
            op = self.next()[1]
            right = self.implicit()
            try:
                left = left * right if op == "*" else left / right
            except ZeroDivisionError:
                raise CalcError("division by zero")
        return left

    def implicit(self):
        left = self.unary()
        # a name or '(' right after a value means multiply: 5 km, 2 pi, 3 (4+1)
        while self.peek()[0] == "name" or self.peek() == ("op", "("):
            if self.peek()[0] == "name" and self.peek()[1] == "to":
                break
            right = self.unary()
            left = left * right
        return left

    def unary(self):
        if self.peek() == ("op", "-"):
            self.next()
            return -self.unary()
        if self.peek() == ("op", "+"):
            self.next()
            return self.unary()
        return self.power()

    def power(self):
        base = self.postfix()
        if self.peek() == ("op", "^"):
            self.next()
            exp = self.unary()  # right-assoc, and allows 2^-1
            try:
                return base ** exp
            except UnitError as e:
                raise CalcError(str(e))
            except (OverflowError, ValueError) as e:
                raise CalcError(f"bad power: {e}")
        return base

    def postfix(self):
        value = self.atom()
        while self.peek() == ("op", "%"):
            self.next()
            value = Quantity(value.value / 100, dict(value.units))
        return value

    # -- atoms --------------------------------------------------------------

    def atom(self):
        kind, val = self.next()
        if kind == "num":
            return Quantity(float(val.replace("_", "")))
        if kind == "op" and val == "(":
            inner = self.conversion()
            self.expect("op", ")")
            return inner
        if kind == "name":
            if val in FUNCTIONS and self.peek() == ("op", "("):
                self.next()
                arg = self.conversion()
                self.expect("op", ")")
                try:
                    return FUNCTIONS[val](arg)
                except (UnitError, ValueError) as e:
                    raise CalcError(str(e))
            if val in self.vars:
                q = self.vars[val]
                return Quantity(q.value, dict(q.units))
            if val in CONSTANTS:
                return Quantity(CONSTANTS[val])
            try:
                return Quantity(1.0, {lookup(val): 1})
            except UnitError:
                raise CalcError(f"unknown name '{val}'")
        raise CalcError(f"unexpected '{val or 'end of input'}'")


def evaluate(text, variables=None):
    """Evaluate one line. `variables` is mutated by assignments and `last`."""
    if variables is None:
        variables = {}
    text = text.strip()
    if not text:
        raise CalcError("nothing to evaluate")
    result = Parser(text, variables).statement()
    variables["last"] = result
    variables["_"] = result
    return result
