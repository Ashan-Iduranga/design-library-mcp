// Small enhancements on top of the server-rendered pages. Everything still
// works without JavaScript except live search, copying and the width toggle.

// "/" jumps to the search box (unless you're already typing somewhere).
document.addEventListener("keydown", (event) => {
  const typing = event.target.closest("input, textarea, select, [contenteditable]");
  if (event.key === "/" && !typing && !event.ctrlKey && !event.metaKey) {
    const search = document.getElementById("q");
    if (search) {
      event.preventDefault();
      search.focus();
      search.select();
    }
  }
});

// Theme toggle: system -> the opposite of system -> back. Remembered per browser.
document.getElementById("theme-toggle")?.addEventListener("click", () => {
  const root = document.documentElement;
  const systemDark = matchMedia("(prefers-color-scheme: dark)").matches;
  const current = root.dataset.theme || (systemDark ? "dark" : "light");
  const next = current === "dark" ? "light" : "dark";
  root.dataset.theme = next;
  try { localStorage.setItem("theme", next); } catch (e) { /* private mode: not remembered */ }
});

// Copy buttons: <button data-copy="#code">
document.addEventListener("click", async (event) => {
  const button = event.target.closest("[data-copy]");
  if (!button) return;
  const source = document.querySelector(button.dataset.copy);
  const label = button.textContent;
  try {
    await navigator.clipboard.writeText(source.textContent);
    button.textContent = "Copied";
  } catch (e) {
    button.textContent = "Copy failed";
  }
  setTimeout(() => (button.textContent = label), 1600);
});

// Detail page: desktop / tablet / mobile preview widths.
const frame = document.getElementById("stage-frame");
if (frame) {
  const widthLabel = document.getElementById("stage-width");
  const showWidth = () => (widthLabel.textContent = `${Math.round(frame.getBoundingClientRect().width)} px wide`);
  document.querySelectorAll(".seg[data-width]").forEach((button) => {
    button.addEventListener("click", () => {
      document.querySelectorAll(".seg[data-width]").forEach((b) => b.setAttribute("aria-pressed", "false"));
      button.setAttribute("aria-pressed", "true");
      frame.style.width = button.dataset.width;
      setTimeout(showWidth, 260);
    });
  });
  showWidth();
  addEventListener("resize", showWidth);
}

// Syntax highlighting (highlight.js is only loaded on the detail page).
addEventListener("DOMContentLoaded", () => {
  if (window.hljs) document.querySelectorAll("pre code:not(.nohighlight)").forEach((el) => hljs.highlightElement(el));
});

// Add/edit form: "Fetch details" fills empty fields from the page's metadata.
document.getElementById("fetch-meta")?.addEventListener("click", async () => {
  const url = document.getElementById("url").value.trim();
  const status = document.getElementById("fetch-status");
  if (!url) {
    status.textContent = "Enter a page URL first.";
    status.className = "help is-error";
    return;
  }
  status.textContent = "Fetching title and description...";
  status.className = "help";
  try {
    const response = await fetch(`/api/meta?url=${encodeURIComponent(url)}`);
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "request failed");
    const fill = (id, value) => {
      const field = document.getElementById(id);
      if (field && !field.value && value) field.value = value;
    };
    fill("title", data.title);
    fill("source", data.source);
    fill("notes", data.description);
    fill("preview_image_url", data.image_url);
    status.textContent = "Filled in the empty fields. Check them before saving.";
    status.className = "help is-ok";
  } catch (error) {
    status.textContent = `Could not fetch details: ${error.message}`;
    status.className = "help is-error";
  }
});

// Phones: the category sidebar opens as a drawer, and closes again once you pick one.
document.addEventListener("click", (event) => {
  const toggle = event.target.closest(".drawer-toggle");
  if (!toggle) return;
  const open = document.querySelector(".browse").classList.toggle("drawer-open");
  toggle.setAttribute("aria-expanded", String(open));
});
document.addEventListener("change", (event) => {
  if (event.target.name !== "category" || !matchMedia("(max-width: 900px)").matches) return;
  document.querySelector(".browse")?.classList.remove("drawer-open");
  document.querySelector(".drawer-toggle")?.setAttribute("aria-expanded", "false");
});
