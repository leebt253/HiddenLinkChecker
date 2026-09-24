"""Server-rendered pages for the authenticated web experience."""

from html import escape

from shared_contracts.api_models import CurrentUserResponse, LinkCheckHistoryItem, LinkCheckResponse


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
.stats { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; margin-top: 22px; }
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
.result-table th, .result-table td { padding: 12px 10px; border-bottom: 1px solid var(--line); text-align: left; }
.result-table th { color: var(--muted); font-size: 11px; letter-spacing: .08em; text-transform: uppercase; }
.back-link { display: inline-block; margin-top: 26px; color: var(--teal-dark); font: 700 13px Arial, sans-serif; text-decoration: none; }
@media (max-width: 800px) { .login-shell, .workspace { grid-template-columns: 1fr; } .login-copy h1 { font-size: 54px; } .dashboard-heading { display: block; } .dashboard-heading p { margin-top: 18px; } .topbar, .page-content, .login-shell { padding-left: 20px; padding-right: 20px; } .auth-panel { padding: 28px; } }
</style>
"""


def _document(title: str, body: str) -> str:
    return f'<!doctype html><html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{escape(title)}</title>{_STYLE}</head><body>{body}</body></html>'


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


def render_dashboard(history: list[LinkCheckHistoryItem], user: CurrentUserResponse) -> str:
    """Render URL submission and authenticated user's link-check history."""
    rows = "".join(
        f'<li class="history-item"><div class="history-item-main"><input class="history-url" type="text" value="{escape(item.submitted_url, quote=True)}" readonly aria-label="Submitted URL"><a href="/link-checks/{item.check_id}">Open inspection</a></div><span class="status">{escape(item.status)}</span></li>'
        for item in history
    )
    history_html = f'<ul class="history-list">{rows}</ul>' if rows else '<div class="empty">No checks yet. Your first inspection will appear here.</div>'
    body = (
        '<div class="site-shell"><header class="topbar">'
        f'{_brand()}{_profile(user)}'
        '</header><main class="page-content"><section class="dashboard-heading">'
        '<div><span class="eyebrow">Your control room</span><h1>Dashboard</h1></div>'
        '<p>Track the hidden destinations inside your pages before they become a blind spot.</p>'
        '</section><section class="workspace"><div class="panel">'
        '<span class="eyebrow">New inspection</span><h2>Check a URL</h2>'
        '<p>We will inspect the submitted page only. Discovered links are recorded, not opened.</p>'
        '<form class="url-form" action="/link-checks" method="post">'
        '<label for="url">Page address<input id="url" name="url" type="url" placeholder="https://example.com/page" required></label>'
        '<label class="check-option"><input name="include_dom" type="checkbox" checked> Include DOM context</label>'
        '<button class="primary-button" type="submit">Start inspection</button></form></div>'
        '<aside class="panel"><span class="eyebrow">Workspace pulse</span><div class="stats">'
        f'<div class="stat"><span class="muted">Checks</span><strong>{len(history)}</strong></div>'
        '<div class="stat"><span class="muted">Account</span><strong>OK</strong></div></div>'
        f'<div class="history"><h2>Recent checks</h2>{history_html}</div></aside></section></main></div>'
    )
    return _document("Dashboard - Hidden Link Checker", body)


def render_link_check(link_check: LinkCheckResponse) -> str:
    """Render a link-check result supplied by the API."""
    rows = "".join(
        "<tr>"
        f"<td>{escape(link.element_type)}</td>"
        f"<td>{escape(link.visibility)}</td>"
        f"<td>{escape(link.source_url)}</td>"
        f"<td>{escape(link.actual_url)}</td>"
        "</tr>"
        for link in link_check.links
    )
    body = (
        '<div class="site-shell"><header class="topbar">'
        f'{_brand()}</header><main class="page-content"><section class="panel">'
        f'<span class="eyebrow">Inspection / {escape(link_check.status)}</span>'
        f'<h1 class="inspection-title">Inspection result</h1>'
        f'<label class="inspection-url">Submitted URL<input type="text" value="{escape(link_check.submitted_url, quote=True)}" readonly></label>'
        '<table class="result-table"><thead><tr><th>Type</th><th>Visibility</th><th>Source</th><th>Actual URL</th></tr></thead>'
        f'<tbody>{rows}</tbody></table><a class="back-link" href="/">Back to dashboard</a>'
        '</section></main></div>'
    )
    return _document("Inspection - Hidden Link Checker", body)
