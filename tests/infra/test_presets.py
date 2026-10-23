"""The presets, detected on the examples, which are small projects of each library, and on
projects written for a test."""

import json
import re
from pathlib import Path

import pytest

from i18n_ai.application.exports.locale import (
    DetectPresetQuery,
    DetectPresetQueryHandler,
    ListPresetsQuery,
    ListPresetsQueryHandler,
    PresetMatch,
)
from i18n_ai.domain.exports.locale import PRESETS, PresetUnknown, preset_named
from i18n_ai.infra.adapters.filesystem import FileSystemProjectInspector


async def detect(root: Path, name: str | None = None) -> PresetMatch | None:
    handler = DetectPresetQueryHandler(FileSystemProjectInspector())
    return await handler.handle(DetectPresetQuery(root, name))


def write(root: Path, files: dict[str, str]) -> Path:
    for name, content in files.items():
        (root / name).parent.mkdir(parents=True, exist_ok=True)
        (root / name).write_text(content, encoding="utf-8")
    return root


def npm(*packages: str) -> str:
    return json.dumps({"dependencies": dict.fromkeys(packages, "*")})


@pytest.mark.parametrize(
    ("project", "preset", "reason", "tree", "tree_from"),
    [
        ("i18next", "i18next", "i18next in package.json", "locales", None),
        ("icu", "next-intl", "next-intl in package.json", "messages", None),
        ("vue-i18n", "vue-i18n", "vue-i18n in package.json", "locales", None),
        ("angular", "angular", "@angular/localize in package.json", "src/locale", "angular.json"),
        ("rails", "rails", "rails in Gemfile", "config/locales", None),
        ("django", "django", "django in requirements.txt", "locale", "site/settings.py"),
        ("flutter", "flutter", "flutter_localizations in pubspec.yaml", "lib/l10n", "l10n.yaml"),
    ],
)
async def test_each_example_reveals_its_library(
    examples: Path, project: str, preset: str, reason: str, tree: str, tree_from: str | None
) -> None:
    match = await detect(examples / project)

    assert match is not None
    assert (match.preset.name, match.reason) == (preset, reason)
    assert match.tree == examples / project / tree
    assert match.tree_from == tree_from


async def test_a_project_without_a_library_has_no_preset(examples: Path) -> None:
    assert await detect(examples / "symfony") is None
    assert await detect(examples / "bundle") is None


async def test_nuxt_comes_before_vue_i18n_and_reads_its_lang_dir(tmp_path: Path) -> None:
    write(
        tmp_path,
        {
            "package.json": npm("nuxt", "vue-i18n", "@nuxtjs/i18n"),
            "nuxt.config.ts": "export default defineNuxtConfig({ i18n: { langDir: 'lang/' } })",
            "i18n/lang/en.json": '{"hello": "Hello"}',
        },
    )

    match = await detect(tmp_path)

    assert match is not None
    assert match.preset.name == "nuxt-i18n"
    assert match.preset.format is None  # JSON or YAML
    assert (match.tree, match.tree_from) == (tmp_path / "i18n/lang", "nuxt.config.ts")


async def test_the_first_library_whose_locales_are_found_wins(tmp_path: Path) -> None:
    write(tmp_path, {"package.json": npm("@nuxtjs/i18n", "vue-i18n"), "src/locales/en.json": "{}"})

    match = await detect(tmp_path)

    assert match is not None
    assert (match.preset.name, match.tree) == ("vue-i18n", tmp_path / "src/locales")


async def test_a_library_whose_locales_are_not_found_is_still_told(tmp_path: Path) -> None:
    write(tmp_path, {"package.json": npm("next-intl")})

    match = await detect(tmp_path)

    assert match is not None
    assert (match.preset.name, match.tree) == ("next-intl", None)


@pytest.mark.parametrize(
    ("files", "preset", "tree", "tree_from"),
    [
        (
            {
                "i18next-parser.config.mjs": "export default {\n"
                "  output: './public/static/locales/$LOCALE/$NAMESPACE.json',\n}",
                "public/static/locales/en/common.json": "{}",
            },
            "i18next",
            "public/static/locales",
            "i18next-parser.config.mjs",
        ),
        (
            {
                "package.json": npm("next-i18next"),
                "next-i18next.config.js": "module.exports = {\n"
                "  localePath: path.resolve('./static/i18n'),\n}",
                "static/i18n/en/common.json": "{}",
            },
            "i18next",
            "static/i18n",
            "next-i18next.config.js",
        ),
        (
            {
                "transloco.config.ts": "const config = {\n  rootTranslationsPath: 'src/i18n/',\n};",
                "src/i18n/en.json": "{}",
            },
            "transloco",
            "src/i18n",
            "transloco.config.ts",
        ),
        (
            {
                "project.inlang/settings.json": json.dumps(
                    {"plugin.inlang.messageFormat": {"pathPattern": "./i18n/{locale}.json"}}
                ),
                "i18n/en.json": "{}",
            },
            "paraglide",
            "i18n",
            "project.inlang/settings.json",
        ),
        (
            {
                "manage.py": "",
                "app/settings/base.py": "LOCALE_PATHS = (\n"
                "    os.path.join(BASE_DIR, 'conf/locale'),\n)",
                "conf/locale/fr/LC_MESSAGES/django.po": "",
            },
            "django",
            "conf/locale",
            "app/settings/base.py",
        ),
    ],
)
async def test_a_config_file_says_where_the_locales_are(
    tmp_path: Path, files: dict[str, str], preset: str, tree: str, tree_from: str
) -> None:
    match = await detect(write(tmp_path, files))

    assert match is not None
    assert match.preset.name == preset
    assert (match.tree, match.tree_from) == (tmp_path / tree, tree_from)


async def test_a_config_naming_no_existing_directory_gives_the_usual_place(
    tmp_path: Path,
) -> None:
    write(tmp_path, {"l10n.yaml": "arb-dir: gone\n", "lib/l10n/app_en.arb": "{}"})

    match = await detect(tmp_path)

    assert match is not None
    assert match.reason == "l10n.yaml"
    assert (match.tree, match.tree_from) == (tmp_path / "lib/l10n", None)


@pytest.mark.parametrize(
    ("files", "reason"),
    [
        ({"pyproject.toml": '[project]\ndependencies = ["Django[argon2]>=5"]'}, "pyproject.toml"),
        (
            {"pyproject.toml": "[tool.poetry.group.web.dependencies]\ndjango = '^5'"},
            "pyproject.toml",
        ),
        ({"pyproject.toml": '[dependency-groups]\nweb = ["django"]'}, "pyproject.toml"),
        ({"Pipfile": '[packages]\ndjango = "*"'}, "Pipfile"),
        ({"requirements-web.txt": "# web\n-r base.txt\ndjango==5.2 ; python_version>'3'"}, None),
    ],
)
async def test_python_manifests(tmp_path: Path, files: dict[str, str], reason: str | None) -> None:
    match = await detect(write(tmp_path, files))

    assert match is not None
    assert match.preset.name == "django"
    assert match.reason == f"django in {reason or next(iter(files))}"


async def test_a_broken_manifest_is_passed_over(tmp_path: Path) -> None:
    write(
        tmp_path,
        {
            "package.json": "{",
            "pubspec.yaml": "dependencies: [",
            "pyproject.toml": "[project",
            "composer.json": "[]",
            "Gemfile": "gem 'rails'",
        },
    )

    match = await detect(tmp_path)

    assert match is not None
    assert match.reason == "rails in Gemfile"


async def test_a_preset_can_be_named(examples: Path) -> None:
    match = await detect(examples / "i18next", "Rails")

    assert match is not None
    assert (match.preset.name, match.reason, match.tree) == ("rails", "chosen", None)
    with pytest.raises(PresetUnknown, match="no preset is called nope; the presets are nuxt-i18n"):
        await detect(examples / "i18next", "nope")


async def test_every_preset_is_listed_in_order() -> None:
    listed = await ListPresetsQueryHandler().handle(ListPresetsQuery())

    assert [preset.name for preset in listed] == [preset.name for preset in PRESETS]
    rails = next(preset for preset in listed if preset.name == "rails")
    assert (rails.format, rails.placeholders) == ("yaml", ("rails",))


def test_the_table_is_sound() -> None:
    assert len({preset.name for preset in PRESETS}) == len(PRESETS)
    for preset in PRESETS:
        assert preset.packages or preset.files
        assert preset.trees
        assert preset.placeholders
        for hint in preset.config:
            assert re.compile(hint.pattern).groups >= 1
    assert preset_named(" Flutter ").name == "flutter"
