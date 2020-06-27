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

import pytest
from pathlib import Path
from typing import Sequence
from packaging.requirements import Requirement
from pynixify.package_requirements import PackageRequirements

@pytest.mark.asyncio
async def test_package_requirements():
    reqs = PackageRequirements.from_result_path(
        Path(__file__).parent / "parse_setuppy_data_result")

    def has_requirement(r: str, l: Sequence[Requirement]):
        return any(str(e) == r for e in l)

    assert has_requirement('pytest', reqs.test_requirements)
    assert not has_requirement('pytest', reqs.runtime_requirements)
    assert has_requirement('setuptools_scm', reqs.build_requirements)
    assert has_requirement('Click>=6.0', reqs.runtime_requirements)

