from dataclasses import dataclass


@dataclass(frozen=True)
class InstallReceipt:
    """`installed_now` is False when the package was already there, and was reused."""

    provider: str
    package: str
    installed_now: bool
