use axum::{body::Body, http::Request};
use tower::ServiceExt;

#[tokio::test]
async fn creates_an_empty_router() {
    let response = api_base::new()
        .oneshot(Request::builder().uri("/missing").body(Body::empty()).unwrap())
        .await
        .unwrap();

    assert_eq!(response.status(), 404);
}
