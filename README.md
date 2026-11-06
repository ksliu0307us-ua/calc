# calc

A terminal calculator that understands units.

```
$ calc 5 km / 20 min to mph
9.320567884 mph

$ calc 1.5 GiB to MB
1610.612736 MB

$ calc "3 ft + 2 m"
9.56167979 ft

$ calc
> speed = 100 kph
100 kph
> speed * 2.5 h to mi
155.3427981 mi
> 80 kg * 9.81 m/s^2 * 10 m to kcal
1.875717017 kcal
```

I kept doing unit conversions in a browser tab and arithmetic in a Python
REPL, and neither would let me write `5 km / 20 min to mph`. This does.

## Who it's for

Me, daily. Anyone who does back-of-the-envelope maths with real-world
quantities: trips, recipes, download times, workouts, bills.

## Built with

- Python 3.9+, standard library only. The parser is a small hand-written
  Pratt parser; the unit system tracks dimensions so `2 m + 3 kg` is an
  error and `2 m * 3 ft` is `1.8288 m^2`.
- `pytest` for the tests.

## Install

```sh
git clone https://github.com/ksliu0307us-ua/calc.git
cd calc
pip install -e .
```

Or run it without installing: `python -m calc.cli ...`.

## Usage

```sh
calc "2 ^ 10"                      # one expression (quote it if it has * or parentheses)
calc 5 km to mi                    # words are joined, so no quotes needed here
calc                               # interactive; variables persist, `last` or `_` is the previous result
calc -f budget.txt                 # one expression per line, `#` comments, variables carry over
```

In the prompt, `units` lists every unit, `vars` lists your variables, `quit` leaves.

## What it understands

- `+ - * / ^` (also `**`), parentheses, unary minus, `%` as a postfix
  (`150 * 20%` is `30`).
- Numbers like `1_000_000`, `1e9`, `.5`.
- Functions: `sqrt abs round floor ceil sin cos tan asin acos atan ln log log2 exp`.
  Trig takes radians, or anything in `deg` (`sin(90 deg)`).
- Constants: `pi`, `e`, `tau`.
- Variables: `x = 3 m`, then `x * 2`. `last` and `_` are the previous result.
- Units, with implicit multiplication: `5 km`, `2 pi`, `3 (4+1)`.
- Conversion with `to`: `... to km`, `... to m/s`, `... to kg*m/s^2`.
- Units of the same kind fold together: `2 m * 3 ft` gives `m^2`;
  `3 ft + 2 m` answers in the left operand's unit.

Length, area, volume, mass, time, speed, data (both `MB` and `MiB`, and
bits), energy, power, and angles are built in. Plenty of spelled-out aliases
work (`miles`, `pounds`, `hours`). `units` in the prompt prints the list.

## One thing to know

Implicit multiplication binds tighter than `/`. That's what makes
`5 km / 20 min` mean (5 km) ÷ (20 min), but it also means `4/3 pi r^3` is
`4 ÷ (3·π·r³)`. Write `(4/3) pi r^3`. A smarter rule is on the roadmap.

## Running the tests

```sh
pip install pytest
pytest
```

## Roadmap

See [ROADMAP.md](ROADMAP.md). Issues and PRs welcome.

## License

MIT. See [LICENSE](LICENSE).
