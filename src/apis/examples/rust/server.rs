use get_widgets::build_api;

fn main() -> std::io::Result<()> {
    build_api().serve("0.0.0.0:8080")
}
