import operator
from packaging.requirements import Requirement
from pypi2nixpkgs.nixpkgs_sources import NixpkgsData
from pypi2nixpkgs.exceptions import (
    NoMatchingVersionFound,
)

class VersionChooser:
    def __init__(self, nixpkgs_data: NixpkgsData):
        self.nixpkgs_data = nixpkgs_data

    async def require(self, r: Requirement):
        drvs = self.nixpkgs_data.from_requirement(r)
        if not drvs:
            raise NoMatchingVersionFound(str(r))
        return max(drvs, key=operator.attrgetter('version'))

