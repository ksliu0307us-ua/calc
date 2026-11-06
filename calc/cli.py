import argparse
import sys

from . import parser, units
from .units import fmt_quantity


def repl(variables):
    print("calc — type an expression, 'units' to list units, 'vars' for variables, 'quit' to leave")
    while True:
        try:
            line = input("> ")
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        s = line.strip()
        if not s:
            continue
        if s in ("quit", "exit", "q"):
            return 0
        if s == "units":
            print(" ".join(sorted(units.UNITS)))
            continue
        if s == "vars":
            for k, v in variables.items():
                if k not in ("last", "_"):
                    print(f"{k} = {fmt_quantity(v)}")
            continue
        try:
            print(fmt_quantity(parser.evaluate(s, variables)))
        except parser.CalcError as e:
            print(f"error: {e}")


def build_parser():
    p = argparse.ArgumentParser(prog="calc", description="a calculator that understands units")
    p.add_argument("expr", nargs="*", help="expression to evaluate; omit for an interactive prompt")
    p.add_argument("-f", "--file", help="evaluate each line of a file (variables carry over)")
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    variables = {}

    if args.file:
        try:
            lines = open(args.file, encoding="utf-8").read().splitlines()
        except OSError as e:
            print(f"error: {e}", file=sys.stderr)
            return 1
        status = 0
        for n, line in enumerate(lines, 1):
            s = line.split("#", 1)[0].strip()
            if not s:
                continue
            try:
                print(f"{s} = {fmt_quantity(parser.evaluate(s, variables))}")
            except parser.CalcError as e:
                print(f"line {n}: error: {e}", file=sys.stderr)
                status = 1
        return status

    if args.expr:
        try:
            print(fmt_quantity(parser.evaluate(" ".join(args.expr), variables)))
            return 0
        except parser.CalcError as e:
            print(f"error: {e}", file=sys.stderr)
            return 1

    return repl(variables)


if __name__ == "__main__":
    sys.exit(main())
