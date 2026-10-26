"""Command line interface: `python -m designlib <command>`."""

import argparse

from designlib.core.index import rebuild_index


def cmd_rebuild(args: argparse.Namespace) -> None:
    count = rebuild_index()
    print(f"Indexed {count} entries.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="designlib", description="Your local design library.")
    commands = parser.add_subparsers(dest="command", required=True)

    rebuild = commands.add_parser("rebuild", help="rebuild index.db from the JSON entries")
    rebuild.set_defaults(func=cmd_rebuild)

    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    args.func(args)
