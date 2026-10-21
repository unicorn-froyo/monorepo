use axum::{http::StatusCode, routing::get, Json, Router};

async fn get_widgets() -> (StatusCode, Json<Vec<String>>) {
    (StatusCode::ACCEPTED, Json(Vec::new()))
}

pub fn build_api() -> Router {
    api_base::new().route("/widgets", get(get_widgets))
}
