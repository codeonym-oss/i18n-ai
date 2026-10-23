"""The locale file formats: what is read, and a target written the way its source is."""

import json
from pathlib import Path, PurePosixPath
from typing import Any

import pytest

from i18n_ai.domain.exports.locale import SourceFile
from i18n_ai.infra.adapters.filesystem.formats import FORMATS, format_of, load_document
from i18n_ai.infra.adapters.filesystem.formats.arb_format import ArbFormat
from i18n_ai.infra.adapters.filesystem.formats.yaml_format import YamlFormat

yaml = YamlFormat()
arb = ArbFormat()

ARB = """\
{
    "@@locale": "en",
    "@@x-team": "web",
    "title": "Notes",
    "@title": {"description": "The app's name"},
    "count": "{n, plural, one{# note} other{# notes}}",
    "@count": {"placeholders": {"n": {"type": "int"}}}
}
"""

SOURCE = """\
# The shop's messages
shop:
  title: "Acme"   # shown in the tab
  empty: 'Nothing here'
  intro: |
    Welcome.
    Take a look.
  item_one: One item
  item_other: Many items
  limit: 0x10
  tags:
    - new
    - sale
"""


def source(tmp_path: Path, text: str, name: str = "en.yml", key: str | None = None) -> SourceFile:
    path = tmp_path / name
    path.write_bytes(text.encode())
    return SourceFile(PurePosixPath(name), path, None, root_key=key)


def translated(text: str) -> str:
    return f"<{text}>"


def test_yaml_is_read_as_plain_values(tmp_path: Path) -> None:
    content = yaml.read(source(tmp_path, SOURCE).path)

    assert content["shop"]["title"] == "Acme"
    assert type(content["shop"]["title"]) is str
    assert content["shop"]["intro"] == "Welcome.\nTake a look.\n"
    assert content["shop"]["limit"] == 16
    assert content["shop"]["tags"] == ["new", "sale"]


def test_yaml_1_2_keeps_no_a_key(tmp_path: Path) -> None:
    content = yaml.read(source(tmp_path, "no:\n  yes: Ja\n1: one\n").path)

    assert content == {"no": {"yes": "Ja"}, "1": "one"}


def test_a_target_keeps_the_source_comments_order_and_quoting(tmp_path: Path) -> None:
    like = source(tmp_path, SOURCE)
    content: dict[str, Any] = {
        "shop": {
            "title": "Acmé",
            "empty": "Rien ici",
            "intro": "Bienvenue.\nRegardez.\n",
            "item_one": "Un article",
            "item_many": "Beaucoup d'articles",
            "item_other": "Des articles",
            "limit": 16,
            "tags": ["nouveau", "soldes"],
        }
    }

    yaml.write(tmp_path / "fr.yml", content, like, None)

    assert (tmp_path / "fr.yml").read_text(encoding="utf-8") == (
        "# The shop's messages\n"
        "shop:\n"
        '  title: "Acmé"   # shown in the tab\n'
        "  empty: 'Rien ici'\n"
        "  intro: |\n"
        "    Bienvenue.\n"
        "    Regardez.\n"
        "  item_one: Un article\n"
        "  item_many: Beaucoup d'articles\n"
        "  item_other: Des articles\n"
        "  limit: 0x10\n"
        "  tags:\n"
        "    - nouveau\n"
        "    - soldes\n"
    )


def test_a_key_the_target_drops_is_gone(tmp_path: Path) -> None:
    like = source(tmp_path, "a: A\nb: B\n")

    yaml.write(tmp_path / "ja.yml", {"b": "ビー"}, like, None)

    assert (tmp_path / "ja.yml").read_text(encoding="utf-8") == "b: ビー\n"


def test_a_rooted_file_is_rooted_at_its_locale(tmp_path: Path) -> None:
    like = source(tmp_path, "# Rails' locales\n\nen:\n  hello: Hello\n", key="en")

    yaml.write(tmp_path / "fr.yml", {"hello": "Bonjour"}, like, "fr")

    assert (tmp_path / "fr.yml").read_text() == "# Rails' locales\n\nfr:\n  hello: Bonjour\n"


def test_an_existing_target_keeps_its_other_keys(tmp_path: Path) -> None:
    like = source(tmp_path, "en:\n  hello: Hello\n", key="en")
    (tmp_path / "fr.yml").write_text("fr:\n  hello: Salut\nfr-CA:\n  hello: Allo\n")

    yaml.write(tmp_path / "fr.yml", {"hello": "Bonjour"}, like, "fr")

    assert (tmp_path / "fr.yml").read_text() == "fr:\n  hello: Bonjour\nfr-CA:\n  hello: Allo\n"


def test_a_bundle_takes_the_new_locale_last(tmp_path: Path) -> None:
    like = source(tmp_path, "en:\n  hello: Hello # greeting\n", "i18n.yml", key="en")

    yaml.write(like.path, {"hello": "Hallo"}, like, "de")

    assert (
        like.path.read_text() == "en:\n  hello: Hello # greeting\nde:\n  hello: Hallo # greeting\n"
    )


@pytest.mark.parametrize(
    ("text", "written"),
    [
        ("a:\n    b: B\n    c:\n    - x\n", "a:\n    b: <B>\n    c:\n    - <x>\n"),
        ("a:\n  c:\n    - x\n", "a:\n  c:\n    - <x>\n"),
        ("---\na: A\n", "---\na: <A>\n"),
    ],
)
def test_the_indent_and_the_start_are_kept(tmp_path: Path, text: str, written: str) -> None:
    like = source(tmp_path, text)
    content = _map(yaml.read(like.path), translated)

    yaml.write(tmp_path / "fr.yml", content, like, None)

    assert (tmp_path / "fr.yml").read_text() == written


@pytest.mark.parametrize("name", ["en.json", "en.yml"])
def test_the_line_endings_are_kept(tmp_path: Path, name: str) -> None:
    text = '{\r\n  "a": "A"\r\n}\r\n' if name.endswith(".json") else "a: A\r\n"
    like = source(tmp_path, text, name)
    adapter = format_of(like.path)
    assert adapter is not None

    adapter.write(tmp_path / f"fr{like.path.suffix}", {"a": "B"}, like, None)

    written = (tmp_path / f"fr{like.path.suffix}").read_bytes()
    assert written.count(b"\r\n") == text.count("\r\n")
    assert b"\n" not in written.replace(b"\r\n", b"")


def test_invalid_yaml_says_why(tmp_path: Path) -> None:
    path = source(tmp_path, "a: [\n").path

    document, error = load_document(path, yaml)

    assert document is None
    assert error is not None
    assert error.startswith("not valid YAML: ")


def test_an_empty_file_is_no_document(tmp_path: Path) -> None:
    document, error = load_document(source(tmp_path, "").path, yaml)

    assert document is None
    assert error == "its top level is nothing, not an object"


def test_arb_is_read_without_its_metadata(tmp_path: Path) -> None:
    content = arb.read(source(tmp_path, ARB, "app_en.arb").path)

    assert content == {"title": "Notes", "count": "{n, plural, one{# note} other{# notes}}"}


def test_an_arb_target_names_its_locale_and_keeps_its_own_metadata(tmp_path: Path) -> None:
    like = source(tmp_path, ARB, "app_en.arb")
    target = tmp_path / "app_fr.arb"
    target.write_text('{"@@locale": "fr", "title": "Old", "@title": {"description": "Le nom"}}')

    arb.write(target, {"title": "Notes", "count": "{n, plural, other{# notes}}"}, like, None, "fr")

    written = json.loads(target.read_text())
    assert list(written) == ["@@locale", "@@x-team", "title", "@title", "count"]
    assert written["@@locale"] == "fr"
    assert written["@title"] == {"description": "Le nom"}  # its own, not the source's
    assert target.read_text().startswith('{\n    "@@locale"')  # the source's indent


def test_an_arb_target_without_locale_in_its_source_gets_none(tmp_path: Path) -> None:
    like = source(tmp_path, '{"a": "A"}', "app_en.arb")

    arb.write(tmp_path / "app_de.arb", {"a": "Ah"}, like, None, "de")

    assert json.loads((tmp_path / "app_de.arb").read_text()) == {"a": "Ah"}


def test_formats_by_extension() -> None:
    assert format_of(Path("a.YAML")) is FORMATS[yaml.format]
    assert format_of(Path("a.json")) is not None
    assert format_of(Path("app_en.arb")) is FORMATS[arb.format]
    assert format_of(Path("a.po")) is None


def _map(node: Any, change: Any) -> Any:
    if isinstance(node, dict):
        return {key: _map(value, change) for key, value in node.items()}
    if isinstance(node, list):
        return [_map(item, change) for item in node]
    return change(node) if isinstance(node, str) else node
