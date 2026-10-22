import asyncio
import importlib
import logging
import shutil
import sys

from ....application.ports.provider import IPackageInstaller
from .exceptions import PackageInstallFailed

logger = logging.getLogger(__name__)


class RuntimePackageInstaller(IPackageInstaller):
    """Installs into the interpreter i18n-ai runs on, whether a project's venv or a
    `uv tool` environment: with `uv pip install --python <it>` when uv is there, which needs no
    pip in the environment, and with `python -m pip` otherwise."""

    async def install(self, package: str) -> None:
        commands = []
        uv = shutil.which("uv")
        if uv is not None:
            commands.append([uv, "pip", "install", "--python", sys.executable, package])
        commands.append([sys.executable, "-m", "pip", "install", package])

        output = ""
        for command in commands:
            logger.info("Running %s", " ".join(command))
            process = await asyncio.create_subprocess_exec(
                *command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT
            )
            stdout, _ = await process.communicate()
            output = stdout.decode(errors="replace").strip()
            if process.returncode == 0:
                importlib.invalidate_caches()
                return
            logger.debug("%s failed: %s", command[0], output)
        raise PackageInstallFailed(package, _tail(output))


def _tail(output: str, lines: int = 15) -> str:
    return "\n".join(output.splitlines()[-lines:])
