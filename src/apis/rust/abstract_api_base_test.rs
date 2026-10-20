use api_base::{Api, Response};

fn health() -> Response {
    Response::json(202, r#"{"status":"ok"}"#)
}

#[test]
fn dispatches_registered_routes() {
    let mut api = Api::new();
    api.handle("GET", "/health", health);

    assert_eq!(api.dispatch("GET", "/health"), health());
}

#[test]
fn returns_not_found_for_unknown_routes() {
    let api = Api::new();

    assert_eq!(api.dispatch("GET", "/missing").status, 404);
}
