use get_widgets::build_api;

#[test]
fn returns_widgets() {
    let response = build_api().dispatch("GET", "/widgets");

    assert_eq!(response.status, 202);
    assert_eq!(response.content_type, "application/json");
    assert_eq!(response.body, "[]");
}
