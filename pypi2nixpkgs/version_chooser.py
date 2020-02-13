import operator
from pathlib import Path
from dataclasses import dataclass
from typing import Any, Dict, Callable, Awaitable, Optional, List, Tuple
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
        self._local_packages: Dict[str, Package] = {}
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
            pkg = self._local_packages[canonicalize_name(r.name)]
        except KeyError:
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

    async def require_local(self, pypi_name: str, src: Path):
        assert pypi_name not in self._choosed_packages
        package = PyPIPackage(
            pypi_name=pypi_name,
            download_url='',
            sha256='',
            version='0.1dev',
            pypi_cache=self.pypi_data.pypi_cache,
            local_source=src,
        )
        self._local_packages[canonicalize_name(pypi_name)] = package
        await self.require(Requirement(pypi_name))

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


@dataclass
class ChosenPackageRequirements:
    build_requirements: List[Package]
    test_requirements: List[Package]
    runtime_requirements: List[Package]

    @classmethod
    def from_package_requirements(
            cls,
            package_requirements: PackageRequirements,
            version_chooser: VersionChooser):
        kwargs: Any = {}

        # build_requirements uses packages from nixpkgs. The packages do not
        # need to be included in the version chooser
        kwargs['build_requirements'] = []
        for req in package_requirements.build_requirements:
            package_ = max(
                version_chooser.nixpkgs_data.from_requirement(req),
                key=operator.attrgetter('version')
            )
            kwargs['build_requirements'].append(package_)

        # test_requirements is not implemented for now
        kwargs['test_requirements'] = []

        # runtime_requirements uses the packages in the version chooser
        packages: List[Package] = []
        for req in package_requirements.runtime_requirements:
            package = version_chooser.package_for(req.name)
            if package is None:
                raise PackageNotFound(
                    f'Package {req.name} not found in the version chooser'
                )
            packages.append(package)
        kwargs['runtime_requirements'] = packages

        return cls(**kwargs)
