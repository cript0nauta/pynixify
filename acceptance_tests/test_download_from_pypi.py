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

import os
import shutil
import pytest
from packaging.requirements import Requirement
from pynixify.pypi_api import (
    PyPIData,
    PyPICache,
)

@pytest.mark.asyncio
async def test_download_from_pypi():
    data = PyPIData(PyPICache())
    req = Requirement('faraday-agent_dIspatcher==1.0')
    (package, ) = await data.from_requirement(req)
    print(package)
    assert package.sha256 == 'd7a549af9047f1af0d824cf29dd93c5449241266a24e8687d3399cb15bfc61ae'
    path = await package.source()
