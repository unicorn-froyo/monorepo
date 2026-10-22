use axum::{
    body::{to_bytes, Body},
    http::Request,
};
use tower::ServiceExt;

#[tokio::test]
async fn hardens_https_and_missing_routes() {
    for (uri, status) in [
        ("https://example.com/widgets", 202),
        ("https://example.com/missing", 404),
    ] {
        let response = get_widgets::build_api()
            .oneshot(Request::builder().uri(uri).body(Body::empty()).unwrap())
            .await
            .unwrap();
        assert_eq!(response.status(), status);
        assert_eq!(response.headers()["x-content-type-options"], "nosniff");
        assert_eq!(response.headers()["x-frame-options"], "DENY");
        assert_eq!(response.headers()["referrer-policy"], "no-referrer");
        assert_eq!(
            response.headers()["permissions-policy"],
            "camera=(), microphone=(), geolocation=()"
        );
        assert_eq!(
            response.headers()["strict-transport-security"],
            "max-age=31536000"
        );
    }
}

#[tokio::test]
async fn returns_widgets() {
    let response = get_widgets::build_api()
        .oneshot(
            Request::builder()
                .uri("/widgets")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), 202);
    assert_eq!(response.headers()["x-content-type-options"], "nosniff");
    assert_eq!(
        response.headers().get("content-type").unwrap(),
        "application/json",
    );
    assert_eq!(
        to_bytes(response.into_body(), usize::MAX).await.unwrap(),
        "[]"
    );
}
