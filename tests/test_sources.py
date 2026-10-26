"""Tests for the library and gallery importers added for "import everything", using
small fake inputs (no downloads), plus paging and per-library preview assets."""

import base64
import io
import json
import zipfile

import httpx
import pytest
from fastapi.testclient import TestClient

from conftest import make_entry
from designlib.core.fetch import PageMeta
from designlib.core.index import save_and_index
from designlib.core.search import Filters, count_matches, search
from designlib.importers import collectui, daisyui, flowbite, galleries, icons, shadcn, tokens
from designlib.web.app import create_app
from designlib.web.preview import build_srcdoc


def make_zip(files: dict[str, str]) -> tuple[zipfile.ZipFile, str]:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, text in files.items():
            archive.writestr(name, text)
    buffer.seek(0)
    return zipfile.ZipFile(buffer), "repo-main/"


# ---------- paging ----------


@pytest.fixture
def seventy():
    for i in range(70):
        save_and_index(make_entry(id=f"card-{i:03d}", title=f"Card {i:03d}"))


def test_search_offset_and_count(seventy):
    page2 = search(Filters(sort="title", limit=60, offset=60))
    assert [e.id for e in page2] == [f"card-{i:03d}" for i in range(60, 70)]
    assert count_matches(Filters()) == 70
    assert count_matches(Filters(query="card 005")) >= 1


def test_gallery_show_more(seventy):
    client = TestClient(create_app())
    page = client.get("/?sort=title").text
    assert page.count('class="card ') == 60
    assert "offset=60" in page and "more=1" in page and "70 references" in page

    more = client.get("/?sort=title&offset=60&more=1", headers={"HX-Request": "true"}).text
    assert more.count('class="card ') == 10
    assert 'hx-swap-oob="true"' in more and "All 70 shown" in more
    assert "<html" not in more


# ---------- shadcn/ui ----------

SHADCN_REGISTRY = '''export const blocks = [
  {
    name: "login-01",
    description: "A simple login form.",
    type: "registry:block",
    files: [
      {
        path: "blocks/login-01/page.tsx",
        type: "registry:page",
      },
    ],
    categories: ["authentication", "login"],
  },
  {
    name: "sidebar-01",
    type: "registry:block",
    description: "A simple sidebar.",
    files: [
      { path: "blocks/sidebar-01/page.tsx", type: "registry:page" },
      { path: "blocks/sidebar-01/nav.tsx", type: "registry:component" },
    ],
  },
]'''


def test_shadcn_registry_parsing_ignores_field_order():
    items = shadcn.parse_registry(SHADCN_REGISTRY)
    assert [i["name"] for i in items] == ["login-01", "sidebar-01"]
    assert items[1]["description"] == "A simple sidebar."  # description after type
    assert items[0]["categories"] == ["authentication", "login"]


def test_shadcn_entry_has_install_command_and_all_files():
    archive, prefix = make_zip({
        f"repo-main/{shadcn.REGISTRY}blocks/sidebar-01/page.tsx": "export default function Page() {}",
        f"repo-main/{shadcn.REGISTRY}blocks/sidebar-01/nav.tsx": "export function Nav() {}",
    })
    entry = shadcn.build_entry(archive, prefix, "blocks", shadcn.parse_registry(SHADCN_REGISTRY)[1])
    assert entry.prompt == "npx shadcn@latest add sidebar-01"
    assert "// File: blocks/sidebar-01/nav.tsx" in entry.code
    assert entry.framework.value == "react" and entry.license == "MIT"


# ---------- Flowbite / daisyUI ----------

FLOWBITE_PAGE = """---
title: Tailwind CSS Buttons - Flowbite
description: Buttons for actions
---

## Default button

Use these default button styles.

{{< example github="components/buttons.md" >}}
<button class="bg-brand">Default</button>
{{< /example >}}

## Default button

{{< example >}}
<button class="bg-brand">Again</button>
{{< /example >}}

## Templated

{{< example >}}
<button>{{< icon >}}</button>
{{< /example >}}
"""


def test_flowbite_examples_unique_ids_and_skips_templates():
    entries = flowbite.page_entries("components", "buttons", FLOWBITE_PAGE)
    assert [e.title for e in entries] == ["Buttons: Default button (Flowbite)", "Buttons: Default button (Flowbite)"]
    assert len({e.id for e in entries}) == 2  # a repeated heading doesn't overwrite
    assert entries[0].notes.startswith("Use these default button styles.")
    assert entries[0].url.endswith("/docs/components/buttons/#default-button")


DAISY_PAGE = """---
title: Button
desc: Buttons allow the user to take actions
---

### ~Button
<button class="btn">Default</button>

```html
<button class="$$btn">Default</button>
```

### ~Sizes
```html
<button class="$$btn $$btn-xs">Xsmall</button>
```
"""


def test_daisyui_examples_strip_prefix_marker():
    entries = daisyui.page_entries("button", DAISY_PAGE)
    assert [e.title for e in entries] == ["Button: Button (daisyUI)", "Button: Sizes (daisyUI)"]
    assert entries[1].code == '<button class="btn btn-xs">Xsmall</button>'


def test_previews_load_library_assets():
    daisy = make_entry(source="daisyUI", license="MIT", framework="tailwind", code="<button class='btn'>x</button>")
    assert "daisyui/daisyui.css" in build_srcdoc(daisy)
    flow = make_entry(source="Flowbite", license="MIT", framework="tailwind", code="<button>x</button>")
    doc = build_srcdoc(flow)
    assert '<style type="text/tailwindcss">@theme' in doc and "flowbite.min.js" in doc


# ---------- tokens and icons ----------


def test_radix_light_and_dark_keep_their_own_colors():
    archive, prefix = make_zip({
        "repo-main/src/light.ts": 'export const gray = {\n  gray1: "#fcfcfc",\n  gray2: "#f9f9f9",\n};\n',
        "repo-main/src/dark.ts": 'export const grayDark = {\n  grayDark1: "#111111",\n  grayDark2: "#191919",\n};\n',
    })
    [entry] = tokens.radix_entries(archive, prefix)
    assert ":root {\n  --gray-1: #fcfcfc;" in entry.code
    assert ".dark {\n  --gray-1: #111111;" in entry.code
    assert 'style="background:#111111"' in entry.code  # dark chip shows the dark color


def test_lucide_groups_list_every_icon_name():
    svg = '<svg viewBox="0 0 24 24"><path d="M1 1"/></svg>'
    archive, prefix = make_zip({
        "repo-main/categories/arrows.json": json.dumps({"title": "Arrows", "description": "Arrow icons."}),
        "repo-main/icons/arrow-up.json": json.dumps({"tags": ["up"], "categories": ["arrows"]}),
        "repo-main/icons/arrow-up.svg": svg,
        "repo-main/icons/arrow-down.json": json.dumps({"tags": ["down"], "categories": ["arrows"]}),
        "repo-main/icons/arrow-down.svg": svg,
    })
    [entry] = icons.lucide_entries(archive, prefix)
    assert entry.title == "Lucide icons: Arrows (2)"
    assert "arrow-down, arrow-up" in entry.notes and "import { ArrowDown }" in entry.notes
    assert entry.code.count("<figure>") == 2 and entry.license == "ISC"


# ---------- galleries ----------


def test_saas_landing_page_reads_only_the_pages_own_tags():
    html = (
        '<a href="https://saaslandingpage.com/tag/fintech/">Fintech</a>'  # site navigation: ignored
        '<a href="https://saaslandingpage.com/font/inter/" rel="tag">Inter</a>'
        '<a href="https://saaslandingpage.com/technology/framer/" rel="tag">Framer</a>'
    )
    page = galleries.Page(url="https://saaslandingpage.com/acme/", html=html,
                          meta=PageMeta(url="", title="Acme page - SaaS Landing Page"))
    fields = galleries.slp_build(page)
    assert fields["title"] == "Acme landing page"
    assert "framer" in fields["tags"] and "fintech" not in fields["tags"]
    assert fields["style_notes"] == {"fonts": "Inter"}


def test_gallery_url_filters():
    assert galleries.slp_wanted("https://saaslandingpage.com/acme/")
    assert not galleries.slp_wanted("https://saaslandingpage.com/templates/lemon/")  # paid templates
    assert galleries.dp_wanted("https://designprompts.dev/components/botanical/button")
    assert not galleries.dp_wanted("https://designprompts.dev/components/catalogue/botanical")


# ---------- Collect UI ----------


def fake_jwt(claims: dict) -> str:
    encode = lambda data: base64.urlsafe_b64encode(json.dumps(data).encode()).decode().rstrip("=")
    return f"{encode({'alg': 'HS256'})}.{encode(claims)}.signature"


def test_collectui_finds_public_key_in_site_javascript(monkeypatch):
    monkeypatch.setattr(collectui, "MIN_DELAY_SECONDS", 0)
    key = fake_jwt({"role": "anon", "ref": "abc123"})

    def handler(request):
        if request.url.path == "/":
            return httpx.Response(200, text='import("./_app/immutable/entry/start.js")')
        if request.url.path.endswith("start.js"):
            return httpx.Response(200, text='import("../chunks/data.js")')
        if request.url.path.endswith("data.js"):
            return httpx.Response(200, text=f'const k="{fake_jwt({"role": "service_role"})}";const a="{key}";')
        return httpx.Response(404)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    assert collectui.find_backend(client) == ("https://abc123.supabase.co", key)  # anon only, never service_role


def test_collectui_entry_is_link_only_with_credit():
    post = {
        "id": "99f5324e-acef", "title": "cool  sliders", "source_url": "https://x.com/a/status/1",
        "media_type": "video", "thumbnail": "https://cdn.collectui.com/t.jpg", "media_url": "https://cdn/v.mp4",
        "categories": ["range-slider", "2"], "designer_username": "zzzzshawn",
    }
    entry = collectui.make_entry(post, {"range-slider": "Range Slider"})
    assert entry.title == "Range Slider by @zzzzshawn: cool sliders"
    assert entry.license == "link-only" and entry.code is None
    assert entry.url == "https://x.com/a/status/1"  # credit goes to the designer's original post
    assert entry.preview_image_url == "https://cdn.collectui.com/t.jpg"  # thumbnail, not the video
    assert entry.type.value == "interaction" and "2" not in entry.tags


def test_gallery_import_stops_cleanly_when_offline(monkeypatch):
    from designlib.core.fetch import FetchError
    from designlib.importers.common import ImportStopped

    monkeypatch.setattr(galleries, "sitemap_urls", lambda sitemap: [f"https://designprompts.dev/components/s{i}" for i in range(30)])

    def offline(url, client=None):
        raise FetchError("getaddrinfo failed")

    monkeypatch.setattr(galleries.fetch, "fetch_page", offline)
    with pytest.raises(ImportStopped, match="Run the same command again to resume"):
        galleries.run("designprompts")


def test_sitemap_download_failure_is_a_clear_message(monkeypatch):
    from designlib.importers.common import ImportStopped

    def no_network(*args, **kwargs):
        raise httpx.ConnectError("getaddrinfo failed")

    monkeypatch.setattr(galleries.httpx, "get", no_network)
    with pytest.raises(ImportStopped, match="Check your connection"):
        galleries.sitemap_urls("https://designprompts.dev/sitemap.xml")
