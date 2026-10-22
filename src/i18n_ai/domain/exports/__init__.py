"""Each sub-domain's public names. Import from `exports.locale` or `exports.provider`, not from
the sub-domain packages."""

from types import ModuleType


def public(*packages: ModuleType) -> list[str]:
    """Collect the names the packages export. Raises if two packages export the same name for
    different things."""
    owners: dict[str, ModuleType] = {}
    for package in packages:
        for name in package.__all__:
            owner = owners.setdefault(name, package)
            if getattr(owner, name) is not getattr(package, name):
                raise ImportError(
                    f"{name} is exported by both {owner.__name__} and {package.__name__}"
                )
    return list(owners)
