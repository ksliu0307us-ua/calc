"""Quantities: a number with units attached.

A unit is a dict of symbol -> exponent, e.g. {"m": 1, "s": -1} for m/s. Every
symbol knows its factor to a base unit and which base dimensions it has, so
two quantities can be compared (same dimensions?) and converted. The symbols
the user typed are kept for display, so `10 m / 2 s` prints as `5 m/s`, not
in some canonical form.
"""

from dataclasses import dataclass, field
from fractions import Fraction

# symbol -> (factor to base unit, {base dimension: exponent})
UNITS = {
    # length (base: m)
    "m": (1, {"m": 1}), "km": (1000, {"m": 1}), "cm": (0.01, {"m": 1}), "mm": (0.001, {"m": 1}),
    "um": (1e-6, {"m": 1}), "nm": (1e-9, {"m": 1}),
    "in": (0.0254, {"m": 1}), "ft": (0.3048, {"m": 1}), "yd": (0.9144, {"m": 1}), "mi": (1609.344, {"m": 1}),
    "nmi": (1852, {"m": 1}),
    # area / volume
    "ha": (10_000, {"m": 2}), "acre": (4046.8564224, {"m": 2}),
    "L": (0.001, {"m": 3}), "mL": (1e-6, {"m": 3}), "gal": (0.003785411784, {"m": 3}),
    "qt": (0.000946352946, {"m": 3}), "pt": (0.000473176473, {"m": 3}), "cup": (0.0002365882365, {"m": 3}),
    "floz": (2.95735295625e-5, {"m": 3}), "tbsp": (1.478676478125e-5, {"m": 3}), "tsp": (4.92892159375e-6, {"m": 3}),
    # mass (base: kg)
    "kg": (1, {"kg": 1}), "g": (0.001, {"kg": 1}), "mg": (1e-6, {"kg": 1}), "t": (1000, {"kg": 1}),
    "lb": (0.45359237, {"kg": 1}), "oz": (0.028349523125, {"kg": 1}), "st": (6.35029318, {"kg": 1}),
    # time (base: s)
    "s": (1, {"s": 1}), "ms": (0.001, {"s": 1}), "us": (1e-6, {"s": 1}), "min": (60, {"s": 1}),
    "h": (3600, {"s": 1}), "hr": (3600, {"s": 1}), "day": (86400, {"s": 1}), "week": (604800, {"s": 1}),
    "year": (31557600, {"s": 1}),
    # speed
    "mph": (0.44704, {"m": 1, "s": -1}), "kph": (1000 / 3600, {"m": 1, "s": -1}), "knot": (1852 / 3600, {"m": 1, "s": -1}),
    # data (base: B)
    "bit": (0.125, {"B": 1}), "B": (1, {"B": 1}),
    "kB": (1e3, {"B": 1}), "MB": (1e6, {"B": 1}), "GB": (1e9, {"B": 1}), "TB": (1e12, {"B": 1}), "PB": (1e15, {"B": 1}),
    "KiB": (2**10, {"B": 1}), "MiB": (2**20, {"B": 1}), "GiB": (2**30, {"B": 1}), "TiB": (2**40, {"B": 1}),
    "kbit": (125, {"B": 1}), "Mbit": (125e3, {"B": 1}), "Gbit": (125e6, {"B": 1}),
    # energy / power (derived, in base dims kg m^2 s^-2)
    "J": (1, {"kg": 1, "m": 2, "s": -2}), "kJ": (1e3, {"kg": 1, "m": 2, "s": -2}),
    "cal": (4.184, {"kg": 1, "m": 2, "s": -2}), "kcal": (4184, {"kg": 1, "m": 2, "s": -2}),
    "Wh": (3600, {"kg": 1, "m": 2, "s": -2}), "kWh": (3.6e6, {"kg": 1, "m": 2, "s": -2}),
    "W": (1, {"kg": 1, "m": 2, "s": -3}), "kW": (1e3, {"kg": 1, "m": 2, "s": -3}), "hp": (745.69987158, {"kg": 1, "m": 2, "s": -3}),
    # angle (dimensionless, but we keep a pseudo-dimension so rad and deg convert)
    "rad": (1, {"rad": 1}), "deg": (3.141592653589793 / 180, {"rad": 1}),
}

ALIASES = {
    "meter": "m", "meters": "m", "metre": "m", "metres": "m", "kilometer": "km", "kilometers": "km",
    "inch": "in", "inches": "in", "feet": "ft", "foot": "ft", "yard": "yd", "yards": "yd",
    "mile": "mi", "miles": "mi", "liter": "L", "liters": "L", "litre": "L", "litres": "L", "l": "L",
    "gallon": "gal", "gallons": "gal", "gram": "g", "grams": "g", "kilogram": "kg", "kilograms": "kg",
    "pound": "lb", "pounds": "lb", "lbs": "lb", "ounce": "oz", "ounces": "oz", "ton": "t", "tonne": "t",
    "sec": "s", "secs": "s", "second": "s", "seconds": "s", "minute": "min", "minutes": "min", "mins": "min",
    "hour": "h", "hours": "h", "hrs": "h", "days": "day", "weeks": "week", "years": "year", "yr": "year",
    "byte": "B", "bytes": "B", "bits": "bit", "KB": "kB", "kb": "kB", "mb": "MB", "gb": "GB", "tb": "TB",
    "degree": "deg", "degrees": "deg", "radian": "rad", "radians": "rad", "watt": "W", "watts": "W",
    "joule": "J", "joules": "J", "calorie": "cal", "calories": "cal", "kilocalorie": "kcal",
}


class UnitError(Exception):
    pass


def lookup(symbol):
    symbol = ALIASES.get(symbol, symbol)
    if symbol not in UNITS:
        raise UnitError(f"unknown unit '{symbol}'")
    return symbol


def _merge(a, b, sign=1):
    out = dict(a)
    for k, v in b.items():
        out[k] = out.get(k, 0) + sign * v
        if out[k] == 0:
            del out[k]
    return out


def _scale(units, k):
    return {u: e * k for u, e in units.items()}


def dims_of(units):
    """Base dimensions of a unit dict, e.g. {"km":1,"h":-1} -> {"m":1,"s":-1}."""
    dims = {}
    for sym, exp in units.items():
        _, d = UNITS[sym]
        dims = _merge(dims, _scale(d, exp))
    return dims


def factor_of(units):
    f = 1.0
    for sym, exp in units.items():
        f *= UNITS[sym][0] ** exp
    return f


@dataclass
class Quantity:
    value: float
    units: dict = field(default_factory=dict)  # symbol -> exponent

    # -- helpers -----------------------------------------------------------

    @property
    def dims(self):
        return dims_of(self.units)

    @property
    def dimensionless(self):
        return not self.dims

    def in_base(self):
        return self.value * factor_of(self.units)

    def to(self, units):
        """Same quantity expressed in `units` (a dict), or raise if incompatible."""
        if dims_of(units) != self.dims:
            raise UnitError(f"can't convert {fmt_units(self.units) or 'a plain number'} to {fmt_units(units)}")
        return Quantity(self.in_base() / factor_of(units), dict(units))

    # -- arithmetic ----------------------------------------------------------

    def _same_dims(self, other, op):
        if self.dims != other.dims:
            a = fmt_units(self.units) or "a plain number"
            b = fmt_units(other.units) or "a plain number"
            raise UnitError(f"can't {op} {a} and {b}")

    def __add__(self, other):
        self._same_dims(other, "add")
        return Quantity(self.value + other.to(self.units).value, dict(self.units))

    def __sub__(self, other):
        self._same_dims(other, "subtract")
        return Quantity(self.value - other.to(self.units).value, dict(self.units))

    def __mul__(self, other):
        return Quantity(self.value * other.value, _merge(self.units, other.units)).simplified()

    def __truediv__(self, other):
        if other.value == 0:
            raise ZeroDivisionError("division by zero")
        return Quantity(self.value / other.value, _merge(self.units, other.units, -1)).simplified()

    def __neg__(self):
        return Quantity(-self.value, dict(self.units))

    def __pow__(self, other):
        if not other.dimensionless:
            raise UnitError("exponent must be a plain number")
        k = other.value
        if self.units and k != int(k):
            # fractional powers only work if every exponent divides evenly
            frac = Fraction(k).limit_denominator(100)
            new = {}
            for u, e in self.units.items():
                r = Fraction(e) * frac
                if r.denominator != 1:
                    raise UnitError(f"can't raise {fmt_units(self.units)} to the power {k}")
                new[u] = int(r)
            return Quantity(self.value ** k, new)
        return Quantity(self.value ** k, _scale(self.units, int(k)) if self.units else {})

    def simplified(self):
        """Fold units of the same dimension into one, e.g. m * ft -> m^2 (in m)."""
        by_dim = {}
        for sym, exp in self.units.items():
            key = tuple(sorted(UNITS[sym][1].items()))
            by_dim.setdefault(key, []).append(sym)
        units = dict(self.units)
        value = self.value
        for syms in by_dim.values():
            if len(syms) < 2:
                continue
            keep = syms[0]
            for other in syms[1:]:
                exp = units.pop(other)
                # convert `other`^exp into `keep`
                value *= (UNITS[other][0] / UNITS[keep][0]) ** exp
                units[keep] = units.get(keep, 0) + exp
            if units.get(keep) == 0:
                del units[keep]
        return Quantity(value, units)


def fmt_units(units):
    if not units:
        return ""
    pos = [(u, e) for u, e in units.items() if e > 0]
    neg = [(u, -e) for u, e in units.items() if e < 0]

    def part(items):
        return "·".join(f"{u}^{e}" if e != 1 else u for u, e in items)

    if pos and neg:
        return f"{part(pos)}/{part(neg)}"
    if pos:
        return part(pos)
    return "1/" + part(neg)


def fmt_number(x):
    if x == int(x) and abs(x) < 1e15:
        return str(int(x))
    s = f"{x:.10g}"
    return s


def fmt_quantity(q):
    u = fmt_units(q.units)
    return f"{fmt_number(q.value)} {u}".strip()
