import json
import asyncio
from pathlib import Path
from typing import Sequence, Any
from collections import defaultdict
from packaging.utils import canonicalize_name
from packaging.requirements import Requirement
from packaging.version import Version, parse
from pypi2nixpkgs.base import Package
from pypi2nixpkgs.exceptions import PackageNotFound, NixBuildError

class NixPackage(Package):
    def __init__(self, *, attr: str, version: Version):
        self.version = version
        self.__attr = attr  # Ugly hack to fix mypy errors

    @property
    def attr(self):
        # Ugly hack to fix mypy errors
        return self.__attr

    async def source(self, extra_args=[]):
        args = [
            '--no-out-link',
            '<nixpkgs>',
            '--no-build-output',
            '-A',
            f'python37Packages."{self.attr}".src',
        ]
        args += extra_args
        return await run_nix_build(*args)


class NixpkgsData:
    def __init__(self, data):
        data_defaultdict: Any = defaultdict(list)
        for (k, v) in data.items():
            data_defaultdict[canonicalize_name(k)] += v
        self.__data = dict(data_defaultdict)

    def from_pypi_name(self, name: str) -> Sequence[NixPackage]:
        try:
            data = self.__data[canonicalize_name(name)]
        except KeyError:
            raise PackageNotFound(f'{name} is not defined in nixpkgs')
        return [
            NixPackage(attr=drv['attr'], version=parse(drv['version']))
            for drv in data
        ]

    def from_requirement(self, req: Requirement) -> Sequence[NixPackage]:
        drvs = self.from_pypi_name(req.name)
        return [drv for drv in drvs if str(drv.version) in req.specifier]


async def load_nixpkgs_data(extra_args):
    nix_expression_path = Path(__file__).parent / "data" / "pythonPackages.nix"
    args = [
        '--eval',
        '--strict',
        '--json',
        str(nix_expression_path),
    ]
    args += extra_args
    proc = await asyncio.create_subprocess_exec(
        'nix-instantiate', *args, stdout=asyncio.subprocess.PIPE)
    (stdout, _) = await proc.communicate()
    status = await proc.wait()
    assert status == 0
    ret = json.loads(stdout)
    return ret


async def run_nix_build(*args: Sequence[str]) -> Path:
    proc = await asyncio.create_subprocess_exec(
        'nix-build', *args, stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL)
    (stdout, _) = await proc.communicate()
    status = await proc.wait()
    if status:
        raise NixBuildError(f'nix-buld failed with code {status}')
    return Path(stdout.strip().decode())
