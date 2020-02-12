import operator
from typing import Dict, Callable, Awaitable, Optional, List, Tuple
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name
from packaging.specifiers import SpecifierSet
from pypi2nixpkgs.base import Package
from pypi2nixpkgs.nixpkgs_sources import NixpkgsData
from pypi2nixpkgs.pypi_api import PyPIData, PyPIPackage
from pypi2nixpkgs.package_requirements import (
    PackageRequirements,
    eval_path_requirements,
)
from pypi2nixpkgs.exceptions import (
    NoMatchingVersionFound,
    PackageNotFound,
)

class VersionChooser:
    F_TYPE = Callable[[Package], Awaitable[PackageRequirements]]
    def __init__(self, nixpkgs_data: NixpkgsData, pypi_data: PyPIData,
                 req_evaluate: F_TYPE):
        self.nixpkgs_data = nixpkgs_data
        self.pypi_data = pypi_data
        self._choosed_packages: Dict[str, Tuple[Package, SpecifierSet]] = {}
        self.evaluate_requirements = req_evaluate

    async def require(self, r: Requirement):
        pkg: Package

        if r.marker and not r.marker.evaluate():
            return

        try:
            (pkg, specifier) = self._choosed_packages[canonicalize_name(r.name)]
        except KeyError:
            pass
        else:
            specifier &= r.specifier
            self._choosed_packages[canonicalize_name(r.name)] = (pkg, specifier)
            if pkg.version not in specifier:
                raise NoMatchingVersionFound(
                    f'{r.name}=={str(pkg.version)} does not match {r}'
                )
            return

        # TODO improve mypy signatures to make this possible
        # pkgs = await self.pypi_data.from_requirement(r)
        # pkgs += self.nixpkgs_data.from_requirement(r)
        pkgs: List[Package] = []

        found_pypi = True
        found_nixpkgs = True

        try:
            for p in self.nixpkgs_data.from_requirement(r):
                pkgs.append(p)
        except PackageNotFound:
            found_nixpkgs = False

        if not pkgs:
            try:
                for p_ in await self.pypi_data.from_requirement(r):
                    pkgs.append(p_)
            except PackageNotFound:
                found_pypi = False

        if not found_nixpkgs and not found_pypi:
            raise PackageNotFound(f'{r.name} not found in PyPI nor nixpkgs')

        if not pkgs:
            raise NoMatchingVersionFound(str(r))

        pkg = max(pkgs, key=operator.attrgetter('version'))
        self._choosed_packages[canonicalize_name(r.name)] = (pkg, r.specifier)
        reqs: PackageRequirements = await self.evaluate_requirements(pkg)

        for req in reqs.runtime_requirements:
            await self.require(req)
        # for req in reqs.test_requirements:
        #     if canonicalize_name(req.name) in self._choosed_packages:
        #         continue
        #     await self.require(req)

    def package_for(self, package_name: str) -> Optional[Package]:
        try:
            (pkg, _) = self._choosed_packages[canonicalize_name(package_name)]
        except KeyError:
            return None
        return pkg

    def all_pypi_packages(self) -> List[PyPIPackage]:
        return [
            v[0] for v in self._choosed_packages.values()
            if isinstance(v[0], PyPIPackage)
        ]

async def evaluate_package_requirements(
        pkg: Package, extra_args=[]) -> PackageRequirements:
    src = await pkg.source(extra_args)
    return await eval_path_requirements(src)
