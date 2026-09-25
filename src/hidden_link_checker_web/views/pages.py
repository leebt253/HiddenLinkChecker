"""Server-rendered pages for the authenticated web experience."""

from html import escape

from shared_contracts.api_models import (
    CurrentUserResponse,
    LinkCheckHistoryItem,
    LinkCheckResponse,
)

_STYLE = """
<style>
:root {
  --ink: #172326; --muted: #667477; --paper: #f4f1eb; --white: #fffdf8;
  --line: #d9ddd9; --teal: #0b7772; --teal-dark: #075650; --coral: #e76f51;
  --shadow: 0 20px 60px rgba(23, 35, 38, .12);
}
* { box-sizing: border-box; }
body { margin: 0; color: var(--ink); background: var(--paper); font-family: Georgia, "Times New Roman", serif; }
button, input { font: inherit; }
a { color: inherit; }
.site-shell { min-height: 100vh; background: radial-gradient(circle at 85% 12%, #d5ebe5 0, transparent 28%), var(--paper); }
.topbar { display: flex; align-items: center; justify-content: space-between; max-width: 1240px; margin: 0 auto; padding: 28px 32px; }
.brand { display: flex; align-items: center; gap: 12px; font-weight: 700; letter-spacing: .02em; text-decoration: none; }
.brand-mark { display: grid; place-items: center; width: 34px; height: 34px; color: var(--white); background: var(--teal); border-radius: 50% 50% 50% 8px; font-family: Arial, sans-serif; }
.eyebrow { color: var(--coral); font: 700 12px/1.2 Arial, sans-serif; letter-spacing: .16em; text-transform: uppercase; }
.muted { color: var(--muted); }
.login-shell { display: grid; grid-template-columns: minmax(0, 1.1fr) minmax(340px, .9fr); gap: 5vw; align-items: center; max-width: 1180px; min-height: calc(100vh - 90px); margin: 0 auto; padding: 40px 32px 80px; }
.login-copy { max-width: 650px; }
.login-copy h1 { max-width: 620px; margin: 18px 0; font-size: clamp(48px, 7vw, 92px); line-height: .94; letter-spacing: -.04em; }
.login-copy p { max-width: 510px; color: var(--muted); font: 18px/1.6 Arial, sans-serif; }
.signal-list { display: grid; gap: 12px; margin: 42px 0 0; padding: 0; list-style: none; font: 14px/1.4 Arial, sans-serif; }
.signal-list li { display: flex; gap: 10px; align-items: center; }
.signal-list li::before { content: ""; width: 8px; height: 8px; background: var(--coral); border-radius: 50%; }
.auth-panel { padding: 42px; background: var(--white); border: 1px solid var(--line); box-shadow: var(--shadow); }
.auth-panel h2 { margin: 8px 0 12px; font-size: 36px; line-height: 1; }
.auth-panel p { color: var(--muted); font: 14px/1.6 Arial, sans-serif; }
.google-button, .primary-button { display: inline-flex; justify-content: center; align-items: center; gap: 10px; width: 100%; margin-top: 26px; padding: 15px 20px; border: 0; color: var(--white); background: var(--teal); font: 700 14px Arial, sans-serif; text-decoration: none; cursor: pointer; transition: background .2s, transform .2s; }
.google-button:hover, .primary-button:hover { background: var(--teal-dark); transform: translateY(-2px); }
.google-g { display: grid; place-items: center; width: 24px; height: 24px; color: var(--teal); background: var(--white); border-radius: 50%; font: 700 15px Arial, sans-serif; }
.page-content { max-width: 1240px; margin: 0 auto; padding: 26px 32px 80px; }
.profile { display: flex; align-items: center; gap: 12px; font: 13px Arial, sans-serif; }
.avatar { display: grid; place-items: center; width: 38px; height: 38px; overflow: hidden; color: var(--white); background: var(--coral); border-radius: 50%; font-weight: 700; }
.avatar img { width: 100%; height: 100%; object-fit: cover; }
.logout-button { border: 0; color: var(--muted); background: transparent; font: 700 12px Arial, sans-serif; cursor: pointer; }
.dashboard-heading { display: flex; justify-content: space-between; align-items: end; gap: 30px; margin: 34px 0 28px; }
.dashboard-heading h1 { margin: 8px 0 0; font-size: clamp(42px, 6vw, 76px); line-height: .95; letter-spacing: -.04em; }
.dashboard-heading p { max-width: 410px; margin: 0; color: var(--muted); font: 14px/1.5 Arial, sans-serif; }
.workspace { display: grid; grid-template-columns: minmax(0, 1.1fr) minmax(300px, .9fr); gap: 22px; }
.panel { min-width: 0; padding: 28px; overflow: hidden; background: var(--white); border: 1px solid var(--line); }
.panel h1 { margin: 12px 0; font-size: clamp(34px, 5vw, 58px); line-height: .98; overflow-wrap: anywhere; }
.inspection-title { font-size: clamp(22px, 3vw, 38px) !important; line-height: 1.08 !important; word-break: break-word; }
.panel h2 { margin: 0 0 8px; font-size: 28px; }
.panel p { color: var(--muted); font: 14px/1.5 Arial, sans-serif; }
.url-form { display: grid; gap: 14px; margin-top: 22px; }
.url-form label { min-width: 0; color: var(--muted); font: 700 12px Arial, sans-serif; letter-spacing: .08em; text-transform: uppercase; }
.url-form input[type=url] { display: block; width: 100%; min-width: 0; max-width: 100%; margin-top: 8px; padding: 14px; border: 1px solid var(--line); color: var(--ink); background: #faf9f5; outline: none; }
.url-form input[type=url]:focus { border-color: var(--teal); box-shadow: 0 0 0 3px rgba(11, 119, 114, .12); }
.check-option { display: flex; align-items: center; gap: 9px; color: var(--muted); font: 14px Arial, sans-serif; }
.check-option input { accent-color: var(--teal); }
.stats { display: grid; grid-template-columns: minmax(0, 1fr); gap: 12px; margin-top: 22px; }
.stat { padding: 18px; background: #e4f0ec; }
.stat strong { display: block; margin-top: 6px; font-size: 30px; }
.history { margin-top: 22px; }
.history-list { display: grid; gap: 10px; margin: 18px 0 0; padding: 0; list-style: none; }
.history-item { display: flex; justify-content: space-between; align-items: center; gap: 18px; padding: 16px 0; border-bottom: 1px solid var(--line); font: 14px Arial, sans-serif; }
.history-item-main { display: grid; min-width: 0; gap: 8px; flex: 1 1 auto; }
.history-url, .inspection-url input { width: 100%; min-width: 0; max-width: 100%; padding: 11px 12px; overflow: hidden; border: 1px solid var(--line); color: var(--ink); background: #faf9f5; font: 14px Arial, sans-serif; text-overflow: ellipsis; }
.history-item a { color: var(--teal-dark); font: 700 12px Arial, sans-serif; text-decoration: none; }
.status { flex: 0 0 auto; padding: 5px 8px; color: var(--teal-dark); background: #d7eee8; font: 700 11px Arial, sans-serif; text-transform: uppercase; }
.empty { padding: 22px 0; color: var(--muted); font: 14px Arial, sans-serif; }
.inspection-url { display: block; max-width: 100%; margin: 22px 0 0; color: var(--muted); font: 700 12px Arial, sans-serif; letter-spacing: .08em; text-transform: uppercase; }
.inspection-url input { display: block; margin-top: 8px; }
.welcome-panel { max-width: 620px; margin: 12vh auto; text-align: center; }
.welcome-panel .primary-button { width: auto; padding-left: 32px; padding-right: 32px; }
.result-table { width: 100%; margin-top: 22px; border-collapse: collapse; font: 13px Arial, sans-serif; }
.result-filter + .result-filter { margin-left: 20px; }
.results-scroll { max-width: 100%; max-height: 520px; margin-top: 22px; overflow: auto; padding: 4px; border: 1px solid var(--line); }
.results-scroll .result-table { margin-top: 0; min-width: 760px; }
.result-table th, .result-table td { padding: 12px 10px; border-bottom: 1px solid var(--line); text-align: left; }
.result-table th { color: var(--muted); font-size: 11px; letter-spacing: .08em; text-transform: uppercase; }
.result-status { margin: 18px 0; padding: 14px 16px; border-left: 4px solid var(--teal); background: #e4f0ec; font: 14px/1.5 Arial, sans-serif; }
.result-status strong { display: block; margin-bottom: 3px; color: var(--teal-dark); }
.result-status-partial { border-color: #bd7c18; background: #fff2d7; }
.result-status-partial strong { color: #825000; }
.result-status-failed { border-color: #b23d35; background: #fbe7e3; }
.result-status-failed strong { color: #8b2822; }
.dom-context { margin-top: 20px; font: 14px Arial, sans-serif; }
.dom-context pre { max-height: 360px; overflow: auto; padding: 14px; background: #eef1ed; white-space: pre-wrap; overflow-wrap: anywhere; }
.pagination { display: flex; flex-wrap: wrap; align-items: center; gap: 10px; margin-top: 18px; font: 13px Arial, sans-serif; }
.pagination a, .pagination select { padding: 8px 10px; border: 1px solid var(--line); color: var(--teal-dark); background: var(--white); text-decoration: none; }
.pagination select { cursor: pointer; }
.back-link { display: inline-block; margin-top: 26px; color: var(--teal-dark); font: 700 13px Arial, sans-serif; text-decoration: none; }
@media (max-width: 800px) { .login-shell, .workspace { grid-template-columns: 1fr; } .login-copy h1 { font-size: 54px; } .dashboard-heading { display: block; } .dashboard-heading p { margin-top: 18px; } .topbar, .page-content, .login-shell { padding-left: 20px; padding-right: 20px; } .auth-panel { padding: 28px; } }
</style>
"""


def _document(title: str, body: str, head: str = "") -> str:
    return f'<!doctype html><html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{escape(title)}</title>{head}{_STYLE}</head><body>{body}</body></html>'


def _brand() -> str:
    return '<a class="brand" href="/"><span class="brand-mark">H</span><span>Hidden Link Checker</span></a>'


def _profile(user: CurrentUserResponse) -> str:
    display_name = escape(user.display_name or user.email)
    avatar = f'<img src="{escape(user.avatar_url, quote=True)}" alt="">' if user.avatar_url else escape((user.display_name or user.email)[:1].upper())
    return f'<div class="profile"><span class="avatar">{avatar}</span><span>{display_name}</span><form action="/logout" method="post"><button class="logout-button" type="submit">Đăng xuất</button></form></div>'


def render_login(google_login_url: str) -> str:
    """Render the unauthenticated entry point for Google sign-in."""
    body = (
        '<div class="site-shell"><header class="topbar">'
        f'{_brand()}<span class="eyebrow">DOM INTELLIGENCE / 01</span></header>'
        '<main class="login-shell"><section class="login-copy">'
        '<span class="eyebrow">See what is hidden</span>'
        '<h1>Find the links your page forgot to show.</h1>'
        '<p>Scan a page, surface every referenced destination, and keep a clear record of what your users could miss.</p>'
        '<ul class="signal-list"><li>Text, image and background links</li><li>Ownership-aware scan history</li><li>Google sign-in with secure sessions</li></ul>'
        '</section><section class="auth-panel"><span class="eyebrow">Private workspace</span>'
        '<h2>Welcome back.</h2><p>Sign in with Google to open your link intelligence dashboard.</p>'
        f'<a class="google-button" href="{escape(google_login_url, quote=True)}"><span class="google-g">G</span> Đăng nhập với Google</a>'
        '</section></main></div>'
    )
    return _document("Sign in - Hidden Link Checker", body)




def render_error(status_code: int, title: str, message: str) -> str:
    """Render a safe, user-facing error page without exposing server internals."""
    body = (
        '<div class="site-shell"><header class="topbar">'
        f'{_brand()}</header><main class="page-content"><section class="panel welcome-panel">'
        f'<span class="eyebrow">Error {status_code}</span>'
        f'<h1 class="inspection-title">{escape(title)}</h1>'
        f'<p>{escape(message)}</p>'
        '<a class="primary-button" href="/">Return to dashboard</a>'
        '</section></main></div>'
    )
    return _document(f"Error {status_code} - Hidden Link Checker", body)


def render_dashboard(
    history: list[LinkCheckHistoryItem], user: CurrentUserResponse, recent_page: int = 1
) -> str:
    """Render URL submission and authenticated user's link-check history."""
    unique_by_url: dict[str, LinkCheckHistoryItem] = {}
    for item in history:
        unique_by_url.setdefault(item.url, item)
    unique_history = list(unique_by_url.values())
    page_size = 10
    page_count = max(1, (len(unique_history) + page_size - 1) // page_size)
    current_page = min(max(recent_page, 1), page_count)
    page_start = (current_page - 1) * page_size
    visible_history = unique_history[page_start : page_start + page_size]
    rows = "".join(
        f'<li class="history-item"><div class="history-item-main"><input class="history-url" type="text" value="{escape(item.url, quote=True)}" readonly aria-label="Checked URL"><span class="muted">{escape(item.checked_at.isoformat())}</span></div><form action="/link-checks/{item.check_id}/delete" method="post"><button class="logout-button" type="submit">Delete history</button></form></li>'
        for item in visible_history
    )
    if rows:
        page_links = []
        if current_page > 1:
            page_links.append(f'<a href="/?recent_page={current_page - 1}" rel="prev">Previous</a>')
        page_links.extend(
            f'<a href="/?recent_page={page}" aria-current="page">{page}</a>'
            if page == current_page
            else f'<a href="/?recent_page={page}">{page}</a>'
            for page in range(1, page_count + 1)
        )
        if current_page < page_count:
            page_links.append(f'<a href="/?recent_page={current_page + 1}" rel="next">Next</a>')
        history_html = (
            f'<ul class="history-list">{rows}</ul>'
            f'<nav class="pagination" aria-label="Recent checks pages">'
            f'<span>Page {current_page} of {page_count} · {len(unique_history)} URLs</span>'
            f'{"".join(page_links)}</nav>'
        )
    else:
        history_html = '<div class="empty">No checks yet. Your first inspection will appear here.</div>'
    body = (
        '<div class="site-shell"><header class="topbar">'
        f'{_brand()}{_profile(user)}'
        '</header><main class="page-content"><section class="dashboard-heading">'
        '<div><span class="eyebrow">Your control room</span><h1>Dashboard</h1></div>'
        '<p>Track the hidden destinations inside your pages before they become a blind spot.</p>'
        '</section><section class="workspace"><div class="panel">'
        '<span class="eyebrow">New inspection</span><h2>Check a URL</h2>'
        '<p>We inspect only the submitted page. Findings appear in this response and are not saved.</p>'
        '<form class="url-form" action="/link-checks" method="post">'
        '<label for="url">Page address<input id="url" name="url" type="url" placeholder="https://example.com/page" required></label>'
        '<button class="primary-button" type="submit">Check URL</button></form></div>'
        '<aside class="panel"><span class="eyebrow">Workspace pulse</span><div class="stats">'
        f'<div class="stat"><span class="muted">Unique URLs checked</span><strong>{len(unique_history)}</strong></div>'
        '</div>'
        f'<div class="history"><h2>Recent checks</h2>{history_html}</div></aside></section></main></div>'
    )
    return _document("Dashboard - Hidden Link Checker", body)


def render_link_check(link_check: LinkCheckResponse) -> str:
    """Render the one-request result supplied directly by the API."""
    rows = "".join(
        f'<tr data-element-type="{escape(link.element_type)}" data-visibility="{escape(link.visibility)}">'
        f"<td>{escape(link.element_type)}</td>"
        f"<td>{escape(link.visibility)}</td>"
        f"<td>{escape(link.object_reference or '')}</td>"
        f"<td>{escape(link.source_url)}</td>"
        f"<td>{escape(link.actual_url)}</td>"
        f"<td>{escape(link.visible_text or '')}</td>"
        f"<td>{escape(link.alt_text or '')}</td>"
        f"<td>{escape(_format_position(link.position))}</td>"
        "</tr>"
        for link in link_check.links
    )
    total_records = len(link_check.links)
    status_copy = {
        "completed": ("Inspection completed", "The page was inspected successfully."),
        "partial": (
            "Partial result",
            "The page could not be fully inspected. Review the limitations and treat these findings as incomplete.",
        ),
        "failed": (
            "Inspection failed",
            "The page could not be inspected. No link findings are available for this request.",
        ),
    }
    status_title, status_message = status_copy[link_check.status]
    status_detail = (
        f'<span> Error code: {escape(link_check.error_code)}</span>' if link_check.error_code else ""
    )
    status_block = (
        f'<div class="result-status result-status-{escape(link_check.status)}" role="status">'
        f'<strong>{status_title}</strong>{status_message}{status_detail}</div>'
    )
    links_summary = (
        f'<p class="muted" id="findings-total" data-total="{total_records}">'
        f'{total_records} hidden link(s) found in this URL.</p>'
        if link_check.links or link_check.status != "failed"
        else ""
    )
    no_findings_message = (
        '<p class="muted">No hidden links were found in the processed page content.</p>'
        if not link_check.links and link_check.status != "failed"
        else ""
    )
    limitations = "".join(f"<li>{escape(item)}</li>" for item in link_check.limitations)
    limitations_block = (
        f'<div class="limitations"><strong>Limitations</strong><ul>{limitations}</ul></div>'
        if limitations
        else ""
    )
    results_table = (
        '<label class="result-filter">Visibility <select id="visibility-filter"><option value="all">All</option><option value="direct">Direct</option><option value="indirect">Indirect</option></select></label>'
        '<label class="result-filter">Type <select id="type-filter"><option value="all">All</option><option value="text">Text</option><option value="image">Image</option><option value="background">Background</option></select></label>'
        '<div class="results-scroll"><table class="result-table"><thead><tr><th>Element type</th><th>Visibility</th><th>Object reference</th><th>Source URL</th><th>Actual URL</th><th>Visible text</th><th>Alt text</th><th>Position</th></tr></thead>'
        f'<tbody>{rows}</tbody></table></div>'
        '<nav class="pagination" id="results-pagination" aria-label="Inspection result pages">'
        '<button type="button" id="results-previous">Previous</button>'
        '<span id="results-page-status" aria-live="polite"></span>'
        '<button type="button" id="results-next">Next</button>'
        '<label for="results-page-size">Rows per page <select id="results-page-size">'
        '<option value="30" selected>30</option><option value="50">50</option><option value="100">100</option>'
        '</select></label></nav>'
        if rows
        else ""
    )
    dom_context = (
        f'<details class="dom-context"><summary>DOM excerpt</summary><pre>{escape(link_check.dom_excerpt)}</pre></details>'
        if link_check.dom_excerpt
        else ""
    )
    filter_script = """<script>
document.addEventListener('DOMContentLoaded', () => {
const filters = [document.getElementById('visibility-filter'), document.getElementById('type-filter')];
const pageSizeSelect = document.getElementById('results-page-size');
const previousButton = document.getElementById('results-previous');
const nextButton = document.getElementById('results-next');
const pageStatus = document.getElementById('results-page-status');
const resultRows = Array.from(document.querySelectorAll('.result-table tbody tr'));
let currentPage = 1;
function filterFindings() {
  const [visibility, type] = filters.map(select => select.value);
  const matchingRows = resultRows.filter(row =>
    (visibility === 'all' || row.dataset.visibility === visibility)
    && (type === 'all' || row.dataset.elementType === type)
  );
  const pageSize = Number(pageSizeSelect.value);
  const pageCount = Math.max(1, Math.ceil(matchingRows.length / pageSize));
  currentPage = Math.min(currentPage, pageCount);
  const firstRow = (currentPage - 1) * pageSize;
  const visibleRows = new Set(matchingRows.slice(firstRow, firstRow + pageSize));
  resultRows.forEach(row => {
    row.hidden = !visibleRows.has(row);
  });
  pageStatus.textContent = `Page ${currentPage} of ${pageCount} · ${matchingRows.length} shown`;
  previousButton.disabled = currentPage <= 1;
  nextButton.disabled = currentPage >= pageCount;
}
filters.forEach(select => select.addEventListener('change', () => { currentPage = 1; filterFindings(); }));
pageSizeSelect.addEventListener('change', () => { currentPage = 1; filterFindings(); });
previousButton.addEventListener('click', () => { currentPage -= 1; filterFindings(); });
nextButton.addEventListener('click', () => { currentPage += 1; filterFindings(); });
filterFindings();
});
</script>""" if link_check.links else ""
    body = (
        '<div class="site-shell"><header class="topbar">'
        f'{_brand()}</header><main class="page-content"><section class="panel">'
        f'<span class="eyebrow">Inspection / {escape(link_check.status)}</span>'
        f'<h1 class="inspection-title">Inspection result</h1>'
        f'<label class="inspection-url">Submitted URL<input type="text" value="{escape(link_check.submitted_url, quote=True)}" readonly></label>'
        f'{status_block}'
        f'<p class="muted">Checked at {escape(link_check.checked_at.isoformat())}</p>'
        f'{links_summary}{no_findings_message}{limitations_block}{dom_context}{results_table}<a class="back-link" href="/">Back to dashboard</a>'
        '</section></main></div>'
    )
    return _document("Inspection - Hidden Link Checker", body, filter_script)


def _format_position(position: dict[str, float] | None) -> str:
    """Render only the explicitly allowed numeric DOM position fields."""
    if not position:
        return ""
    return ", ".join(
        f"{escape(axis)}: {escape(format(value, 'g'))}" for axis, value in position.items()
    )
