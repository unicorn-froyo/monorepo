use axum::{body::{to_bytes, Body}, http::Request};
use tower::ServiceExt;

#[tokio::test]
async fn returns_widgets() {
    let response = get_widgets::build_api()
        .oneshot(Request::builder().uri("/widgets").body(Body::empty()).unwrap())
        .await
        .unwrap();

    assert_eq!(response.status(), 202);
    assert_eq!(response.headers()["x-content-type-options"], "nosniff");
    assert_eq!(
        response.headers().get("content-type").unwrap(),
        "application/json",
    );
    assert_eq!(to_bytes(response.into_body(), usize::MAX).await.unwrap(), "[]");
}
