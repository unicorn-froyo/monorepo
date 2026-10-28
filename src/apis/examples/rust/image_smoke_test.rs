use std::env;
use std::process::{Command, Output};
use std::thread;
use std::time::Duration;

const IMAGE: &str = "get-widgets-rust:latest";
const REQUEST_SCRIPT: &str = r#"
exec 3<>/dev/tcp/127.0.0.1/8080
printf "GET %s HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n" "$1" >&3
cat <&3
"#;

struct Container {
    id: String,
}

impl Drop for Container {
    fn drop(&mut self) {
        if let Ok(logs) = docker_output(&["logs", &self.id]) {
            eprintln!("{logs}");
        }
        let _ = Command::new("docker")
            .args(["rm", "--force", &self.id])
            .output();
    }
}

fn docker(args: &[&str]) -> Output {
    Command::new("docker")
        .args(args)
        .output()
        .unwrap_or_else(|error| panic!("failed to run docker {args:?}: {error}"))
}

fn docker_output(args: &[&str]) -> Result<String, String> {
    let output = docker(args);
    if output.status.success() {
        Ok(String::from_utf8_lossy(&output.stdout).trim().to_owned())
    } else {
        Err(format!(
            "docker {args:?} failed:\n{}",
            String::from_utf8_lossy(&output.stderr)
        ))
    }
}

fn request(container: &Container, path: &str) -> Result<String, String> {
    docker_output(&[
        "exec",
        &container.id,
        "bash",
        "-c",
        REQUEST_SCRIPT,
        "bash",
        path,
    ])
}

fn assert_response(response: &str, status: u16) {
    let normalized = response.replace('\r', "");
    assert!(
        normalized.starts_with(&format!("HTTP/1.1 {status} ")),
        "unexpected response status:\n{response}"
    );
    for header in [
        "x-content-type-options: nosniff",
        "x-frame-options: DENY",
        "referrer-policy: no-referrer",
        "permissions-policy: camera=(), microphone=(), geolocation=()",
    ] {
        assert!(
            normalized
                .lines()
                .any(|line| line.eq_ignore_ascii_case(header)),
            "missing {header:?}:\n{response}"
        );
    }
    assert!(
        !normalized.lines().any(|line| line
            .to_ascii_lowercase()
            .starts_with("strict-transport-security:")),
        "unexpected HSTS on an HTTP connection:\n{response}"
    );
}

#[test]
fn image_serves_offline_with_expected_metadata() {
    let expected_arch = env::var("ARCH").expect("ARCH must name the expected Docker architecture");
    assert_eq!(
        docker_output(&["image", "inspect", IMAGE, "--format", "{{.Architecture}}"])
            .expect("inspect image architecture"),
        expected_arch
    );
    assert_eq!(
        docker_output(&[
            "image",
            "inspect",
            IMAGE,
            "--format",
            "{{json .Config.Entrypoint}}",
        ])
        .expect("inspect image entrypoint"),
        r#"["/app/server"]"#
    );

    let container = Container {
        id: docker_output(&[
            "run",
            "--detach",
            "--network",
            "none",
            "--read-only",
            "--cap-drop",
            "ALL",
            IMAGE,
        ])
        .expect("start image"),
    };

    let widgets = (0..30)
        .find_map(|_| match request(&container, "/widgets") {
            Ok(response) => Some(response),
            Err(_) => {
                thread::sleep(Duration::from_secs(1));
                None
            }
        })
        .expect("server did not become ready within 30 seconds");

    assert_response(&widgets, 202);
    assert!(
        widgets.ends_with("\r\n\r\n[]"),
        "unexpected body:\n{widgets}"
    );
    assert_response(
        &request(&container, "/missing").expect("request missing route"),
        404,
    );
}
