use api_base::{Api, Response};

fn get_widgets() -> Response {
    Response::json(202, "[]")
}

pub fn build_api() -> Api {
    let mut api = Api::new();
    api.handle("GET", "/widgets", get_widgets);
    api
}
