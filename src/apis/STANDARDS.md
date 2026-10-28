# Cross-platform API standards

These standards apply to Go, Java, Python, Ruby, Rust, and TypeScript APIs under
`src/apis/`. Keep the behavior consistent when adding a stack or changing a
shared API base; implement it in the language's API foundation rather than
copying it into each endpoint.

## HTTP application contract

- Expose a portable HTTP application/handler, not a cloud-function handler.
  The server entrypoint serves the application; route code must not depend on a
  particular cloud provider.
- Use the language's shared API foundation under `src/apis/<language>/` and
  register routes there. Examples under `src/apis/examples/` demonstrate the
  contract; each serves `GET /widgets` on port 8080 and returns `202` with an
  empty JSON array.
- Build and test through Bazel. Package example services as OCI-compatible
  images, keeping image targets `manual` so `bazelisk build //...` does not
  load them.

## Response-header policy

Apply these headers to every HTTP response, including routed requests and
framework-generated not-found responses:

| Header | Value |
| --- | --- |
| `X-Content-Type-Options` | `nosniff` |
| `X-Frame-Options` | `DENY` |
| `Referrer-Policy` | `no-referrer` |
| `Permissions-Policy` | `camera=(), microphone=(), geolocation=()` |

For requests known to be HTTPS, also send
`Strict-Transport-Security: max-age=31536000`. Do not send HSTS on HTTP; do
not add `includeSubDomains` or `preload` without a separate domain-wide
rollout. Use the trusted connection scheme, not an untrusted forwarding
header. When TLS terminates at a proxy, configure the proxy and application
to propagate and trust the original scheme appropriately. The Rust middleware
currently reads the request URI scheme, so its server must preserve that
scheme for HSTS to be emitted.

Do not add a blanket Content-Security-Policy without accounting for built-in
HTML endpoints such as FastAPI's interactive API documentation. Express APIs
also disable `X-Powered-By`.

## Middleware integration

- Go: construct services with `api.New()`; Gin middleware is registered on the
  engine before routes.
- Java: extend `AbstractApiBase`; its Spring `OncePerRequestFilter` runs before
  MVC routing so successful, error, and not-found responses share the policy.
- Python: subclass `AbstractApiBase`; it installs ASGI middleware before
  configuring routes.
- Ruby: subclass `AbstractApiBase`; its Railtie registers Rack middleware at
  the start of the Rails stack so routing errors are covered too.
- Rust: register routes with `api_base::new()` and call `.into_router()` **after**
  the last route to apply the Axum middleware to the whole router. Do not add
  unprotected routes to the returned router.
- TypeScript: extend `AbstractApiBase`; Express middleware is installed
  before `configureRoutes()` registers endpoints.

Test the header policy in each language's shared base and an example endpoint.
Cover a successful request, a missing route, HTTP without HSTS, and HTTPS
with HSTS (using the stack's trusted-scheme mechanism). Run
`bazelisk build //...` and `bazelisk test //...` before merging.
