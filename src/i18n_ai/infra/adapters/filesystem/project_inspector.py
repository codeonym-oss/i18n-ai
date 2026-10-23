"""What a project reveals of its i18n library: the dependencies its manifests name (`package.json`,
`Gemfile`, `pubspec.yaml`, `composer.json`, Python's `pyproject.toml`, `requirements*.txt` and
`Pipfile`), its files, and the paths its config files name. Every file is read as text or
data; none is run, so a config computed in code is missed, and the preset's usual places are
tried instead."""

import json
import os
import re
import tomllib
from collections.abc import Iterable
from pathlib import Path

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

from ....application.ports.locale import IProjectInspector
from ....domain.exports.locale import ConfigHint

# A config file is read only when it is this small.
_CONFIG_BYTES = 1_000_000
_GEM = re.compile(r"""^\s*gem\s+['"]([^'"]+)['"]""", re.MULTILINE)
# A Python requirement's name: `Django>=5`, `django[argon2]`, `django ; python_version...`
_REQUIREMENT = re.compile(r"\s*([A-Za-z0-9][A-Za-z0-9._-]*)")


class FileSystemProjectInspector(IProjectInspector):
    async def dependencies(self, root: Path) -> dict[str, str]:
        return _dependencies(root)

    async def find(self, root: Path, pattern: str) -> str | None:
        return _find(root, pattern)

    async def configured(self, root: Path, hint: ConfigHint) -> tuple[Path, str] | None:
        return _configured(root, hint)

    async def is_directory(self, path: Path) -> bool:
        return _is_directory(path)


def _dependencies(root: Path) -> dict[str, str]:
    found: dict[str, str] = {}
    readers = (
        ("package.json", _npm),
        ("composer.json", _composer),
        ("Gemfile", _gems),
        ("pubspec.yaml", _pub),
        ("pyproject.toml", _pyproject),
        ("Pipfile", _pipfile),
    )
    manifests = [(root / name, read) for name, read in readers]
    manifests += [(path, _requirements) for path in sorted(root.glob("requirements*.txt"))]
    for path, read in manifests:
        text = _text(path)
        if text is None:
            continue
        try:
            names = list(read(text))
        except (ValueError, YAMLError, AttributeError, TypeError):
            continue
        for name in names:
            found.setdefault(name.lower(), path.name)
    return found


def _find(root: Path, pattern: str) -> str | None:
    files = (path for path in sorted(root.glob(pattern)) if path.is_file())
    return next((path.relative_to(root).as_posix() for path in files), None)


def _configured(root: Path, hint: ConfigHint) -> tuple[Path, str] | None:
    for file in sorted(root.glob(hint.file)):
        text = _text(file)
        match = re.search(hint.pattern, text) if text is not None else None
        if match is None:
            continue
        for base in hint.under:
            path = Path(os.path.normpath(root / base / match.group(1).strip()))
            if path.is_file():
                path = path.parent
            if path.is_dir():
                return path, file.relative_to(root).as_posix()
    return None


def _is_directory(path: Path) -> bool:
    return path.is_dir()


def _text(path: Path) -> str | None:
    try:
        if not path.is_file() or path.stat().st_size > _CONFIG_BYTES:
            return None
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def _keys(data: object, *sections: str) -> Iterable[str]:
    """The keys of each of `sections` of `data`, those that are tables."""
    if not isinstance(data, dict):
        return
    for section in sections:
        table = data.get(section)
        if isinstance(table, dict):
            yield from (str(key) for key in table)


def _npm(text: str) -> Iterable[str]:
    return _keys(
        json.loads(text),
        "dependencies", "devDependencies", "peerDependencies", "optionalDependencies",
    )  # fmt: skip


def _composer(text: str) -> Iterable[str]:
    return _keys(json.loads(text), "require", "require-dev")


def _gems(text: str) -> Iterable[str]:
    return _GEM.findall(text)


def _pub(text: str) -> Iterable[str]:
    return _keys(YAML(typ="safe", pure=True).load(text), "dependencies", "dev_dependencies")


def _requirements(text: str) -> Iterable[str]:
    for line in text.splitlines():
        if not line.lstrip().startswith(("#", "-")):
            yield from _names([line])


def _pyproject(text: str) -> Iterable[str]:
    data = tomllib.loads(text)
    project = data.get("project", {})
    yield from _names(project.get("dependencies", []))
    for group in [*project.get("optional-dependencies", {}).values(),
                  *data.get("dependency-groups", {}).values()]:  # fmt: skip
        yield from _names(entry for entry in group if isinstance(entry, str))
    poetry = data.get("tool", {}).get("poetry", {})
    yield from _keys(poetry, "dependencies", "dev-dependencies")
    for group in poetry.get("group", {}).values():
        yield from _keys(group, "dependencies")


def _pipfile(text: str) -> Iterable[str]:
    return _keys(tomllib.loads(text), "packages", "dev-packages")


def _names(requirements: Iterable[str]) -> Iterable[str]:
    for requirement in requirements:
        match = _REQUIREMENT.match(requirement)
        if match is not None:
            yield match.group(1)
