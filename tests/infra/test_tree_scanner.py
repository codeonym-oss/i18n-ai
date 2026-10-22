from pathlib import Path

import pytest

from i18n_ai.application.ports.locale import TreeRequest
from i18n_ai.domain.exports.locale import LocaleCode, SourceLocaleUnknown, TreeLayout
from i18n_ai.infra.adapters.filesystem import FileSystemLocaleTreeScanner
from i18n_ai.infra.adapters.filesystem.json_io import detect_style


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
