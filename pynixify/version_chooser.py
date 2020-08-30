# pynixify - Nix expression generator for Python packages
# Copyright (C) 2020 Matías Lang

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import asyncio
import operator
from pathlib import Path
from dataclasses import dataclass
from typing import Any, Dict, Callable, Awaitable, Optional, List, Tuple
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name
from packaging.specifiers import SpecifierSet
from pynixify.base import Package
from pynixify.nixpkgs_sources import NixpkgsData, NixPackage
from pynixify.pypi_api import PyPIData, PyPIPackage
from pynixify.package_requirements import (
    PackageRequirements,
    eval_path_requirements,
)
from pynixify.exceptions import (
    NoMatchingVersionFound,
    PackageNotFound,
)

class VersionChooser:
    def __init__(self, nixpkgs_data: NixpkgsData, pypi_data: PyPIData,
                 req_evaluate: Callable[[Package], Awaitable[PackageRequirements]],
                 should_load_tests: Callable[[str], bool] = lambda _: False,
                 ):
        self.nixpkgs_data = nixpkgs_data
        self.pypi_data = pypi_data
        self._choosed_packages: Dict[str, Tuple[Package, SpecifierSet]] = {}
        self._local_packages: Dict[str, Package] = {}
        self.evaluate_requirements = req_evaluate
        self.should_load_tests = should_load_tests

    async def require(self, r: Requirement, coming_from: Optional[Package]=None):
        pkg: Package

        if r.marker and not r.marker.evaluate():
            return

        try:
            self.nixpkgs_data.from_requirement(r)
        except PackageNotFound:
            is_in_nixpkgs = False
        else:
            is_in_nixpkgs = True
        if (isinstance(coming_from, NixPackage) and
                is_in_nixpkgs and
                not self.nixpkgs_data.from_requirement(r)):
            # This shouldn't happen in an ideal world. Unfortunately,
            # nixpkgs does some patching to packages to disable some
            # requirements. Because we don't use these patches, the
            # dependency resolution would fail if we don't ignore the
            # requirement.
            print(f"warning: ignoring requirement {r} from {coming_from} "
                  f"because there is no matching version in nixpkgs packages")
            return

        print(f'Resolving {r}{f" (from {coming_from})" if coming_from else ""}')

        try:
            (pkg, specifier) = self._choosed_packages[canonicalize_name(r.name)]
        except KeyError:
            pass
        else:
            specifier &= r.specifier
            self._choosed_packages[canonicalize_name(r.name)] = (pkg, specifier)
            if pkg.version not in specifier:
                raise NoMatchingVersionFound(
                    f'New requirement '
                    f'{r}{f" (from {coming_from})" if coming_from else ""} '
                    f'does not match already installed {r.name}=={str(pkg.version)}'
                )
            return

        # TODO improve mypy signatures to make this possible
        # pkgs = await self.pypi_data.from_requirement(r)
        # pkgs += self.nixpkgs_data.from_requirement(r)
        pkgs: List[Package] = []

        found_pypi = True
        found_nixpkgs = True

        if canonicalize_name(r.name) in self._local_packages:
            pkg = self._local_packages[canonicalize_name(r.name)]
        else:
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

        if isinstance(pkg, NixPackage) or (
                not self.should_load_tests(canonicalize_name(r.name))):
            reqs.test_requirements = []

        await asyncio.gather(*(
            self.require(req, coming_from=pkg)
            for req in (reqs.runtime_requirements + reqs.test_requirements +
                        reqs.build_requirements)
        ))

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
            version_chooser: VersionChooser,
            load_tests: bool):
        kwargs: Any = {}

        kwargs['build_requirements'] = []
        for req in package_requirements.build_requirements:
            if req.marker and not req.marker.evaluate():
                continue
            package = version_chooser.package_for(req.name)
            if package is None:
                raise PackageNotFound(
                    f'Package {req.name} not found in the version chooser'
                )
            kwargs['build_requirements'].append(package)

        # tests_requirements uses the packages in the version chooser
        packages: List[Package] = []
        if load_tests:
            for req in package_requirements.test_requirements:
                if req.marker and not req.marker.evaluate():
                    continue
                package = version_chooser.package_for(req.name)
                if package is None:
                    raise PackageNotFound(
                        f'Package {req.name} not found in the version chooser'
                    )
                packages.append(package)
        kwargs['test_requirements'] = packages

        # runtime_requirements uses the packages in the version chooser
        packages = []
        for req in package_requirements.runtime_requirements:
            if req.marker and not req.marker.evaluate():
                continue
            package = version_chooser.package_for(req.name)
            if package is None:
                raise PackageNotFound(
                    f'Package {req.name} not found in the version chooser'
                )
            packages.append(package)
        kwargs['runtime_requirements'] = packages

        return cls(**kwargs)
