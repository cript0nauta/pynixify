from pathlib import Path
from dataclasses import dataclass
from packaging.version import Version

@dataclass
class Package:
    version: Version

    async def source(self, extra_args=[]) -> Path:
        raise NotImplementedError()

    @property
    def attr(self) -> str:
        raise NotImplementedError()
