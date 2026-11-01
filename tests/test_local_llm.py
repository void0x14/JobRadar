import json
from pathlib import Path

import pytest

from jobradar.local_llm import (
    LocalLLMError,
    cookie_header,
    gemini_env,
    patch_loopback,
    set_fallback_models,
    set_models,
)

COOKIES = [
    {"name": "__Secure-1PSID", "value": "psid", "domain": ".google.com"},
    {"name": "__Secure-1PSIDTS", "value": "psidts", "domain": ".google.com"},
    {"name": "NID", "value": "nid", "domain": ".google.com"},
]

CONFIG = """llm:
  extract_model: "gemini/gemini-flash-lite-latest"  # extraction + scoring
  writer_model: "gemini/gemini-flash-latest"      # longer job summaries
  daily_budget_inr: 15
"""


def write_cookies(tmp_path: Path, cookies: list[dict[str, str]]) -> Path:
    path = tmp_path / "cookies.json"
    path.write_text(json.dumps(cookies))
    return path


def test_cookie_header_from_a_browser_export(tmp_path: Path) -> None:
    header = cookie_header(write_cookies(tmp_path, COOKIES))
    assert header == "__Secure-1PSID=psid; __Secure-1PSIDTS=psidts; NID=nid"


def test_cookie_header_says_which_cookie_is_missing(tmp_path: Path) -> None:
    path = write_cookies(tmp_path, [{"name": "NID", "value": "nid"}])
    with pytest.raises(LocalLLMError, match="__Secure-1PSID"):
        cookie_header(path)


def test_a_cookie_file_that_is_not_json_is_reported(tmp_path: Path) -> None:
    path = tmp_path / "cookies.json"
    path.write_text("not json")
    with pytest.raises(LocalLLMError, match="can't read the cookie file"):
        cookie_header(path)


def test_gemini_env_carries_the_cookie() -> None:
    env = gemini_env("__Secure-1PSID=psid; __Secure-1PSIDTS=psidts")
    assert 'GEMINI_COOKIES="__Secure-1PSID=psid; __Secure-1PSIDTS=psidts"' in env
    assert "GEMINI_AUTH_USER=" in env


def test_set_models_keeps_the_comments() -> None:
    after = set_models(CONFIG, extract="gemini-web/gemini-auto", writer="gemini-web/gemini-auto")
    assert 'extract_model: "gemini-web/gemini-auto"  # extraction + scoring' in after
    assert 'writer_model: "gemini-web/gemini-auto"      # longer job summaries' in after


def test_set_models_adds_a_line_that_is_missing() -> None:
    after = set_models("llm:\n  daily_budget_inr: 15\n", extract="gemini-web/gemini-auto")
    assert "  extract_model: gemini-web/gemini-auto" in after
    assert "daily_budget_inr: 15" in after


def test_set_models_leaves_the_other_model_alone() -> None:
    after = set_models(CONFIG, extract="gemini-web/gemini-auto")
    assert "gemini-web/gemini-auto" in after
    assert 'writer_model: "gemini/gemini-flash-latest"' in after


def test_set_models_needs_an_llm_section() -> None:
    with pytest.raises(LocalLLMError, match="llm:"):
        set_models("scoring:\n  hide_below: 40\n", extract="gemini-web/gemini-auto")


def test_the_gemini_server_is_bound_to_localhost(tmp_path: Path) -> None:
    server = tmp_path / "internal" / "server" / "server.go"
    server.parent.mkdir(parents=True)
    server.write_text('\taddress := fmt.Sprintf(":%s", port)\n')
    assert patch_loopback(tmp_path) is True
    assert 'fmt.Sprintf("127.0.0.1:%s", port)' in server.read_text()
    assert patch_loopback(tmp_path) is False  # only once


def test_a_server_without_the_file_is_left_alone(tmp_path: Path) -> None:
    assert patch_loopback(tmp_path) is False


def test_set_fallback_models_replaces_a_one_line_chain() -> None:
    text = 'llm:\n  fallback_models: ["old/model"]  # the chain\n  daily_budget_inr: 15\n'
    after = set_fallback_models(text, ["deepseek-web/deepseek-chat"])
    assert 'fallback_models: ["deepseek-web/deepseek-chat"]  # the chain' in after


def test_set_fallback_models_replaces_a_list_written_under_the_key() -> None:
    text = "llm:\n  fallback_models:\n    - old/model\n  daily_budget_inr: 15\n"
    after = set_fallback_models(text, ["deepseek-web/deepseek-chat"])
    assert '    - "deepseek-web/deepseek-chat"' in after
    assert "old/model" not in after


def test_set_fallback_models_adds_the_line_when_it_is_missing() -> None:
    after = set_fallback_models("llm:\n  daily_budget_inr: 15\n", ["deepseek-web/deepseek-chat"])
    assert '  fallback_models: ["deepseek-web/deepseek-chat"]' in after


def test_set_fallback_models_can_clear_the_chain() -> None:
    after = set_fallback_models(CONFIG, [])
    assert "fallback_models: []" in after


def test_set_fallback_models_needs_an_llm_section() -> None:
    with pytest.raises(LocalLLMError, match="llm:"):
        set_fallback_models("scoring:\n  hide_below: 40\n", ["deepseek-web/deepseek-chat"])
