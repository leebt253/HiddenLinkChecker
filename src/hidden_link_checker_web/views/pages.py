"""Server-rendered pages; these functions depend only on API DTOs."""

from html import escape

from shared_contracts.api_models import CurrentUserResponse, LinkCheckHistoryItem, LinkCheckResponse


def render_login(google_login_url: str) -> str:
    """Render the unauthenticated entry point for Google sign-in."""
    return (
        "<!doctype html><html><body><main><h1>Hidden Link Checker</h1>"
        f'<a href="{escape(google_login_url, quote=True)}">Đăng nhập với Google</a>'
        "</main></body></html>"
    )


def render_welcome(user: CurrentUserResponse) -> str:
    """Render the authenticated welcome page using the API public profile."""
    display_name = user.display_name or user.email
    return (
        "<!doctype html><html><body><main><h1>Chào mừng</h1>"
        f"<p>{escape(display_name)}</p>"
        '<form action="/logout" method="post"><button type="submit">Đăng xuất</button></form>'
        "</main></body></html>"
    )


def render_dashboard(history: list[LinkCheckHistoryItem]) -> str:
    """Render URL submission and the current user's scan history."""
    rows = "".join(
        "<li>"
        f'<a href="/link-checks/{item.check_id}">{escape(item.submitted_url)}</a> '
        f"({escape(item.status)})"
        "</li>"
        for item in history
    )
    return (
        "<!doctype html><html><body><main><h1>Hidden Link Checker</h1>"
        '<form action="/link-checks" method="post">'
        '<label>URL <input name="url" type="url" required></label>'
        '<label><input name="include_dom" type="checkbox" checked> Include DOM</label>'
        '<button type="submit">Check URL</button></form><h2>History</h2>'
        f"<ul>{rows}</ul></main></body></html>"
    )


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
    return (
        "<!doctype html><html><body><main>"
        f"<h1>{escape(link_check.submitted_url)}</h1>"
        f"<p>Status: {escape(link_check.status)}</p>"
        "<table><thead><tr><th>Type</th><th>Visibility</th><th>Source</th>"
        f"<th>Actual URL</th></tr></thead><tbody>{rows}</tbody></table>"
        '<p><a href="/">Back to dashboard</a></p></main></body></html>'
    )
