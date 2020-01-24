from typing import Sequence
from dataclasses import dataclass
from packaging.utils import canonicalize_name
from packaging.requirements import Requirement
from packaging.version import Version, parse


@dataclass
class PyPIPackage:
    version: Version
    sha256: str
    download_url: str


class PyPIData:
    def __init__(self, pypi_cache):
        self.pypi_cache = pypi_cache

    async def from_requirement(self, req: Requirement) -> Sequence[PyPIPackage]:
        response = await self.pypi_cache.fetch(canonicalize_name(req.name))
        matching = []
        for (version, version_dist) in response['releases'].items():
            try:
                data = next(e for e in version_dist if e['packagetype'] == 'sdist')
            except StopIteration:
                continue
            if version in req.specifier:
                matching.append(PyPIPackage(
                    sha256=data['digests']['sha256'],
                    version=parse(version),
                    download_url=data['url'],
                ))
        return matching
