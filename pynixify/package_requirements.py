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

from dataclasses import dataclass
from pathlib import Path
from typing import List

from packaging.requirements import Requirement
from pkg_resources import parse_requirements

from pynixify.exceptions import NixBuildError
from pynixify.nixpkgs_sources import run_nix_build


@dataclass
class PackageRequirements:
    build_requirements: List[Requirement]
    test_requirements: List[Requirement]
    runtime_requirements: List[Requirement]

    @classmethod
    def from_result_path(cls, result_path: Path):
        attr_mapping = {
            "build_requirements": Path("setup_requires.txt"),
            "test_requirements": Path("tests_requires.txt"),
            "runtime_requirements": Path("install_requires.txt"),
        }
        kwargs = {}
        for attr, filename in attr_mapping.items():
            with (result_path / filename).open() as fp:
                # Convert from Requirement.parse to Requirement
                reqs = [Requirement(str(r)) for r in parse_requirements(fp)]
                kwargs[attr] = reqs
        return cls(**kwargs)


async def eval_path_requirements(path: Path) -> PackageRequirements:
    nix_expression_path = Path(__file__).parent / "data" / "parse_setuppy_data.nix"
    if path.name.endswith(".whl"):
        # Some nixpkgs packages use a wheel as source, which don't have a
        # setup.py file. For now, ignore them assume they have no dependencies
        print(
            f"{path} is a wheel file instead of a source distribution. "
            f"Assuming it has no dependencies."
        )
        return PackageRequirements(
            build_requirements=[], test_requirements=[], runtime_requirements=[]
        )
    assert nix_expression_path.exists()
    nix_store_path = await run_nix_build(
        str(nix_expression_path),
        "--no-out-link",
        "--no-build-output",
        "--arg",
        "file",
        str(path.resolve()),
    )
    if (nix_store_path / "failed").exists():
        print(f"Error parsing requirements of {path}. Assuming it has no dependencies.")
        return PackageRequirements(
            build_requirements=[],
            test_requirements=[],
            runtime_requirements=[],
        )
    return PackageRequirements.from_result_path(nix_store_path)
