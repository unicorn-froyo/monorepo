use std::collections::HashMap;
use std::io::{self, BufRead, BufReader, Write};
use std::net::{TcpListener, TcpStream};

pub type Handler = fn() -> Response;

#[derive(Debug, Eq, PartialEq)]
pub struct Response {
    pub status: u16,
    pub content_type: &'static str,
    pub body: String,
}

impl Response {
    pub fn json(status: u16, body: impl Into<String>) -> Self {
        Self {
            status,
            content_type: "application/json",
            body: body.into(),
        }
    }
}

#[derive(Default)]
pub struct Api {
    routes: HashMap<(String, String), Handler>,
}

impl Api {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn handle(&mut self, method: &str, path: &str, handler: Handler) {
        self.routes
            .insert((method.to_owned(), path.to_owned()), handler);
    }

    pub fn dispatch(&self, method: &str, path: &str) -> Response {
        self.routes
            .get(&(method.to_owned(), path.to_owned()))
            .map(|handler| handler())
            .unwrap_or_else(|| Response::json(404, r#"{"error":"not found"}"#))
    }

    pub fn serve(&self, address: &str) -> io::Result<()> {
        let listener = TcpListener::bind(address)?;
        for stream in listener.incoming() {
            self.serve_connection(stream?)?;
        }
        Ok(())
    }

    fn serve_connection(&self, mut stream: TcpStream) -> io::Result<()> {
        let mut request_line = String::new();
        BufReader::new(stream.try_clone()?).read_line(&mut request_line)?;
        let mut parts = request_line.split_whitespace();
        let method = parts.next().unwrap_or_default();
        let path = parts.next().unwrap_or_default();
        let response = self.dispatch(method, path);
        let reason = match response.status {
            202 => "Accepted",
            404 => "Not Found",
            _ => "OK",
        };
        write!(
            stream,
            "HTTP/1.1 {} {}\r\nContent-Type: {}\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{}",
            response.status,
            reason,
            response.content_type,
            response.body.len(),
            response.body,
        )
    }
}
