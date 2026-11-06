import math

import pytest

from calc import parser
from calc.cli import main
from calc.parser import CalcError, evaluate
from calc.units import fmt_quantity


def ev(text, variables=None):
    return fmt_quantity(evaluate(text, variables))


# --- plain arithmetic -----------------------------------------------------------

@pytest.mark.parametrize("expr,expected", [
    ("1 + 2 * 3", "7"),
    ("(1 + 2) * 3", "9"),
    ("2 ^ 3 ^ 2", "512"),          # right-associative
    ("-2 ^ 2", "-4"),              # ^ binds tighter than unary minus
    ("2 ** 10", "1024"),
    ("7 / 2", "3.5"),
    ("1_000_000 / 4", "250000"),
    ("1e3 + .5", "1000.5"),
    ("2 pi", "6.283185307"),
    ("3 (4 + 1)", "15"),
    ("20%", "0.2"),
    ("150 * 20%", "30"),
    ("sqrt(16) + abs(-3)", "7"),
    ("round(2.6) + floor(2.6) + ceil(2.1)", "8"),
    ("log(1000) + ln(e) + log2(8)", "7"),
])
def test_arithmetic(expr, expected):
    assert ev(expr) == expected


def test_trig_in_degrees_and_radians():
    assert ev("sin(90 deg)") == "1"
    assert abs(evaluate("cos(pi)").value + 1) < 1e-12
    assert ev("sin(pi/2)") == "1"


# --- units ----------------------------------------------------------------------

@pytest.mark.parametrize("expr,expected", [
    ("5 km to m", "5000 m"),
    ("3 ft + 2 m", "9.56167979 ft"),
    ("2 m + 3 ft", "2.9144 m"),
    ("1 mi to km", "1.609344 km"),
    ("100 kph to mph", "62.13711922 mph"),
    ("5 km / 20 min to mph", "9.320567884 mph"),
    ("10 m / 2 s", "5 m/s"),
    ("1.5 GiB to MB", "1610.612736 MB"),
    ("8 Mbit/s * 1 h to GB", "3.6 GB"),
    ("2 lb to kg", "0.90718474 kg"),
    ("1 gal to L", "3.785411784 L"),
    ("3 m * 4 m", "12 m^2"),
    ("12 m^2 / 3 m", "4 m"),
    ("sqrt(16 m^2)", "4 m"),
    ("(2 m)^3 to L", "8000 L"),
    ("2 m * 3 ft", "1.8288 m^2"),          # mixed length units fold into one
    ("60 mph * 2 h to mi", "120 mi"),
    ("1 kWh to kJ", "3600 kJ"),
    ("500 kcal to kJ", "2092 kJ"),
    ("3 hours + 30 minutes to min", "210 min"),
    ("1 / (2 s)", "0.5 1/s"),
])
def test_units(expr, expected):
    assert ev(expr) == expected


def test_unit_aliases():
    assert ev("2 miles to kilometers") == "3.218688 km"
    assert ev("3 pounds to grams") == "1360.77711 g"


def test_unit_errors():
    with pytest.raises(CalcError, match="can't add"):
        evaluate("2 m + 3 s")
    with pytest.raises(CalcError, match="can't convert"):
        evaluate("2 kg to m")
    with pytest.raises(CalcError, match="unknown"):
        evaluate("2 furlongs")
    with pytest.raises(CalcError, match="plain number"):
        evaluate("ln(2 m)")
    with pytest.raises(CalcError, match="power"):
        evaluate("sqrt(2 m)")


# --- variables -------------------------------------------------------------------

def test_variables_and_last():
    v = {}
    assert ev("speed = 30 mph", v) == "30 mph"
    assert ev("speed * 2 h to mi", v) == "60 mi"
    assert ev("last / 2", v) == "30 mi"
    assert ev("_ to km", v) == "48.28032 km"
    assert ev("speed", v) == "30 mph"


def test_cannot_shadow_builtins():
    with pytest.raises(CalcError, match="built in"):
        evaluate("pi = 3")


# --- syntax errors ----------------------------------------------------------------

@pytest.mark.parametrize("expr", ["1 +", "(1 + 2", "1 2 3 $", "2 to", "", "foo + 1", "1 / 0"])
def test_errors_are_calc_errors(expr):
    with pytest.raises(CalcError):
        evaluate(expr)


# --- cli ----------------------------------------------------------------------------

def test_cli_one_shot(capsys):
    assert main(["5", "km", "to", "mi"]) == 0
    assert capsys.readouterr().out.strip() == "3.106855961 mi"
    assert main(["2", "m", "+", "3", "s"]) == 1
    assert "can't add" in capsys.readouterr().err


def test_cli_file(tmp_path, capsys):
    f = tmp_path / "calc.txt"
    f.write_text("# fuel\ndist = 400 km\nfuel = 32 L\nfuel / dist * 100 km  # per 100 km\nbogus +\n")
    assert main(["-f", str(f)]) == 1
    out, err = capsys.readouterr()
    assert "fuel / dist * 100 km = 8 L" in out
    assert "line 5" in err
