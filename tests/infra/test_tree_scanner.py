from pathlib import Path

import pytest

from i18n_ai.application.ports.locale import TreeRequest
from i18n_ai.domain.exports.locale import (
    LocaleCode,
    LocaleFormat,
    LocaleTreeNotFound,
    MixedLocaleFormats,
    SourceLocaleUnknown,
    TreeLayout,
)
from i18n_ai.infra.adapters.filesystem import FileSystemLocaleTreeScanner
from i18n_ai.infra.adapters.filesystem.formats.json_format import detect_style


async def test_the_locales_directory_defaults_to_en(examples: Path) -> None:
    tree = await FileSystemLocaleTreeScanner().scan(TreeRequest(examples / "i18next" / "locales"))
    assert tree.layout == TreeLayout.DIRECTORY
    assert tree.source.value == "en"
    assert [str(file.name) for file in tree.files] == [
        "auth/login.json",
        "common.json",
        "meta.json",
    ]
    assert [locale.value for locale in tree.existing] == ["fr"]


async def test_several_locales_and_no_en_need_a_source(tmp_path: Path) -> None:
    for name in ("de", "fr"):
        (tmp_path / name).mkdir()
    with pytest.raises(SourceLocaleUnknown):
        await FileSystemLocaleTreeScanner().scan(TreeRequest(tmp_path))
    tree = await FileSystemLocaleTreeScanner().scan(TreeRequest(tmp_path, source=LocaleCode("de")))
    assert tree.source.value == "de"


async def test_an_existing_locale_keeps_its_spelling(tmp_path: Path) -> None:
    (tmp_path / "en").mkdir()
    (tmp_path / "en" / "a.json").write_text('{"x": "y"}')
    (tmp_path / "pt_BR").mkdir()
    tree = await FileSystemLocaleTreeScanner().scan(TreeRequest(tmp_path / "en"))
    assert (
        tree.target_location(LocaleCode("pt-BR"), tree.files[0]).path
        == tmp_path / "pt_BR" / "a.json"
    )


async def test_include_and_exclude(examples: Path) -> None:
    request = TreeRequest(
        examples / "i18next" / "locales" / "en", include=("*.json",), exclude=("meta.json",)
    )
    tree = await FileSystemLocaleTreeScanner().scan(request)
    assert [str(file.name) for file in tree.files] == ["auth/login.json", "common.json"]


def test_the_json_style_is_detected() -> None:
    assert detect_style('{\n    "a": 1\n}\n').indent == 4
    assert detect_style('{\n\t"a": 1\n}').indent == "\t"
    assert detect_style('{"a": 1}').indent is None
    assert detect_style('{"a": 1}').trailing_newline is False


async def test_detect_finds_every_tree_in_a_project(examples: Path) -> None:
    (examples / "node_modules/pkg/locales/en").mkdir(parents=True)
    (examples / "node_modules/pkg/locales/en/a.json").write_text('{"a": "A"}')
    (examples / "package.json").write_text('{"name": "site", "dependencies": {}}')
    (examples / "broken.json").write_text("{")

    found = await FileSystemLocaleTreeScanner().detect(examples)

    assert [
        (c.path.relative_to(examples).as_posix(), c.layout.value, *c.formats) for c in found
    ] == [
        ("bundle/i18n.json", "bundle", "json"),
        ("i18next/locales", "directory", "json"),
        ("icu/messages", "file", "json"),
        ("vue-i18n/locales", "file", "yaml"),
        ("rails/config/locales", "file", "yaml"),
    ]
    assert [locale.value for locale in found[1].locales] == ["en", "fr"]


async def test_detect_finds_nothing_in_a_project_without_locales(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src/config.json").write_text('{"debug": true}')

    assert await FileSystemLocaleTreeScanner().detect(tmp_path) == []


async def test_detect_takes_a_lone_locale_only_where_it_looks_like_one(tmp_path: Path) -> None:
    for directory in ("app/ts", "app/locales/fr", "site/en"):
        (tmp_path / directory).mkdir(parents=True)
        (tmp_path / directory / "a.json").write_text('{"a": "A"}')

    found = await FileSystemLocaleTreeScanner().detect(tmp_path)

    assert sorted(c.path.relative_to(tmp_path).as_posix() for c in found) == [
        "app/locales",
        "site",
    ]


async def test_a_rails_file_holds_its_messages_under_its_locale(examples: Path) -> None:
    tree = await FileSystemLocaleTreeScanner().scan(TreeRequest(examples / "rails/config/locales"))

    assert tree.layout == TreeLayout.FILE
    assert tree.format == LocaleFormat.YAML
    [file] = tree.files
    assert file.root_key == "en"
    assert file.document is not None
    assert file.document.content["hello"] == "Hello world"
    location = tree.target_location(LocaleCode("fr"), file)
    assert location.path == examples / "rails/config/locales/fr.yml"
    assert location.bundle_key == "fr"


async def test_a_file_rooted_at_another_key_is_read_whole(tmp_path: Path) -> None:
    (tmp_path / "en.yml").write_text("app:\n  title: Acme\n")

    tree = await FileSystemLocaleTreeScanner().scan(TreeRequest(tmp_path / "en.yml"))

    assert tree.files[0].root_key is None
    assert tree.target_location(LocaleCode("de"), tree.files[0]).bundle_key is None


async def test_a_yaml_bundle(tmp_path: Path) -> None:
    (tmp_path / "i18n.yaml").write_text("en:\n  a: A\nde:\n  a: Ah\n")

    tree = await FileSystemLocaleTreeScanner().scan(TreeRequest(tmp_path / "i18n.yaml"))

    assert tree.layout == TreeLayout.BUNDLE
    assert tree.format == LocaleFormat.YAML
    assert tree.files[0].root_key == "en"
    assert [locale.value for locale in tree.existing] == ["de"]


async def test_mixed_formats_are_refused_unless_one_is_chosen(tmp_path: Path) -> None:
    (tmp_path / "en").mkdir()
    (tmp_path / "en/app.json").write_text('{"a": "A"}')
    (tmp_path / "en/mail.yml").write_text("b: B\n")
    scanner = FileSystemLocaleTreeScanner()

    with pytest.raises(MixedLocaleFormats, match="mixes the formats json, yaml"):
        await scanner.scan(TreeRequest(tmp_path / "en"))

    tree = await scanner.scan(TreeRequest(tmp_path / "en", format=LocaleFormat.YAML))
    assert [str(file.name) for file in tree.files] == ["mail.yml"]
    assert tree.format == LocaleFormat.YAML


async def test_mixed_locale_files_are_refused(tmp_path: Path) -> None:
    (tmp_path / "en.yml").write_text("c: C\n")
    (tmp_path / "fr.json").write_text('{"c": "C"}')
    scanner = FileSystemLocaleTreeScanner()

    with pytest.raises(MixedLocaleFormats):
        await scanner.scan(TreeRequest(tmp_path))

    tree = await scanner.scan(TreeRequest(tmp_path, format=LocaleFormat.YAML))
    assert tree.files[0].path == tmp_path / "en.yml"


async def test_a_file_in_another_format_is_not_a_tree(tmp_path: Path) -> None:
    (tmp_path / "en.po").write_text('msgid "a"\nmsgstr ""\n')
    (tmp_path / "en.json").write_text('{"a": "A"}')
    scanner = FileSystemLocaleTreeScanner()

    with pytest.raises(LocaleTreeNotFound, match=r"\(\.json, \.yml, \.yaml\)"):
        await scanner.scan(TreeRequest(tmp_path / "en.po"))
    with pytest.raises(LocaleTreeNotFound, match=r"\(\.yml, \.yaml\)"):
        await scanner.scan(TreeRequest(tmp_path / "en.json", format=LocaleFormat.YAML))
