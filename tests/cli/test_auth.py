"""`i18n-ai auth`: a provider's key saved in the keyring (in memory here), shown by where it comes
from and never by its value, and removed."""

import re
from collections.abc import Callable
from pathlib import Path

import keyring
import pytest
from keyring.backends import fail
from typer.testing import CliRunner

from i18n_ai.cli import interactive
from i18n_ai.cli.app import app
from support.fakes import MemoryKeyring, ScriptedPrompter

runner = CliRunner()
ANSI = re.compile(r"\x1b\[[0-9;]*m")
OPENAI = ("i18n-ai", "OPENAI_API_KEY")

Terminal = Callable[..., ScriptedPrompter]


@pytest.fixture(autouse=True)
def isolated(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """In an empty project, with no provider key from the developer's machine."""
    monkeypatch.chdir(tmp_path)
    for key in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY"):
        # set first, so that what the .env sets is undone too
        monkeypatch.setenv(key, "")
        monkeypatch.delenv(key)
    monkeypatch.setenv("COLUMNS", "200")


@pytest.fixture
def terminal(monkeypatch: pytest.MonkeyPatch) -> Terminal:
    monkeypatch.setattr(interactive, "is_interactive", lambda no_input: not no_input)

    def script(*answers: object) -> ScriptedPrompter:
        prompter = ScriptedPrompter(*answers)
        monkeypatch.setattr(interactive, "prompter", lambda: prompter)
        return prompter

    return script


def invoke(*args: str, input: str | None = None) -> tuple[int, str]:
    result = runner.invoke(app, list(args), input=input)
    return result.exit_code, ANSI.sub("", result.output)


def test_login_reads_a_piped_key(vault: MemoryKeyring) -> None:
    code, output = invoke("auth", "login", "openai", input="sk-piped\n")

    assert code == 0, output
    assert vault.passwords == {OPENAI: "sk-piped"}
    assert "OPENAI_API_KEY saved in the system keyring (fakes MemoryKeyring) for openai" in output
    assert "sk-piped" not in output


def test_login_asks_for_the_provider_and_the_key(terminal: Terminal, vault: MemoryKeyring) -> None:
    prompter = terminal("anthropic", "sk-typed")

    code, output = invoke("auth", "login")

    assert code == 0, output
    assert [(question.kind, question.message) for question in prompter.asked] == [
        ("select", "Which provider's key to save?"),
        ("secret", "ANTHROPIC_API_KEY (hidden)"),
    ]
    assert vault.passwords == {("i18n-ai", "ANTHROPIC_API_KEY"): "sk-typed"}


def test_login_tells_that_the_environment_wins(
    vault: MemoryKeyring, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-env")

    code, output = invoke("auth", "login", "openai", input="sk-new\n")

    assert code == 0, output
    assert vault.passwords == {OPENAI: "sk-new"}
    assert "OPENAI_API_KEY is also set in the environment, which wins over the keyring" in output


@pytest.mark.parametrize(
    ("provider", "message"),
    [
        ("ollama", "the ollama provider takes no API key"),
        ("nope", "cannot tell the provider of 'nope'"),
    ],
)
def test_login_refuses_a_provider_without_a_key(
    provider: str, message: str, vault: MemoryKeyring
) -> None:
    code, output = invoke("auth", "login", provider, input="sk\n")

    assert code == 2
    assert message in output
    assert vault.passwords == {}


def test_login_refuses_an_empty_key(vault: MemoryKeyring) -> None:
    code, output = invoke("auth", "login", "openai", input="\n")

    assert code == 2
    assert "no OPENAI_API_KEY given; nothing saved" in output
    assert vault.passwords == {}


def test_login_without_a_keyring_writes_nothing(tmp_path: Path) -> None:
    keyring.set_keyring(fail.Keyring())

    code, output = invoke("auth", "login", "openai", input="sk\n")

    assert code == 2
    assert "no system keyring is available here" in output
    assert list(tmp_path.iterdir()) == []


def test_login_needs_the_provider_off_a_terminal() -> None:
    code, output = invoke("auth", "login", input="sk\n")

    assert code == 2
    assert "Missing argument 'PROVIDER'" in output


def test_status_tells_where_each_key_comes_from(
    vault: MemoryKeyring, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    vault.set_password("i18n-ai", "OPENAI_API_KEY", "sk-keyring")
    vault.set_password("i18n-ai", "GROQ_API_KEY", "gsk-keyring")
    (tmp_path / ".env").write_text("ANTHROPIC_API_KEY=sk-dotenv\n")
    monkeypatch.setenv("MISTRAL_API_KEY", "sk-env")

    code, output = invoke("auth", "status")

    assert code == 0, output
    assert "System keyring: fakes MemoryKeyring" in output
    rows = {line.split()[1]: line for line in output.splitlines() if "_API_KEY" in line}
    assert "✓ keyring" in rows["openai"]
    assert "✓ .env" in rows["anthropic"]
    assert "✓ environment" in rows["mistralai"]
    assert "-" in rows["cohere"]
    assert "ollama" not in rows
    assert "-keyring" not in output
    assert "sk-" not in output


def test_status_without_a_keyring() -> None:
    keyring.set_keyring(fail.Keyring())

    code, output = invoke("auth", "status")

    assert code == 0
    assert "No system keyring here" in output


def test_logout_removes_the_key(vault: MemoryKeyring) -> None:
    vault.set_password(*OPENAI, "sk-saved")

    code, output = invoke("auth", "logout", "openai")

    assert code == 0, output
    assert "OPENAI_API_KEY removed from the system keyring" in output
    assert vault.passwords == {}

    code, output = invoke("auth", "logout", "openai")
    assert code == 0
    assert "No OPENAI_API_KEY in the system keyring" in output


def test_logout_tells_the_key_left_in_the_environment(
    vault: MemoryKeyring, monkeypatch: pytest.MonkeyPatch
) -> None:
    vault.set_password(*OPENAI, "sk-saved")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-env")

    code, output = invoke("auth", "logout", "openai")

    assert code == 0, output
    assert "OPENAI_API_KEY is still set in the environment" in output


def test_logout_all(vault: MemoryKeyring) -> None:
    vault.set_password(*OPENAI, "sk-1")
    vault.set_password("i18n-ai", "GROQ_API_KEY", "gsk-2")
    vault.set_password("someone-else", "OPENAI_API_KEY", "theirs")

    code, output = invoke("auth", "logout", "--all")

    assert code == 0, output
    assert "GROQ_API_KEY removed" in output
    assert "OPENAI_API_KEY removed" in output
    assert vault.passwords == {("someone-else", "OPENAI_API_KEY"): "theirs"}

    code, output = invoke("auth", "logout", "--all")
    assert "No key was saved in the system keyring" in output


def test_logout_offers_the_saved_keys(terminal: Terminal, vault: MemoryKeyring) -> None:
    vault.set_password("i18n-ai", "GROQ_API_KEY", "gsk")
    prompter = terminal("groq")

    code, output = invoke("auth", "logout")

    assert code == 0, output
    assert prompter.asked[0].choices == ["groq"]
    assert vault.passwords == {}

    terminal()
    code, output = invoke("auth", "logout")
    assert "No key is saved in the system keyring" in output


def test_providers_list_tells_the_source(vault: MemoryKeyring) -> None:
    vault.set_password(*OPENAI, "sk-saved")

    code, output = invoke("providers", "list")

    assert code == 0
    assert "✓ OPENAI_API_KEY (keyring)" in output
