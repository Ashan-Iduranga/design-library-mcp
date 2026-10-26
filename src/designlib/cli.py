"""Command line interface: `python -m designlib <command>`.

Commands:
  add <url>     fetch page metadata and save a link-only entry
  list          show entries (newest first)
  search <q>    full-text search with optional filters
  rebuild       rebuild index.db from the JSON entries
  serve         start the web gallery on http://127.0.0.1:8000
  import <name> import open-license components (hyperui, uiverse)
  mcp           run the MCP server over stdio (Claude starts this for you)
"""

import argparse
import sys

from designlib import config
from designlib.core.fetch import FetchError
from designlib.core.index import rebuild_index
from designlib.core.library import add_from_url
from designlib.core.schema import Entry, EntryType, Framework
from designlib.core.search import Filters, search

TYPES = [t.value for t in EntryType]
FRAMEWORKS = [f.value for f in Framework]


def split_tags(text: str | None) -> list[str]:
    """'hero, dark ,saas' -> ['hero', 'dark', 'saas']"""
    return [tag.strip() for tag in (text or "").split(",") if tag.strip()]


def print_entries(entries: list[Entry]) -> None:
    if not entries:
        print("No entries found.")
        return
    for entry in entries:
        stars = "*" * entry.my_rating
        fav = " (fav)" if entry.favorite else ""
        tags = ", ".join(entry.tags)
        print(f"{entry.id:<45} {entry.type.value:<11} {stars:<5} {entry.title}{fav}")
        if tags:
            print(f"{'':<45} {'':<11} {'':<5} tags: {tags}")
    print(f"\n{len(entries)} result(s)")


def cmd_add(args: argparse.Namespace) -> None:
    try:
        entry = add_from_url(
            args.url,
            type=args.type,
            tags=split_tags(args.tags),
            notes=args.notes or "",
            title=args.title,
            fetch=not args.no_fetch,
            framework=args.framework,
            my_rating=args.rating,
            favorite=args.favorite,
        )
    except FetchError as error:
        sys.exit(f"Could not add: {error}\nTip: use --no-fetch --title '...' to add it without fetching.")
    print(f"Added {entry.id}")
    print(f"  title:  {entry.title}")
    print(f"  source: {entry.source}")
    print(f"  image:  {entry.preview_image_url or '(none)'}")
    print(f"  file:   library/entries/{entry.id}.json")
    print(f"  view:   {config.gallery_url(entry.id)}")


def cmd_list(args: argparse.Namespace) -> None:
    print_entries(search(Filters(type=args.type, sort="newest", limit=args.limit)))


def cmd_search(args: argparse.Namespace) -> None:
    filters = Filters(
        query=" ".join(args.query),
        type=args.type,
        tags=split_tags(args.tags),
        framework=args.framework,
        limit=args.limit,
        mode="keyword" if args.keyword else "hybrid",
    )
    print_entries(search(filters))


def cmd_rebuild(args: argparse.Namespace) -> None:
    from designlib.core import semantic

    count = rebuild_index()
    print(f"Indexed {count} entries.")
    if semantic.enabled():
        print(f"Semantic search: embedded {semantic.sync()} new or changed entries.")


def cmd_serve(args: argparse.Namespace) -> None:
    import uvicorn  # imported here so other commands start fast

    url = f"http://{config.HOST}:{args.port}"
    print(f"Design Library running at {url}  (Ctrl+C to stop)")
    if args.open:
        import threading
        import webbrowser

        threading.Timer(1.5, webbrowser.open, args=[url]).start()  # give the server a moment to start
    uvicorn.run(
        "designlib.web.app:create_app",
        factory=True,
        host=config.HOST,  # 127.0.0.1 only: not reachable from other machines
        port=args.port,
        reload=args.reload,
        log_level="warning",
    )


def cmd_import(args: argparse.Namespace) -> None:
    from designlib.importers import hyperui, uiverse
    from designlib.importers.common import ImportStopped

    try:
        if args.name == "hyperui":
            created, updated = hyperui.run(limit=args.limit, include_dark=args.dark, refresh=args.refresh)
        else:
            created, updated = uiverse.run(limit=args.limit, categories=split_tags(args.category), refresh=args.refresh)
    except ImportStopped as error:
        sys.exit(f"Import stopped: {error}")
    print(f"Imported from {args.name}: {created} new, {updated} updated (your ratings and notes were kept).")


def cmd_mcp(args: argparse.Namespace) -> None:
    from designlib.mcp_server import main as run_server

    run_server()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="designlib", description="Your local design library.")
    commands = parser.add_subparsers(dest="command", required=True)

    add = commands.add_parser("add", help="save a page as a link-only reference")
    add.add_argument("url")
    add.add_argument("--type", required=True, choices=TYPES)
    add.add_argument("--tags", help="comma separated, e.g. 'hero,dark,saas'")
    add.add_argument("--notes", help="your notes (defaults to the page description)")
    add.add_argument("--title", help="override the fetched title")
    add.add_argument("--framework", default="none", choices=FRAMEWORKS)
    add.add_argument("--rating", type=int, default=3, choices=range(1, 6))
    add.add_argument("--favorite", action="store_true")
    add.add_argument("--no-fetch", action="store_true", help="don't contact the site")
    add.set_defaults(func=cmd_add)

    list_ = commands.add_parser("list", help="list entries, newest first")
    list_.add_argument("--type", choices=TYPES)
    list_.add_argument("--limit", type=int, default=50)
    list_.set_defaults(func=cmd_list)

    find = commands.add_parser("search", help="full-text search")
    find.add_argument("query", nargs="*", help="words to search for")
    find.add_argument("--type", choices=TYPES)
    find.add_argument("--tags", help="comma separated; all must match")
    find.add_argument("--framework", choices=FRAMEWORKS)
    find.add_argument("--limit", type=int, default=20)
    find.add_argument("--keyword", action="store_true", help="exact words only (skip meaning search)")
    find.set_defaults(func=cmd_search)

    rebuild = commands.add_parser("rebuild", help="rebuild index.db from the JSON entries")
    rebuild.set_defaults(func=cmd_rebuild)

    serve = commands.add_parser("serve", help="start the web gallery (local only)")
    serve.add_argument("--port", type=int, default=config.PORT)
    serve.add_argument("--reload", action="store_true", help="restart when code changes (development)")
    serve.add_argument("--open", action="store_true", help="open the gallery in your browser")
    serve.set_defaults(func=cmd_serve)

    imp = commands.add_parser("import", help="import open-license components")
    imp.add_argument("name", choices=["hyperui", "uiverse"])
    imp.add_argument("--limit", type=int, default=60, help="max entries, spread across categories (0 = all)")
    imp.add_argument("--dark", action="store_true", help="hyperui: also import dark variants")
    imp.add_argument("--category", help="uiverse: only these folders, e.g. 'buttons,cards'")
    imp.add_argument("--refresh", action="store_true", help="download the repo again")
    imp.set_defaults(func=cmd_import)

    mcp = commands.add_parser("mcp", help="run the MCP server over stdio")
    mcp.set_defaults(func=cmd_mcp)

    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    args.func(args)
