import operator
from typing import Mapping, Callable, Awaitable
from packaging.requirements import Requirement
from pypi2nixpkgs.base import Package
from packaging.utils import canonicalize_name
from pypi2nixpkgs.nixpkgs_sources import NixpkgsData
from pypi2nixpkgs.package_requirements import PackageRequirements
from pypi2nixpkgs.exceptions import (
    NoMatchingVersionFound,
)

class VersionChooser:
    F_TYPE = Callable[[Package], Awaitable[PackageRequirements]]
    def __init__(self, nixpkgs_data: NixpkgsData, req_evaluate: F_TYPE):
        self.nixpkgs_data = nixpkgs_data
        self.choosed_packages: Mapping[str, Package] = {}
        self.evaluate_requirements = req_evaluate

    async def require(self, r: Requirement):
        try:
            pkg = self.choosed_packages[canonicalize_name(r.name)]
        except KeyError:
            pass
        else:
            if pkg.version not in r.specifier:
                raise NoMatchingVersionFound(
                    f'{r.name}=={str(pkg.version)} does not match {r}'
                )
        pkgs = self.nixpkgs_data.from_requirement(r)
        if not pkgs:
            raise NoMatchingVersionFound(str(r))
        pkg = max(pkgs, key=operator.attrgetter('version'))
        self.choosed_packages[canonicalize_name(r.name)] = pkg
        reqs: PackageRequirements = await self.evaluate_requirements(pkg)
        for req in reqs.runtime_requirements:
            if canonicalize_name(req.name) in self.choosed_packages:
                continue
            await self.require(req)
        for req in reqs.test_requirements:
            if canonicalize_name(req.name) in self.choosed_packages:
                continue
            await self.require(req)

    def package_for(self, package_name: str) -> Package:
        return self.choosed_packages.get(canonicalize_name(package_name))
