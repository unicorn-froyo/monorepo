use axum::{body::Body, http::Request};
use tower::ServiceExt;

#[tokio::test]
async fn creates_an_empty_router() {
    let response = api_base::new()
        .into_router()
        .oneshot(
            Request::builder()
                .uri("/missing")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), 404);
    assert_eq!(response.headers()["x-content-type-options"], "nosniff");
    assert_eq!(response.headers()["x-frame-options"], "DENY");
    assert_eq!(response.headers()["referrer-policy"], "no-referrer");
    assert_eq!(
        response.headers()["permissions-policy"],
        "camera=(), microphone=(), geolocation=()"
    );
    assert!(!response.headers().contains_key("strict-transport-security"));
}

#[tokio::test]
async fn registers_routes() {
    let response = api_base::new()
        .route("/health", axum::routing::get(|| async { "healthy" }))
        .into_router()
        .oneshot(
            Request::builder()
                .uri("/health")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(response.status(), 200);
    assert_eq!(response.headers()["x-content-type-options"], "nosniff");
}

#[tokio::test]
async fn adds_hsts_on_https() {
    let response = api_base::new()
        .into_router()
        .oneshot(
            Request::builder()
                .uri("https://example.com/missing")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(
        response.headers()["strict-transport-security"],
        "max-age=31536000"
    );
}
