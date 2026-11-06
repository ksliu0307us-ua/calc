# Roadmap

Roughly in order. Open an issue if you want one sooner.

## Soon

- [ ] Temperature (`C`, `F`, `K`) — needs offset conversions, not just scale factors
- [ ] Smarter implicit multiplication: `4/3 pi r^3` should mean (4/3)·π·r³ when the left side is a bare number
- [ ] `in` as a synonym for `to`, and `as` too (`5 km in miles`)
- [ ] Auto-pick a readable unit for results (`0.0005 km` → `0.5 m`, `90000 s` → `25 h`) with `--raw` to turn it off
- [ ] Number formatting options: `--precision 4`, thousands separators, scientific notation
- [ ] User-defined functions: `f(x) = x^2 + 1`

## Next

- [ ] Currency with a cached exchange-rate table the user can update (`calc --update-rates`)
- [ ] Date/time arithmetic: `now + 90 min`, `2026-12-25 - today to days`
- [ ] Config file for default units and custom unit definitions (`cup_jp = 200 mL`)
- [ ] Prefix handling (`k`, `M`, `G`, `m`, `µ`) applied to any base unit instead of listing each combination
- [ ] Prompt history and tab completion for units and variables (`readline` where available)
- [ ] Explain mode: `--explain` prints the conversion factors used

## Later / maybe

- [ ] Uncertainty: `10 ± 0.5 m` propagated through arithmetic
- [ ] Complex numbers
- [ ] A `--json` output for scripting
- [ ] Publish to PyPI

## Housekeeping

- [ ] Tests for the REPL commands (`units`, `vars`)
- [ ] GitHub Actions running `pytest` on Linux, macOS and Windows (unicode `·` in output)
- [ ] Type hints and a `mypy` pass
- [ ] CHANGELOG.md starting at 0.2.0
