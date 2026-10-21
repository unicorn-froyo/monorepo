"""Response header hardening for ASGI APIs."""

SECURITY_HEADERS = (
    (b"x-content-type-options", b"nosniff"),
    (b"x-frame-options", b"DENY"),
    (b"referrer-policy", b"no-referrer"),
    (b"permissions-policy", b"camera=(), microphone=(), geolocation=()"),
)
HSTS = (b"strict-transport-security", b"max-age=31536000")


class SecurityHeadersMiddleware:  # pylint: disable=too-few-public-methods
    """Add security headers to every HTTP response, including error responses."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                headers = message.setdefault("headers", [])
                names = {name for name, _ in SECURITY_HEADERS}
                if scope.get("scheme") == "https":
                    names.add(HSTS[0])
                headers[:] = [(name, value) for name, value in headers if name.lower() not in names]
                headers.extend(SECURITY_HEADERS)
                if scope.get("scheme") == "https":
                    headers.append(HSTS)
            await send(message)

        await self.app(scope, receive, send_with_headers)
