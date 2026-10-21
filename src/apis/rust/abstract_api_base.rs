use axum::{
    body::Body,
    http::{header, HeaderValue, Request},
    middleware::{self, Next},
    response::Response,
    routing::MethodRouter,
    Router,
};

/// API builder that installs response hardening after all routes are registered.
pub struct Api {
    router: Router,
}

/// Creates an empty Axum API.
pub fn new() -> Api {
    Api {
        router: Router::new(),
    }
}

impl Api {
    /// Registers a route while retaining the API's response policy.
    pub fn route(mut self, path: &str, method_router: MethodRouter) -> Self {
        self.router = self.router.route(path, method_router);
        self
    }

    /// Returns the complete router, with security headers on routes and fallbacks.
    pub fn into_router(self) -> Router {
        self.router.layer(middleware::from_fn(security_headers))
    }
}

async fn security_headers(request: Request<Body>, next: Next) -> Response {
    let https = request.uri().scheme_str() == Some("https");
    let mut response = next.run(request).await;
    let headers = response.headers_mut();
    headers.insert(
        header::X_CONTENT_TYPE_OPTIONS,
        HeaderValue::from_static("nosniff"),
    );
    headers.insert(header::X_FRAME_OPTIONS, HeaderValue::from_static("DENY"));
    headers.insert(
        header::REFERRER_POLICY,
        HeaderValue::from_static("no-referrer"),
    );
    headers.insert(
        "permissions-policy",
        HeaderValue::from_static("camera=(), microphone=(), geolocation=()"),
    );
    if https {
        headers.insert(
            header::STRICT_TRANSPORT_SECURITY,
            HeaderValue::from_static("max-age=31536000"),
        );
    }
    response
}
