"""The local LLM servers JobRadar talks to: Gemini Web (your cookie) and DeepSeek Web (your
login). Both speak the OpenAI API on 127.0.0.1, so no provider key is needed.

`jobradar llm setup` clones them and writes their settings, `jobradar llm start` runs them,
`jobradar llm models` asks what they can answer with and `jobradar llm use` points
config.yaml at one of those models.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import signal
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

import httpx

from jobradar.sources.boards.config_edit import _KEY, _block, _find, _parse

log = logging.getLogger(__name__)


class LocalLLMError(Exception):
    """Something needs the owner's hand; the message says what to do."""


@dataclass(frozen=True)
class Service:
    """One local server: where it comes from, how it runs, where it answers."""

    name: str
    repo: str
    directory: str
    base_url: str
    command: tuple[str, ...]
    env: dict[str, str] = field(default_factory=dict)
    login_file: str | None = None  # the file the login writes, when the server needs one


SERVICES: dict[str, Service] = {
    "gemini-web": Service(
        name="gemini-web",
        repo="https://github.com/ntthanh2603/gemini-web-to-api",
        directory="gemini-web-to-api",
        base_url="http://127.0.0.1:4981/openai/v1",
        command=("bin/gemini-web-to-api",),
    ),
    "deepseek-web": Service(
        name="deepseek-web",
        repo="https://github.com/atharvotech/FreeDeepseekAPI-EN",
        directory="FreeDeepseekAPI-EN",
        base_url="http://127.0.0.1:9655/v1",
        command=("node", "server.js"),
        env={"NON_INTERACTIVE": "1", "SKIP_ACCOUNT_MENU": "1"},
        login_file="deepseek-auth.json",
    ),
}

COOKIE_NAMES = ("__Secure-1PSID", "__Secure-1PSIDTS")


def services_dir() -> Path:
    """Where the servers live. JOBRADAR_SERVICES_DIR wins, else <the checkout>/services."""
    override = os.environ.get("JOBRADAR_SERVICES_DIR")
    if override:
        return Path(override).expanduser()
    return Path(__file__).resolve().parents[2] / "services"


def runtime_dir() -> Path:
    """Where the pid files and logs go. JOBRADAR_LLM_RUNTIME_DIR wins."""
    override = os.environ.get("JOBRADAR_LLM_RUNTIME_DIR")
    if override:
        return Path(override).expanduser()
    return Path(__file__).resolve().parents[2] / "data" / "local-llm"


def cookie_header(export: Path) -> str:
    """Turn a browser cookie export (the JSON list an extension gives) into a Cookie header."""
    try:
        data = json.loads(export.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise LocalLLMError(f"can't read the cookie file {export}: {e}") from e
    cookies = data if isinstance(data, list) else data.get("cookies", [])
    pairs = []
    for cookie in cookies:
        if not isinstance(cookie, dict):
            continue
        name = str(cookie.get("name", "")).strip()
        value = str(cookie.get("value", ""))
        if name and value:
            pairs.append(f"{name}={value}")
    header = "; ".join(pairs)
    missing = [name for name in COOKIE_NAMES if f"{name}=" not in header]
    if missing:
        raise LocalLLMError(
            f"{export} has no {', '.join(missing)}. Export the cookies of a signed-in "
            "gemini.google.com tab: the file needs "
            f"{' and '.join(COOKIE_NAMES)}."
        )
    return header


def gemini_env(header: str) -> str:
    """The .env the Gemini Web server reads."""
    safe = header.replace("\\", "\\\\").replace('"', '\\"')
    return (
        "PORT=4981\n"
        "LOG_LEVEL=info\n"
        "APP_ENV=production\n"
        "RATE_LIMIT_ENABLED=true\n"
        "RATE_LIMIT_WINDOW_MS=60000\n"
        "RATE_LIMIT_MAX_REQUESTS=30\n"
        f'GEMINI_COOKIES="{safe}"\n'
        "GEMINI_AUTH_USER=\n"
        "GEMINI_REFRESH_INTERVAL=1440\n"
        "GEMINI_MAX_RETRIES=3\n"
        "GEMINI_TEMPORARY=false\n"
    )


def _run(command: list[str], what: str, cwd: Path | None = None) -> None:
    try:
        subprocess.run(  # noqa: S603 (our own commands: git, go)
            command, cwd=cwd, check=True, capture_output=True, text=True
        )
    except FileNotFoundError as e:
        raise LocalLLMError(f"{command[0]} is not installed, so I can't {what}.") from e
    except subprocess.CalledProcessError as e:
        detail = (e.stderr or e.stdout or "").strip().splitlines()
        raise LocalLLMError(f"couldn't {what}: {detail[-1] if detail else e}") from e


def setup(cookies: Path | None = None) -> list[str]:
    """Clone the servers, build the Gemini Web one and give it the cookie."""
    done: list[str] = []
    root = services_dir()
    root.mkdir(parents=True, exist_ok=True)
    for service in SERVICES.values():
        path = root / service.directory
        if not path.is_dir():
            _run(["git", "clone", "--depth", "1", service.repo, str(path)], f"clone {service.name}")
            done.append(f"cloned {service.name}")
    gemini = root / "gemini-web-to-api"
    if cookies is not None:
        (gemini / ".env").write_text(gemini_env(cookie_header(cookies)), encoding="utf-8")
        done.append("wrote the Gemini Web cookie")
    binary = gemini / "bin" / "gemini-web-to-api"
    if not binary.exists():
        if shutil.which("go") is None:
            raise LocalLLMError(
                "Go is needed to build the Gemini Web server. Install Go, or run "
                "'docker compose up -d --build' in services/gemini-web-to-api."
            )
        _run(
            ["go", "build", "-o", str(binary), "./cmd/server"],
            "build the Gemini Web server",
            gemini,
        )
        done.append("built the Gemini Web server")
    return done


def pid_file(service: Service) -> Path:
    return runtime_dir() / f"{service.name}.pid"


def log_file(service: Service) -> Path:
    return runtime_dir() / f"{service.name}.log"


def running_pid(service: Service) -> int | None:
    """The pid of the server, when it is still alive."""
    path = pid_file(service)
    if not path.is_file():
        return None
    try:
        pid = int(path.read_text(encoding="utf-8").strip())
    except ValueError:
        return None
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return None
    except PermissionError:
        return pid  # it runs, it just isn't ours
    return pid


def logged_in(service: Service) -> bool:
    """Whether the server has the login it needs (a server without one is always ready)."""
    if service.login_file is None:
        return True
    return (services_dir() / service.directory / service.login_file).is_file()


def service_for(base_url: str) -> Service | None:
    """The service that answers at this address, when it is one of ours."""
    for service in SERVICES.values():
        if service.base_url == base_url.rstrip("/"):
            return service
    return None


def endpoint_models(base_url: str) -> list[str] | None:
    """The models an OpenAI-compatible server offers, or None when it doesn't answer."""
    try:
        response = httpx.get(f"{base_url.rstrip('/')}/models", timeout=5)
        response.raise_for_status()
        data = response.json()
    except (httpx.HTTPError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    items = data.get("data")
    if not isinstance(items, list):
        return []
    return [str(m.get("id")) for m in items if isinstance(m, dict)]


def ask(base_url: str, model: str, prompt: str, timeout: float = 90.0) -> str:
    """One chat completion against an OpenAI-compatible server."""
    response = httpx.post(
        f"{base_url.rstrip('/')}/chat/completions",
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"},
        },
        timeout=timeout,
    )
    response.raise_for_status()
    data = response.json()
    return str(data["choices"][0]["message"]["content"])


def start(service: Service, wait: float = 30.0) -> str:
    """Start the server if it isn't running; returns what happened."""
    if running_pid(service) is not None:
        return f"{service.name} is already running"
    if endpoint_models(service.base_url) is not None:
        return f"{service.name} is already running"  # started by hand, not by us
    path = services_dir() / service.directory
    if not path.is_dir():
        raise LocalLLMError(f"{service.name} isn't installed: run `jobradar llm setup`")
    if not logged_in(service):
        raise LocalLLMError(f"{service.name} isn't logged in yet: run `jobradar llm login`")
    runtime_dir().mkdir(parents=True, exist_ok=True)
    env = {**os.environ, **service.env}
    command = list(service.command)
    if "/" not in command[0]:
        found = shutil.which(command[0])
        if found is None:
            raise LocalLLMError(f"{command[0]} is not installed, so {service.name} can't run.")
        command[0] = found
    else:
        command[0] = str(path / command[0])  # a path is read from the parent's directory
    if not Path(command[0]).is_file():
        raise LocalLLMError(f"{command[0]} is missing: run `jobradar llm setup`")
    with log_file(service).open("ab") as log:
        try:
            process = subprocess.Popen(  # noqa: S603 (the command is ours, not user input)
                command,
                cwd=path,
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=log,
                start_new_session=True,  # outlives the shell that started it
            )
        except OSError as e:
            raise LocalLLMError(f"couldn't start {service.name}: {e}") from e
    pid_file(service).write_text(str(process.pid), encoding="utf-8")
    deadline = time.monotonic() + wait
    while time.monotonic() < deadline:
        if endpoint_models(service.base_url) is not None:
            return f"{service.name} is running on {service.base_url}"
        time.sleep(0.5)
    raise LocalLLMError(
        f"{service.name} didn't answer within {int(wait)}s. See {log_file(service)}."
    )


def stop(service: Service) -> str:
    """Stop the server, if it is running."""
    pid = running_pid(service)
    if pid is None:
        pid_file(service).unlink(missing_ok=True)
        return f"{service.name} isn't running"
    os.kill(pid, signal.SIGTERM)
    for _ in range(40):
        if running_pid(service) is None:
            break
        time.sleep(0.25)
    else:
        os.kill(pid, signal.SIGKILL)
    pid_file(service).unlink(missing_ok=True)
    return f"{service.name} stopped"


def ensure_running(base_urls: list[str]) -> list[str]:
    """Start the servers behind these addresses when they are ours and not up yet."""
    started: list[str] = []
    for base_url in base_urls:
        service = service_for(base_url)
        if service is None:
            continue
        try:
            message = start(service)
        except LocalLLMError as e:
            log.warning("local LLM server %s isn't running: %s", service.name, e)
            continue
        if "already running" not in message:
            started.append(message)
    return started


def set_models(text: str, extract: str | None = None, writer: str | None = None) -> str:
    """Point config.yaml at a model, keeping the comments and the layout."""
    lines = text.splitlines()
    section = _find(lines, "llm", 0, len(lines), -1)
    if section is None:
        raise LocalLLMError("config.yaml has no `llm:` section")
    end = _block(lines, section)
    indent = _parse(lines[section]).indent
    for key, value in (("extract_model", extract), ("writer_model", writer)):
        if value is None:
            continue
        index = _find(lines, key, section + 1, end, indent)
        if index is None:
            lines.insert(end, f"{' ' * (indent + 2)}{key}: {value}")
            end += 1
            continue
        match = _KEY.match(lines[index])
        if match is None:
            raise LocalLLMError(f"`{key}:` in config.yaml can't be edited by me; change it by hand")
        old_indent, old_key, old_value, comment = match.groups()
        shown = json.dumps(value) if old_value.startswith(('"', "'")) else value
        gap = lines[index][match.end(3) : match.start(4)] if comment else ""
        tail = f"{gap}{comment}" if comment else ""
        lines[index] = f"{old_indent}{old_key}: {shown}{tail}"
    return "\n".join(lines) + "\n"
