"""The local web gallery (FastAPI + Jinja2 + HTMX).

Pages
  GET  /                    gallery grid; HTMX requests get only the results part
  GET  /d/{id}              detail page with live preview and code
  GET  /new, POST /new      add form
  GET  /d/{id}/edit, POST   edit form
  POST /d/{id}/favorite     toggle favorite (HTMX swaps the button)
  POST /d/{id}/delete       delete entry
  GET  /tags, /sources      overview pages
  GET  /api/meta?url=       metadata for the "Fetch details" button
"""

from pathlib import Path
from urllib.parse import urlencode

import markdown
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
from starlette.datastructures import UploadFile  # what request.form() returns for files

from designlib import config
from designlib.core import fetch, semantic
from designlib.core.index import delete_and_unindex, save_and_index
from designlib.core.schema import LINK_ONLY, OPEN_LICENSES, Entry, EntryType, Framework, new_id, now
from designlib.core.search import (
    SORTS,
    Filters,
    count_entries,
    category_counts,
    count_matches,
    get_entry,
    list_frameworks,
    list_sources,
    list_tags,
    list_types,
    platform_counts,
    search,
    uses_meaning,
)
from designlib.core.taxonomy import BY_SLUG, grouped
from designlib.web.preview import build_srcdoc, preview_kind

HERE = Path(__file__).parent
IMAGE_TYPES = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
MAX_UPLOAD_BYTES = 5 * 1024 * 1024
LICENSES = [LINK_ONLY, *sorted(OPEN_LICENSES)]
PAGE_SIZE = 60  # cards per "page"; "Show more" appends the next 60
PLATFORMS = [("", "All"), ("web", "Web"), ("mobile", "Mobile"), ("desktop", "Desktop"), ("any", "Any platform")]
PLATFORM_VALUES = {value for value, _ in PLATFORMS if value}


def sidebar_context(filters: Filters) -> dict:
    """Counts for the category sidebar and the platform tabs, for the current filters."""
    counts = category_counts(filters)
    selected = set(filters.categories or [])
    platforms = platform_counts(filters)
    return {
        "category_groups": grouped(),
        "category_counts": counts,
        # hide empty categories, but never the one you have selected
        "visible_categories": {slug for slug, n in counts.items() if n} | selected,
        "platforms": PLATFORMS,
        "platform_counts": platforms,
        "platform_total": sum(platforms.values()),
    }

templates = Jinja2Templates(directory=HERE / "templates")
templates.env.globals.update(
    preview_kind=preview_kind,
    build_srcdoc=build_srcdoc,
    types=[t.value for t in EntryType],
    frameworks=[f.value for f in Framework],
    licenses=LICENSES,
    sorts=SORTS,
    category_label=lambda slug: BY_SLUG[slug].label if slug in BY_SLUG else slug,
    category_groups_all=grouped(),
    platform_names=["web", "mobile", "desktop", "any"],
)


def create_app() -> FastAPI:
    app = FastAPI(title="Design Library", docs_url=None, redoc_url=None)
    semantic.warm_up()  # load the meaning model in the background, if installed
    app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")
    config.assets_dir().mkdir(parents=True, exist_ok=True)
    # local_image values look like "assets/mine/x.png", so serve the library's assets/ at /assets
    app.mount("/assets", StaticFiles(directory=config.assets_dir().parent), name="assets")

    @app.get("/healthz")
    def healthz():
        """Tiny, instant answer so `serve` can tell our gallery apart from other programs."""
        return {"app": "design-library"}

    # ---------- gallery ----------

    @app.get("/", response_class=HTMLResponse)
    def home(request: Request):
        params = request.query_params
        filters = Filters(
            query=params.get("q", ""),
            type=params.get("type") or None,
            framework=params.get("framework") or None,
            source=params.get("source") or None,
            platform=params.get("platform") if params.get("platform") in PLATFORM_VALUES else None,
            categories=[c for c in params.getlist("category") if c in BY_SLUG] or None,
            tags=params.getlist("tag"),
            favorites_only=params.get("fav") == "1",
            sort=params.get("sort", "relevance"),
            limit=PAGE_SIZE,
            offset=max(0, int(params.get("offset", "0") or 0)),
            wait_for_model=False,  # live search must stay instant; meaning kicks in once loaded
        )
        results = search(filters)
        matches = count_matches(filters)
        shown = filters.offset + len(results)
        # The "Show more" link: the same query string with the next offset.
        next_params = [(k, v) for k, v in params.multi_items() if k not in ("offset", "more")]
        context = {
            "results": results,
            "filters": filters,
            "total": count_entries(),
            "matches": matches,
            "shown": shown,
            "more_url": "/?" + urlencode([*next_params, ("offset", shown), ("more", "1")]) if shown < matches else None,
            "meaning": uses_meaning(filters),
            **sidebar_context(filters),
        }
        if params.get("more") == "1":  # "Show more": just the extra cards + a new button
            return templates.TemplateResponse(request, "_more.html", context)
        # HTMX sends HX-Request on live updates: answer with just the results.
        # On a history restore (back button, cache miss) it wants the full page.
        is_partial = request.headers.get("HX-Request") and not request.headers.get("HX-History-Restore-Request")
        if is_partial:  # results + refreshed sidebar/tab counts
            return templates.TemplateResponse(request, "_live.html", context)
        context.update(
            type_counts=list_types(),
            framework_counts=list_frameworks(),
            source_counts=list_sources(),
            tag_counts=list_tags()[:30],
        )
        return templates.TemplateResponse(request, "index.html", context)

    @app.get("/d/{entry_id}", response_class=HTMLResponse)
    def detail(request: Request, entry_id: str):
        entry = _get_or_404(entry_id)
        return templates.TemplateResponse(request, "detail.html", {"entry": entry})

    @app.post("/d/{entry_id}/favorite", response_class=HTMLResponse)
    def toggle_favorite(request: Request, entry_id: str):
        entry = _get_or_404(entry_id)
        entry.favorite = not entry.favorite
        save_and_index(entry)
        return templates.TemplateResponse(request, "_favorite.html", {"entry": entry})

    @app.post("/d/{entry_id}/delete")
    def delete(entry_id: str):
        _get_or_404(entry_id)
        delete_and_unindex(entry_id)
        return RedirectResponse("/", status_code=303)

    # ---------- add / edit ----------

    @app.get("/new", response_class=HTMLResponse)
    def new_form(request: Request):
        return _render_form(request, None, {})

    @app.post("/new", response_class=HTMLResponse)
    async def create(request: Request):
        return await _save_form(request, existing=None)

    @app.get("/d/{entry_id}/edit", response_class=HTMLResponse)
    def edit_form(request: Request, entry_id: str):
        entry = _get_or_404(entry_id)
        return _render_form(request, entry, entry.model_dump(mode="json"))

    @app.post("/d/{entry_id}/edit", response_class=HTMLResponse)
    async def update(request: Request, entry_id: str):
        return await _save_form(request, existing=_get_or_404(entry_id))

    @app.get("/api/meta")
    def page_meta(url: str):
        try:
            meta = fetch.fetch_metadata(url)
        except fetch.FetchError as error:
            return JSONResponse({"error": str(error)}, status_code=422)
        return {
            "title": meta.title,
            "description": meta.description,
            "image_url": meta.image_url,
            "source": meta.source,
        }

    # ---------- overview pages ----------

    @app.get("/tags", response_class=HTMLResponse)
    def tags_page(request: Request):
        return templates.TemplateResponse(request, "tags.html", {"tag_counts": list_tags()})

    @app.get("/sources", response_class=HTMLResponse)
    def sources_page(request: Request):
        sources_md = config.library_dir() / "sources.md"
        html = markdown.markdown(sources_md.read_text(encoding="utf-8"), extensions=["tables"]) if sources_md.exists() else ""
        return templates.TemplateResponse(
            request, "sources.html", {"sources_html": html, "source_counts": list_sources()}
        )

    return app


# ---------- helpers ----------


def _get_or_404(entry_id: str) -> Entry:
    entry = get_entry(entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="No entry with that id")
    return entry


def _render_form(request: Request, entry: Entry | None, values: dict, error: str = "", status: int = 200):
    return templates.TemplateResponse(
        request, "form.html", {"entry": entry, "v": values, "error": error}, status_code=status
    )


def _form_to_values(form) -> dict:
    """Turn the submitted HTML form into a dict shaped like an Entry."""

    def text(name: str) -> str:
        return (form.get(name) or "").strip()

    return {
        "title": text("title"),
        "url": text("url"),
        "source": text("source"),
        "license": text("license") or LINK_ONLY,
        "type": text("type"),
        "framework": text("framework") or "none",
        "platform": text("platform") or "any",
        "categories": [c for c in form.getlist("categories") if c],
        "tags": [t for t in text("tags").split(",")],
        "notes": text("notes"),
        "style_notes": {
            "palette": text("palette"),
            "fonts": text("fonts"),
            "spacing": text("spacing"),
            "mood": text("mood"),
        },
        "code": form.get("code") or None,  # keep code whitespace exactly as typed
        "prompt": text("prompt") or None,
        "preview_image_url": text("preview_image_url") or None,
        "when_to_use": text("when_to_use"),
        "avoid_when": text("avoid_when"),
        "my_rating": int(text("my_rating") or 3),
        "favorite": form.get("favorite") == "on",
    }


async def _save_upload(upload: UploadFile, entry_id: str) -> str:
    """Save your own screenshot under library/assets/mine/. Returns the relative path."""
    suffix = Path(upload.filename or "").suffix.lower()
    if suffix not in IMAGE_TYPES:
        raise ValueError(f"screenshot must be one of {sorted(IMAGE_TYPES)}")
    data = await upload.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise ValueError("screenshot is larger than 5 MB")
    filename = f"{entry_id}{suffix}"
    (config.assets_dir() / filename).write_bytes(data)
    return f"assets/mine/{filename}"


async def _save_form(request: Request, existing: Entry | None):
    form = await request.form()
    values = _form_to_values(form)
    entry_id = existing.id if existing else new_id(values["title"] or "entry", salt=values["url"])
    try:
        values["local_image"] = existing.local_image if existing else None
        upload = form.get("screenshot")
        if isinstance(upload, UploadFile) and upload.filename:
            values["local_image"] = await _save_upload(upload, entry_id)
        if form.get("remove_image") == "on":
            values["local_image"] = None
        # Categories count as "set by you" once you pick them (or change the automatic
        # choice); then re-categorizing never overwrites them.
        auto = (existing.platform.value, existing.categories) if existing else ("any", [])
        chosen = (values["platform"], values["categories"])
        values["categories_manual"] = bool(values["categories"]) and (
            (existing is not None and existing.categories_manual) or chosen != auto
        )
        entry = Entry(
            id=entry_id,
            added_at=existing.added_at if existing else now(),
            **values,
        )
    except (ValidationError, ValueError) as error:
        return _render_form(request, existing, values, error=_friendly(error), status=422)
    save_and_index(entry)
    return RedirectResponse(f"/d/{entry.id}", status_code=303)


def _friendly(error: Exception) -> str:
    if isinstance(error, ValidationError):
        return "; ".join(
            f"{'.'.join(str(p) for p in e['loc']) or 'entry'}: {e['msg'].removeprefix('Value error, ')}"
            for e in error.errors()
        )
    return str(error)

