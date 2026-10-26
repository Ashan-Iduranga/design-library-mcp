"""The library's own categories: what a reference *is* (hero, navbar, button, ...).

Edit this table to change how the library is organised, then run
`python -m designlib categorize --force` to re-sort every entry.

Each category has:
  slug      stable id stored in entries ("hero")
  label     what the gallery shows ("Hero")
  group     the sidebar section it belongs to
  keywords  tags / title words that mean "this is one of these". Words are compared
            after simple normalisation (lowercase, plural "s" removed), and also match
            inside hyphenated tags: "hero" matches the tag "hero-section".
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Category:
    slug: str
    label: str
    group: str
    keywords: tuple[str, ...] = field(default=())


GROUPS = ("Pages & sections", "App screens", "Components", "Motion & effects", "Style & brand", "Other")

_P, _A, _C, _M, _S = GROUPS[:5]

CATEGORIES: tuple[Category, ...] = (
    # ---------- Pages & sections (mostly websites) ----------
    Category("landing-page", "Landing / home page", _P, ("landing-page", "landing", "homepage", "home-page", "website", "ai-sites", "agency", "landing-section", "saas-site", "webflow", "framer")),
    Category("hero", "Hero", _P, ("hero", "hero-section", "header-section", "banner", "banners", "announcement", "announcements", "above-the-fold", "jumbotron")),
    Category("navigation", "Navigation", _P, ("navigation", "navbar", "nav", "header", "headers", "header-navigation", "sidebar", "side-menu", "vertical-menu", "breadcrumb", "breadcrumbs", "mobile-menu", "dock", "command-bar", "command", "bottom-navigation", "menubar", "navigation-menu", "tabbar", "tab-bar", "toolbar", "toolbar-tabbar", "navigation-bar", "navigation-drawer", "navigation-rail", "app-bar", "appbar", "top-app-bar", "bottom-app-bar", "panel", "view", "subnavbar", "subnavbar-title")),
    Category("footer", "Footer", _P, ("footer", "footers")),
    Category("cta", "Call to action", _P, ("cta", "ctas", "call-to-action", "closing", "closing-banner", "closing-card", "download-app", "download")),
    Category("features", "Features", _P, ("features", "feature", "benefits", "benefits-columns", "bento", "bento-feature", "bento-style", "how-it-works")),
    Category("pricing", "Pricing", _P, ("pricing", "price", "plans", "plan", "pricing-table", "subscription", "comparison", "comparison-split")),
    Category("testimonials", "Testimonials & reviews", _P, ("testimonial", "testimonials", "reviews", "review", "quote", "social-proof", "tweet")),
    Category("faq", "FAQ", _P, ("faq", "faqs", "questions")),
    Category("blog", "Blog & articles", _P, ("blog", "blog-cards", "blog-index", "blog-index-feature", "article", "post", "posts", "newsfeed", "activity-feed")),
    Category("about", "About", _P, ("about", "about-us", "about-pull", "team-sections", "bio", "bio-card", "press-page", "story")),
    Category("contact", "Contact", _P, ("contact", "contact-us", "contact-forms", "contact-channels", "contact-list")),
    Category("logo-cloud", "Logo cloud", _P, ("logo-cloud", "logo-clouds", "partners", "clients", "marquee")),
    Category("stats", "Stats & numbers", _P, ("stats", "stat", "statistics", "metrics", "numbers", "kpi", "countdown")),
    Category("newsletter", "Newsletter & subscribe", _P, ("newsletter", "newsletter-signup", "subscribe", "waitlist", "invite")),
    Category("error-page", "404 & error pages", _P, ("404", "404-page", "error-page", "error-state", "not-found", "maintenance")),
    Category("coming-soon", "Coming soon", _P, ("coming-soon", "pre-order", "launch", "giveaway")),
    Category("portfolio", "Portfolio", _P, ("portfolio", "showcase", "case-study", "resume")),
    Category("gallery", "Gallery & media grid", _P, ("gallery", "image-gallery", "images", "image-grid", "masonry", "album-cover", "photo", "diff", "image-compare")),
    # ---------- App screens ----------
    Category("dashboard", "Dashboard", _A, ("dashboard", "admin-panel", "admin", "analytics", "overview", "widget", "widgets")),
    Category("auth", "Login & sign up", _A, ("login", "log-in", "signin", "sign-in", "sign-up", "signup", "register", "auth", "auth-split", "authentication", "otp", "otp-code", "verification-code", "password", "forgot-password", "captcha")),
    Category("onboarding", "Onboarding", _A, ("onboarding", "welcome-screen", "welcome", "walkthrough", "product-tour", "splash-screen", "select-user-type", "get-started")),
    Category("settings", "Settings", _A, ("settings", "settings-page", "preferences", "account-settings", "theme-controller", "theme-toggler")),
    Category("profile", "Profile & account", _A, ("profile", "user-profile", "account", "user")),
    Category("checkout", "Checkout & cart", _A, ("checkout", "cart", "carts", "shopping-cart", "payment", "invoice", "email-receipt", "redeem-coupon", "e-wallet", "wallet", "order")),
    Category("ecommerce", "E-commerce & products", _A, ("ecommerce", "e-commerce", "product", "products", "product-cards", "product-collections", "single-product", "shop", "store", "filter-products", "in-stock", "quantity-inputs")),
    Category("chat", "Chat & messaging", _A, ("chat", "chat-layout", "messaging", "direct-messaging", "messages", "chatbot", "bot-interface", "ai-chat", "comments", "comment")),
    Category("inbox", "Inbox & email", _A, ("inbox", "email", "email-application", "email-design", "mail")),
    Category("calendar", "Calendar & schedule", _A, ("calendar", "schedule", "date-picker", "datepicker", "event-listing", "events", "booking", "hotel-booking", "reminder-alarm", "time")),
    Category("data-table", "Tables & lists", _A, ("table", "tables", "data-table", "data", "list-items", "details-list", "leaderboard", "grid-list", "file-tree", "list")),
    Category("charts", "Charts & data viz", _A, ("chart", "charts", "graph", "data-visualization", "analytics-chart", "radar", "pie", "area", "bar-chart", "line-chart", "infographic")),
    Category("empty-state", "Empty states", _A, ("empty-state", "empty-states", "empty", "placeholder", "skeleton", "no-results")),
    Category("notifications", "Notifications & activity", _A, ("notification", "notifications", "flash-messages", "status-update", "activity", "pending-invitation")),
    Category("search", "Search & filters", _A, ("search", "search-bar", "searchbar", "searchbar-expandable", "filter", "filters", "command-palette", "flight-search")),
    Category("file-upload", "File upload", _A, ("file-upload", "file-input", "file-uploaders", "upload", "dropzone", "folder")),
    Category("productivity", "Productivity & tasks", _A, ("todo-list", "todo", "kanban", "project-management", "task", "tasks", "notepad", "notes-widget", "text-editor", "code-editor", "documentation", "notes", "calculator", "creative-tools")),
    Category("media", "Music & video", _A, ("music-player", "video-player", "player", "music", "video", "podcast", "tv-app", "movie-card", "audio")),
    Category("maps-travel", "Maps & travel", _A, ("map", "maps", "location-tracker", "travel-destination", "itinerary", "travel", "weather", "real-estate")),
    Category("ai-interface", "AI interfaces", _A, ("ai", "ai-agents", "ai-flow", "claude", "prompt-input", "agent")),
    # ---------- Components ----------
    Category("button", "Buttons", _C, ("button", "buttons", "button-group", "button-groups", "hover-button", "switch-button", "fab", "speed-dial", "icon-button", "cta-button", "chip", "segmented-button")),
    Category("card", "Cards", _C, ("card", "cards", "info-card", "card-hover", "stack")),
    Category("form", "Forms & inputs", _C, ("form", "forms", "input", "inputs", "input-field", "text-input", "textarea", "field", "label", "validator", "range", "range-slider", "range-inputs", "color-picker", "rating", "number-input", "input-counter", "otp-input")),
    Category("toggle", "Checkboxes, radios & toggles", _C, ("checkbox", "checkboxes", "radio", "radio-button", "radio-buttons", "radio-groups", "toggle", "toggles", "toggle-switch", "toggle-switches", "switch", "segmented-control", "toggle-group")),
    Category("select", "Selects & dropdowns", _C, ("select", "dropdown", "dropdowns", "combobox", "autocomplete", "context-menu", "picker")),
    Category("modal", "Modals, dialogs & popovers", _C, ("modal", "modals", "dialog", "alert-dialog", "drawer", "sheet", "popover", "pop-up", "popup", "lightbox", "tooltip-popover", "action-sheet", "bottom-sheet", "sheet-modal", "actions", "menu-sheet")),
    Category("tooltip", "Tooltips", _C, ("tooltip", "tooltips", "hover-card")),
    Category("tabs", "Tabs", _C, ("tabs", "tab", "segmented")),
    Category("accordion", "Accordions", _C, ("accordion", "accordions", "collapse", "collapsible", "details", "disclosure")),
    Category("alert", "Alerts & toasts", _C, ("alert", "alerts", "toast", "toasts", "banner-alert", "sonner", "callout", "feedback", "snackbar", "notification-banner")),
    Category("badge", "Badges & tags", _C, ("badge", "badges", "tag", "tags", "pill", "indicator", "indicators", "kbd", "status")),
    Category("avatar", "Avatars", _C, ("avatar", "avatars", "user-avatar", "avatar-group")),
    Category("loader", "Loaders & progress", _C, ("loader", "loaders", "loading", "spinner", "progress", "progress-bar", "loading-animation", "skeleton-loader", "steps-progress", "preloader", "progressbar")),
    Category("pagination", "Pagination", _C, ("pagination", "pager", "load-more")),
    Category("carousel", "Sliders & carousels", _C, ("carousel", "slider", "image-slider", "swiper", "scroll-area", "slides", "swiper-fade", "swiper-loop", "swiper-zoom")),
    Category("timeline", "Timelines & steps", _C, ("timeline", "steps", "stepper", "step", "wizard")),
    Category("layout", "Layouts & grids", _C, ("layout", "layouts", "grid", "grids", "resizable", "aspect-ratio", "aspect", "split", "container", "join", "fieldset", "masonry-grid", "columns")),
    Category("menu", "Menus & lists", _C, ("menu", "menus", "list-group", "divider", "dividers", "separator", "item", "swipeout", "sortable", "list-index", "virtual-list", "pull-to-refresh", "infinite-scroll")),
    Category("typography-ui", "Text & content blocks", _C, ("heading", "headings", "paragraph", "paragraphs", "blockquote", "text", "link", "links", "code-block", "mockup-code", "content-block", "block")),
    # ---------- Motion & effects ----------
    Category("animation", "Animations", _M, ("animation", "animated", "motion", "web-animation", "micro-interaction", "ui-interaction", "dynamic-island", "transition", "funny-animation", "character-animation", "confetti", "particles", "beam")),
    Category("hover-effect", "Hover & click effects", _M, ("hover", "hover-effect", "hover-state", "click-effect", "active", "ripple", "magnetic")),
    Category("text-effect", "Text effects", _M, ("text-effect", "text-animation", "typing", "typewriter", "gradient-text", "shiny", "reveal", "word-rotate")),
    Category("scroll-animation", "Scroll animations", _M, ("scroll-animation", "scroll-transition", "scroll", "parallax", "gsap")),
    Category("background", "Backgrounds & patterns", _M, ("pattern", "patterns", "background", "background-pattern", "grid-pattern", "noise", "texture", "gradient", "gradients", "aura", "orb")),
    Category("3d", "3D, WebGL & shaders", _M, ("3d", "webgl", "shader", "three", "low-poly", "virtual-reality", "liquid-metal", "globe")),
    # ---------- Style & brand ----------
    Category("guidelines", "Design guidelines", _S, ("guidelines", "guideline", "human-interface-guidelines", "hig", "material-3", "material-design-3", "m3", "foundations", "accessibility", "design-kit", "ui-kit-official")),
    Category("design-style", "Design styles", _S, ("design-style", "glassmorphism", "liquid-glass", "neumorphism", "neobrutalism", "brutal-design", "brutalism", "claymorphism", "minimalist", "swiss-minimalist", "botanical", "luxury", "terminal", "terminal-aesthetic", "monochrome", "modern-dark", "dark-mode", "retro", "skeuomorphism", "material-design", "web3")),
    Category("branding", "Branding & logos", _S, ("branding", "logo", "brand", "identity", "business-card", "packaging", "stamp", "poster", "book-cover", "pitch-deck", "mockup", "device-mockup", "device-mockups", "app-icon")),
    Category("illustration", "Illustrations", _S, ("illustration", "illustrations", "character", "emoji", "sticker", "playing-cards")),
    Category("fonts", "Typography & fonts", _S, ("typography", "font", "fonts", "typeface", "lettering", "calligraphy", "montserrat")),
    Category("color", "Colors & palettes", _S, ("color", "colors", "color-palette", "palette", "color-scale", "contrast")),
    Category("icons", "Icons", _S, ("icons", "icon", "icon-set", "svg-icons")),
    Category("tokens", "Design tokens & UI kits", _S, ("tokens", "design-tokens", "css-variables", "easing", "shadows", "sizes", "spacing", "ui-kit", "style-guide", "design-system", "wireframe")),
    Category("other", "Other", "Other", ()),
)

BY_SLUG: dict[str, Category] = {c.slug: c for c in CATEGORIES}
SLUGS: tuple[str, ...] = tuple(BY_SLUG)


def grouped() -> list[tuple[str, list[Category]]]:
    """[(group name, [categories...]), ...] in sidebar order."""
    return [(group, [c for c in CATEGORIES if c.group == group]) for group in GROUPS]
