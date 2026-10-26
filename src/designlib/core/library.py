"""High-level actions shared by the CLI, the web gallery and the MCP server."""

from designlib.core.fetch import PageMeta, fetch_metadata, source_name
from designlib.core.index import save_and_index
from designlib.core.schema import LINK_ONLY, Entry, new_id


def add_from_url(
    url: str,
    type: str,
    tags: list[str] | None = None,
    notes: str = "",
    title: str | None = None,
    fetch: bool = True,
    **fields,
) -> Entry:
    """Create a link-only entry for a page, save it as JSON and index it.

    With fetch=True we read the page's title, description and og:image URL.
    Any extra keyword (framework, my_rating, when_to_use, ...) goes straight
    into the Entry, so callers can fill in more than the basics.
    """
    meta = fetch_metadata(url) if fetch else PageMeta(url=url, source=source_name(url))

    final_title = title or meta.title or meta.source or url
    entry = Entry(
        id=new_id(final_title, salt=url),
        title=final_title,
        source=meta.source,
        url=url,
        license=LINK_ONLY,
        type=type,
        tags=tags or [],
        notes=notes or meta.description,
        preview_image_url=meta.image_url,
        **fields,
    )
    return save_and_index(entry)
