"""Disposable PostgreSQL and Flyway lifecycle for Bazel coverage tests."""

import argparse
import json
import os
import re
import secrets
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
from contextlib import closing, contextmanager
from pathlib import Path
from uuid import uuid4

import docker
import psycopg
from docker.errors import DockerException
from psycopg import sql

from tools.migrations.python.schema import validate

LABEL = "com.unicorn-froyo.postgresql-test"


def private_json(path: Path, value: dict) -> None:
    """Create credentials with restricted permissions before writing their contents."""
    with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w") as stream:
        json.dump(value, stream)


def run_flyway(fixture: dict, bundle: dict, connection: dict, password: str, root: Path) -> None:
    """Apply the declared migrations using Bazel's Java launcher and pinned JARs."""
    directory = root / "migrations"
    directory.mkdir()
    for filename in bundle["sql_files"] + bundle["script_configs"]:
        shutil.copyfile(filename, directory / Path(filename).name)
    config = root / "flyway.conf"
    config.write_text("flyway.validateOnMigrate=true\n")
    env = {key: value for key, value in os.environ.items() if not key.startswith("FLYWAY_")}
    # Java must use the fixture's complete runfiles, including when invoked by
    # bazel run rather than bazel test. A sibling CLI runfiles tree may be stale.
    env["JAVA_RUNFILES"] = os.environ.get("TEST_SRCDIR", str(Path.cwd().parent))
    env.update(
        FLYWAY_URL=f"jdbc:postgresql://{connection['host']}:{connection['port']}/{connection['database']}?options=-c%20lock_timeout%3D2000%20-c%20statement_timeout%3D10000",
        FLYWAY_USER="postgres",
        FLYWAY_PASSWORD=password,
    )
    args = [
        str(Path(fixture["flyway"]).resolve()),
        f"-configFiles={config}",
        f"-locations=filesystem:{directory}",
        f"-schemas={bundle['schema']}",
        f"-table={bundle['history_table']}",
        "-cleanDisabled=true",
        "-baselineOnMigrate=false",
        "-outOfOrder=false",
        "-placeholderReplacement=false",
        "-validateMigrationNaming=true",
        "-connectRetries=0",
        "-outputType=json",
    ]
    for command in ("migrate", "validate"):
        result = subprocess.run(
            [*args, command],
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=fixture["migration_timeout_seconds"],
            check=False,
        )
        # Never persist the admin password, including when a driver reports a DSN.
        with (root / "flyway.log").open("a") as stream:
            stream.write((result.stdout + result.stderr).replace(password, "[REDACTED]"))
        report = json.loads(result.stdout)
        expected = "success" if command == "migrate" else "validationSuccessful"
        valid = isinstance(report, dict) and report.get(expected) is True
        if result.returncode or not valid:
            raise RuntimeError(f"Flyway {command} failed; see flyway.log")


def wait_ready(connection: dict, password: str, deadline: float) -> None:
    """An open TCP socket is insufficient: authenticate and execute actual SQL."""
    while True:
        try:
            with psycopg.connect(
                host=connection["host"],
                port=connection["port"],
                dbname=connection["database"],
                user="postgres",
                password=password,
                connect_timeout=1,
                options="-c statement_timeout=1000",
            ) as conn:
                conn.execute("SELECT 1")
            return
        except psycopg.OperationalError:
            if time.monotonic() >= deadline:
                raise TimeoutError("PostgreSQL did not become ready") from None
            time.sleep(0.1)


def grant_application(connection: dict, admin: str, password: str, bundle: dict) -> None:
    """Application tests must not silently run as the migration superuser."""
    with psycopg.connect(
        host=connection["host"],
        port=connection["port"],
        dbname=connection["database"],
        user="postgres",
        password=admin,
    ) as conn:
        conn.execute(sql.SQL("CREATE ROLE app LOGIN PASSWORD {}").format(sql.Literal(password)))
        conn.execute(
            sql.SQL("GRANT USAGE ON SCHEMA {} TO app").format(sql.Identifier(bundle["schema"]))
        )
        conn.execute(
            sql.SQL(
                "GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA {} TO app"
            ).format(sql.Identifier(bundle["schema"]))
        )
        conn.execute(
            sql.SQL("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA {} TO app").format(
                sql.Identifier(bundle["schema"])
            )
        )
        conn.execute(
            sql.SQL("REVOKE ALL ON TABLE {}.{} FROM app").format(
                sql.Identifier(bundle["schema"]), sql.Identifier(bundle["history_table"])
            )
        )
        conn.execute(
            sql.SQL("ALTER ROLE app SET search_path TO {}, public").format(
                sql.Identifier(bundle["schema"])
            )
        )
        conn.execute("ALTER ROLE app SET lock_timeout TO '2s'")
        conn.execute("ALTER ROLE app SET statement_timeout TO '10s'")


def load_image(path: Path, client, timeout: int):
    """Allow cold image imports more time while preserving normal API deadlines."""
    previous_timeout = client.api.timeout
    try:
        client.api.timeout = timeout
        with path.open("rb") as archive:
            return client.images.load(archive)[0]
    finally:
        client.api.timeout = previous_timeout


@contextmanager
def postgres(fixture: dict, root: Path, client):
    """Own every resource, including startup and migration failure cleanup."""
    started = time.monotonic()
    timings = {}
    bundle = json.loads(Path(fixture["migrations"]).read_text())
    validate(bundle)
    admin, password = secrets.token_urlsafe(24), secrets.token_urlsafe(24)
    identity = "bazel-postgres-" + uuid4().hex
    network = client.networks.create(identity, labels={LABEL: identity})
    container = None
    try:
        image = load_image(Path(fixture["image"]), client, fixture["image_load_timeout_seconds"])
        timings["image_loaded_seconds"] = time.monotonic() - started
        container = client.containers.run(
            image.id,
            name=identity,
            detach=True,
            environment={"POSTGRES_PASSWORD": admin, "POSTGRES_DB": fixture["database"]},
            labels={LABEL: identity},
            network=network.id,
            ports={"5432/tcp": ("127.0.0.1", None)},
            tmpfs={"/var/lib/postgresql/data": "rw"},
            mem_limit="2g",
            nano_cpus=2_000_000_000,
        )
        container.reload()
        port = int(container.attrs["NetworkSettings"]["Ports"]["5432/tcp"][0]["HostPort"])
        connection = dict(
            format_version=1,
            host="127.0.0.1",
            port=port,
            database=fixture["database"],
            user="app",
            password=password,
            sslmode="disable",
        )
        wait_ready(connection, admin, time.monotonic() + fixture["startup_timeout_seconds"])
        timings["ready_seconds"] = time.monotonic() - started
        run_flyway(fixture, bundle, connection, admin, root)
        grant_application(connection, admin, password, bundle)
        timings["migrated_seconds"] = time.monotonic() - started
        host_file = root / "connection.json"
        private_json(host_file, connection)
        network_file = root / "container-connection.json"
        private_json(network_file, dict(connection, host=identity, port=5432))
        yield {
            "POSTGRES_CONNECTION_FILE": str(host_file),
            "POSTGRES_CONTAINER_CONNECTION_FILE": str(network_file),
            "POSTGRES_TEST_NETWORK": network.name,
            "POSTGRES_TEST_LABEL": identity,
        }
    finally:
        cleanup_started = time.monotonic()
        try:
            if container is not None:
                logs = container.logs().replace(admin.encode(), b"[REDACTED]")
                (root / "postgresql.log").write_bytes(
                    logs.replace(password.encode(), b"[REDACTED]")
                )
        finally:
            try:
                # Include any service resources created by helpers with the same label.
                for resource in client.containers.list(
                    all=True, filters={"label": f"{LABEL}={identity}"}
                ):
                    resource.remove(force=True, v=True)
            finally:
                try:
                    network.remove()
                finally:
                    timings["cleanup_seconds"] = time.monotonic() - cleanup_started
                    (root / "lifecycle.log").write_text(
                        json.dumps(dict(run_id=identity, **timings))
                    )


def stop_process(process, signum=signal.SIGINT) -> None:
    """Stop and reap a child without detaching it from Bazel's process group."""
    if process.poll() is None:
        process.send_signal(signum)  # SIGINT requests PostgreSQL fast shutdown.
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


@contextmanager
def native_postgres(fixture: dict, root: Path):
    """Run PostgreSQL as a sandbox child with all state in the test directory."""
    started = time.monotonic()
    timings = {}
    bundle = json.loads(Path(fixture["migrations"]).read_text())
    validate(bundle)
    admin, password = secrets.token_urlsafe(24), secrets.token_urlsafe(24)
    data = root / "data"
    password_file = root / "admin-password"
    connection_file = root / "connection.json"
    process = None
    env = {key: value for key, value in os.environ.items() if not key.startswith("PG")}
    env.update(HOME=str(root), TMPDIR=str(root), LC_ALL="C")
    try:
        with os.fdopen(
            os.open(password_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w"
        ) as stream:
            stream.write(admin)
        with (root / "initdb.log").open("w") as log:
            subprocess.run(
                [
                    str(Path(fixture["initdb"]).absolute()),
                    "-D",
                    str(data),
                    "-U",
                    "postgres",
                    "--auth=scram-sha-256",
                    "--encoding=UTF8",
                    "--locale=C",
                    "--no-instructions",
                    f"--pwfile={password_file}",
                ],
                env=env,
                stdout=log,
                stderr=subprocess.STDOUT,
                timeout=fixture["startup_timeout_seconds"],
                check=True,
            )
        password_file.unlink()
        with socket.socket() as reservation:
            reservation.bind(("127.0.0.1", 0))
            port = reservation.getsockname()[1]
        connection = dict(
            format_version=1,
            host="127.0.0.1",
            port=port,
            database="postgres",
            user="app",
            password=password,
            sslmode="disable",
        )
        with (root / "postgresql.log").open("w") as log:
            process = subprocess.Popen(
                [
                    str(Path(fixture["postgres"]).absolute()),
                    "-D",
                    str(data),
                    "-h",
                    "127.0.0.1",
                    "-p",
                    str(port),
                    "-c",
                    "unix_socket_directories=",
                    "-c",
                    "max_connections=20",
                    "-c",
                    "shared_buffers=16MB",
                    "-c",
                    "statement_timeout=10000",
                ],
                env=env,
                stdout=log,
                stderr=subprocess.STDOUT,
            )
        timings.update(pid=process.pid, port=port)
        wait_ready(connection, admin, time.monotonic() + fixture["startup_timeout_seconds"])
        timings["ready_seconds"] = time.monotonic() - started
        with psycopg.connect(
            host=connection["host"],
            port=port,
            dbname="postgres",
            user="postgres",
            password=admin,
            autocommit=True,
            connect_timeout=1,
        ) as conn:
            conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(fixture["database"])))
        connection["database"] = fixture["database"]
        run_flyway(fixture, bundle, connection, admin, root)
        grant_application(connection, admin, password, bundle)
        timings["migrated_seconds"] = time.monotonic() - started
        private_json(connection_file, connection)
        yield {"POSTGRES_CONNECTION_FILE": str(connection_file)}
    finally:
        cleanup_started = time.monotonic()
        try:
            if process is not None:
                stop_process(process)
                timings["exit_code"] = process.returncode
        finally:
            password_file.unlink(missing_ok=True)
            connection_file.unlink(missing_ok=True)
            shutil.rmtree(data, ignore_errors=True)
            for path in root.glob("*.log"):
                path.write_text(
                    path.read_text().replace(admin, "[REDACTED]").replace(password, "[REDACTED]")
                )
            timings["cleanup_seconds"] = time.monotonic() - cleanup_started
            (root / "lifecycle.log").write_text(json.dumps(timings))


def run(fixture: dict, command: list[str]) -> int:
    """Run coverage after fixture setup and preserve diagnostics before teardown."""
    output = Path(os.environ["TEST_UNDECLARED_OUTPUTS_DIR"])
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=os.environ["TEST_TMPDIR"]) as directory:
        root = Path(directory)
        try:
            with native_postgres(fixture, root) as env:
                with subprocess.Popen(command, env=dict(os.environ, **env)) as child:
                    try:
                        return child.wait()
                    finally:
                        stop_process(child, signal.SIGTERM)
        finally:
            for path in root.glob("*.log"):
                shutil.copyfile(path, output / path.name)


def interrupted(_signum, _frame):
    """Unwind the fixture on test cancellation, including migration failures."""
    raise KeyboardInterrupt


def dev(fixture: dict, client) -> int:
    """Keep a disposable migrated DB alive while the developer runs services."""
    with tempfile.TemporaryDirectory(prefix="bazel-postgres-dev-") as directory:
        with postgres(fixture, Path(directory), client) as env:
            print(
                f"PostgreSQL ready. Set POSTGRES_CONNECTION_FILE={env['POSTGRES_CONNECTION_FILE']}",
                flush=True,
            )
            print(f"Recovery label: {env['POSTGRES_TEST_LABEL']}", flush=True)
            signal.pause()
    return 0


def cleanup(identity: str, client) -> None:
    """Recover only explicitly identified resources owned by this fixture runner."""
    if not re.fullmatch(r"bazel-postgres-[0-9a-f]{32}", identity):
        raise ValueError("Expected a complete bazel-postgres-<uuid> recovery label")
    filters = {"label": f"{LABEL}={identity}"}
    for container in client.containers.list(all=True, filters=filters):
        container.remove(force=True, v=True)
    for network in client.networks.list(filters=filters):
        network.remove()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path)
    parser.add_argument("--dev", action="store_true")
    parser.add_argument("--image", type=Path)
    parser.add_argument("--cleanup-run")
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:]  # The launcher's explicit '--' delimiter.
    if not args.cleanup_run and (args.fixture is None or (not args.dev and not command)):
        parser.error("supply --fixture and either --dev or a coverage executable after --")
    signal.signal(signal.SIGTERM, interrupted)
    try:
        if not args.cleanup_run and not args.dev:
            return run(json.loads(args.fixture.read_text()), command)
        with closing(docker.from_env(timeout=10)) as client:
            if args.cleanup_run:
                cleanup(args.cleanup_run, client)
                return 0
            fixture = json.loads(args.fixture.read_text())
            fixture.update(image=str(args.image), image_load_timeout_seconds=120)
            return dev(fixture, client)
    except (
        DockerException,
        psycopg.Error,
        OSError,
        ValueError,
        RuntimeError,
        subprocess.TimeoutExpired,
        subprocess.CalledProcessError,
    ) as error:
        print(f"PostgreSQL fixture failed: {type(error).__name__}; see test logs", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 0 if args.dev else 130


if __name__ == "__main__":
    sys.exit(main())
