import os
from pathlib import Path

import pytest

from i18n_ai.application.ports.locale import TreeRequest
from i18n_ai.domain.exports.locale import (
    LocaleCode,
    LocaleFormat,
    LocaleTreeNotFound,
    MessageSyntax,
    MixedLocaleFormats,
    SourceLocaleUnknown,
    TreeLayout,
)
from i18n_ai.infra.adapters.filesystem import FileSystemLocaleStore, FileSystemLocaleTreeScanner
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
        ("django/locale", "directory", "po"),
        ("gnu/po", "file", "po"),
        ("i18next/locales", "directory", "json"),
        ("icu/messages", "file", "json"),
        ("laravel/lang", "file", "json"),
        ("symfony/translations", "file", "xliff"),
        ("vue-i18n/locales", "file", "yaml"),
        ("angular/src/locale", "file", "xliff"),
        ("flutter/lib/l10n", "file", "arb"),
        ("rails/config/locales", "file", "yaml"),
    ]
    assert [locale.value for locale in found[3].locales] == ["en", "fr"]


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
    (tmp_path / "en.properties").write_text("a=A\n")
    (tmp_path / "en.json").write_text('{"a": "A"}')
    scanner = FileSystemLocaleTreeScanner()

    with pytest.raises(
        LocaleTreeNotFound, match=r"\(\.json, \.yml, \.yaml, \.arb, \.po, \.pot, \.xlf, \.xliff\)"
    ):
        await scanner.scan(TreeRequest(tmp_path / "en.properties"))
    with pytest.raises(LocaleTreeNotFound, match=r"\(\.yml, \.yaml\)"):
        await scanner.scan(TreeRequest(tmp_path / "en.json", format=LocaleFormat.YAML))


async def test_locale_files_may_share_a_prefix(tmp_path: Path) -> None:
    for name in ("app_en.arb", "app_pt_BR.arb", "app.arb", "other_de.arb"):
        (tmp_path / name).write_text('{"a": "A"}')
    scanner = FileSystemLocaleTreeScanner()

    tree = await scanner.scan(TreeRequest(tmp_path))

    assert tree.format == LocaleFormat.ARB
    assert tree.prefix == "app_"
    assert tree.files[0].path == tmp_path / "app_en.arb"
    assert [locale.value for locale in tree.existing] == ["pt_BR"]
    assert tree.target_location(LocaleCode("pt-BR"), tree.files[0]).path == (
        tmp_path / "app_pt_BR.arb"
    )
    assert await scanner.scan(TreeRequest(tmp_path / "app_en.arb")) == tree


async def test_a_new_arb_locale_is_spelled_with_an_underscore(tmp_path: Path) -> None:
    (tmp_path / "intl_en.arb").write_text('{"a": "A"}')
    (tmp_path / "en.json").write_text('{"a": "A"}')

    arb = await FileSystemLocaleTreeScanner().scan(TreeRequest(tmp_path / "intl_en.arb"))
    json = await FileSystemLocaleTreeScanner().scan(TreeRequest(tmp_path / "en.json"))

    location = arb.target_location(LocaleCode("zh-Hant-TW"), arb.files[0])
    assert location.path == tmp_path / "intl_zh_Hant_TW.arb"
    assert location.locale == "zh_Hant_TW"
    assert json.target_location(LocaleCode("pt-BR"), json.files[0]).path == tmp_path / "pt-BR.json"


async def test_a_django_tree_without_its_source_reads_the_msgids(examples: Path) -> None:
    locale = examples / "django" / "locale"

    tree = await FileSystemLocaleTreeScanner().scan(TreeRequest(locale))

    assert (tree.layout, tree.format, tree.source.value) == (
        TreeLayout.DIRECTORY,
        LocaleFormat.PO,
        "en",
    )
    [file] = tree.files
    assert str(file.name) == "LC_MESSAGES/django.po"
    assert file.path == locale / "fr/LC_MESSAGES/django.po"
    assert file.document is not None
    assert file.document.content["Welcome to our shop"] == "Welcome to our shop"  # not French
    assert tree.source_path == file.path
    assert [code.value for code in tree.existing] == ["fr"]
    assert tree.target_location(LocaleCode("pt-BR"), file).path == (
        locale / "pt_BR/LC_MESSAGES/django.po"
    )


async def test_the_latest_catalog_is_the_template(tmp_path: Path) -> None:
    for locale, mtime in (("de", 2_000_000_000), ("fr", 1_000_000_000)):
        catalog = tmp_path / locale / "LC_MESSAGES" / "app.po"
        catalog.parent.mkdir(parents=True)
        catalog.write_text(f'msgid "{locale}"\nmsgstr ""\n')
        os.utime(catalog, (mtime, mtime))

    tree = await FileSystemLocaleTreeScanner().scan(TreeRequest(tmp_path))

    assert tree.files[0].path == tmp_path / "de/LC_MESSAGES/app.po"
    fr = await FileSystemLocaleTreeScanner().scan(TreeRequest(tmp_path, source=LocaleCode("fr")))
    assert fr.source.value == "fr"
    assert fr.files[0].path == tmp_path / "fr/LC_MESSAGES/app.po"


async def test_a_template_beside_its_catalogs(examples: Path) -> None:
    po = examples / "gnu" / "po"
    scanner = FileSystemLocaleTreeScanner()

    tree = await scanner.scan(TreeRequest(po))

    assert (tree.layout, tree.format, tree.prefix) == (TreeLayout.FILE, LocaleFormat.PO, "")
    assert tree.files[0].path == po / "notes.pot"
    assert [code.value for code in tree.existing] == ["de"]
    assert tree.target_location(LocaleCode("ar"), tree.files[0]).path == po / "ar.po"
    assert await scanner.scan(TreeRequest(po / "notes.pot")) == tree


async def test_a_template_names_its_catalogs_as_they_are(tmp_path: Path) -> None:
    (tmp_path / "acme.pot").write_text('msgid "a"\nmsgstr ""\n')
    (tmp_path / "acme-fr_FR.po").write_text('msgid "a"\nmsgstr "b"\n')

    tree = await FileSystemLocaleTreeScanner().scan(TreeRequest(tmp_path / "acme.pot"))

    assert tree.prefix == "acme-"
    assert [code.value for code in tree.existing] == ["fr_FR"]
    assert tree.target_location(LocaleCode("pt-BR"), tree.files[0]).path == (
        tmp_path / "acme-pt_BR.po"
    )


async def test_a_babel_template_beside_its_locale_directories(tmp_path: Path) -> None:
    (tmp_path / "messages.pot").write_text('msgid "a"\nmsgstr ""\n')
    (tmp_path / "fr/LC_MESSAGES").mkdir(parents=True)
    (tmp_path / "fr/LC_MESSAGES/messages.po").write_text('msgid "a"\nmsgstr "b"\n')

    tree = await FileSystemLocaleTreeScanner().scan(TreeRequest(tmp_path))

    [file] = tree.files
    assert (str(file.name), file.path) == ("LC_MESSAGES/messages.po", tmp_path / "messages.pot")
    assert tree.target_location(LocaleCode("de"), file).path == (
        tmp_path / "de/LC_MESSAGES/messages.po"
    )


async def test_an_xliff_template_names_its_translations_as_angular_does(tmp_path: Path) -> None:
    template = tmp_path / "messages.xlf"
    template.write_text(
        '<xliff version="1.2"><file><body><trans-unit id="a"><source>A</source></trans-unit>'
        "</body></file></xliff>"
    )

    tree = await FileSystemLocaleTreeScanner().scan(TreeRequest(tmp_path))

    assert (tree.layout, tree.format, tree.prefix) == (
        TreeLayout.FILE,
        LocaleFormat.XLIFF,
        "messages.",
    )
    assert tree.files[0].path == template
    assert tree.target_location(LocaleCode("pt-BR"), tree.files[0]).path == (
        tmp_path / "messages.pt-BR.xlf"
    )
    assert await FileSystemLocaleTreeScanner().scan(TreeRequest(template)) == tree


async def test_a_preferred_format_is_read_alone_in_a_mixed_tree(tmp_path: Path) -> None:
    (tmp_path / "en").mkdir()
    (tmp_path / "en/app.json").write_text('{"a": "A"}')
    (tmp_path / "en/mail.yml").write_text("b: B\n")
    (tmp_path / "fr.json").write_text("{}")
    (tmp_path / "de.yml").write_text("{}")
    scanner = FileSystemLocaleTreeScanner()

    tree = await scanner.scan(TreeRequest(tmp_path / "en", preferred=LocaleFormat.YAML))
    assert [str(file.name) for file in tree.files] == ["mail.yml"]
    assert (tree.format, tree.left_alone) == (LocaleFormat.YAML, (LocaleFormat.JSON,))

    (tmp_path / "en").rename(tmp_path / "source")
    tree = await scanner.scan(TreeRequest(tmp_path, preferred=LocaleFormat.JSON))
    assert (tree.source.value, tree.existing) == ("fr", ())  # de.yml left alone
    assert tree.left_alone == (LocaleFormat.YAML,)

    with pytest.raises(MixedLocaleFormats):
        await scanner.scan(TreeRequest(tmp_path, preferred=LocaleFormat.ARB))


def laravel(path: Path, source: str | None = None) -> TreeRequest:
    return TreeRequest(
        path, source=LocaleCode(source) if source else None, syntax=MessageSyntax.LARAVEL
    )


def write_lang(root: Path, files: dict[str, str]) -> Path:
    for name, content in files.items():
        (root / name).parent.mkdir(parents=True, exist_ok=True)
        (root / name).write_text(content, encoding="utf-8")
    return root


async def test_a_laravel_tree_without_its_source_takes_its_keys(tmp_path: Path) -> None:
    lang = write_lang(
        tmp_path / "lang",
        {
            "fr.json": '{\n    "Hello": "Bonjour",\n    "Bye": "Salut"\n}\n',
            "de.json": '{"Bye": "Tschüss", "Thanks": "Danke", "n": 3}',
            "en/auth.php": "<?php return ['failed' => 'Nope'];",
            "vendor/pkg/fr.json": '{"Pkg": "Pkg"}',
        },
    )

    tree = await FileSystemLocaleTreeScanner().scan(laravel(lang))

    assert (tree.layout, tree.source.value, tree.syntax) == (
        TreeLayout.FILE, "en", MessageSyntax.LARAVEL
    )  # fmt: skip
    assert tree.source_from == ("de.json", "fr.json")
    assert [locale.value for locale in tree.existing] == ["de", "fr"]
    [file] = tree.files
    assert str(file.name) == "en.json"
    assert file.document is not None
    assert file.document.content == {"Bye": "Bye", "Thanks": "Thanks", "Hello": "Hello"}
    assert tree.target_location(LocaleCode("es"), file).path == lang / "es.json"
    assert tree.target_location(LocaleCode("fr"), file).path == lang / "fr.json"


async def test_a_laravel_tree_with_its_source_reads_it(tmp_path: Path) -> None:
    lang = write_lang(
        tmp_path / "lang",
        {"en.json": '{"Hello": "Hello!"}', "fr.json": '{"Hello": "Salut !"}', "en/a.php": ""},
    )

    tree = await FileSystemLocaleTreeScanner().scan(laravel(lang))

    assert (tree.source.value, tree.source_from) == ("en", ())
    assert tree.files[0].path == lang / "en.json"
    assert tree.files[0].document is not None
    assert tree.files[0].document.content == {"Hello": "Hello!"}

    tree = await FileSystemLocaleTreeScanner().scan(laravel(lang, "fr"))
    assert tree.files[0].path == lang / "fr.json"
    assert [locale.value for locale in tree.existing] == ["en"]

    tree = await FileSystemLocaleTreeScanner().scan(laravel(lang / "fr.json"))
    assert tree.source.value == "en"  # a file names its tree, not its source


async def test_a_laravel_target_is_written_as_its_first_locale_file(tmp_path: Path) -> None:
    lang = write_lang(tmp_path / "lang", {"de.json": '{\n\t"A": "Ä"\n}', "fr.json": '{"A": "À"}'})

    tree = await FileSystemLocaleTreeScanner().scan(laravel(lang))
    target = tree.target_location(LocaleCode("es"), tree.files[0])
    await FileSystemLocaleStore().write(target, {"A": "Á"}, tree.files[0])

    assert (lang / "es.json").read_text(encoding="utf-8") == '{\n\t"A": "Á"\n}'


async def test_without_laravel_s_syntax_the_tree_is_read_as_any(tmp_path: Path) -> None:
    lang = write_lang(tmp_path / "lang", {"fr.json": "{}", "de.json": "{}"})

    with pytest.raises(SourceLocaleUnknown):
        await FileSystemLocaleTreeScanner().scan(TreeRequest(lang))
    tree = await FileSystemLocaleTreeScanner().scan(TreeRequest(lang, source=LocaleCode("fr")))
    assert (tree.syntax, tree.source_from) == (MessageSyntax.STANDARD, ())
