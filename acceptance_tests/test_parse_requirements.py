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
import tempfile
from pathlib import Path
from packaging.requirements import Requirement
from pynixify.base import PackageMetadata
from pynixify.pypi_api import (
    PyPIData,
    PyPICache,
)
from pynixify.package_requirements import (
    eval_path_requirements
)

@pytest.mark.asyncio
async def test_eval_package_requirements():
    data = PyPIData(PyPICache())
    req = Requirement('faraday-agent_dIspatcher==1.0')
    (package, ) = await data.from_requirement(req)
    path = await package.source()
    reqs = await eval_path_requirements(path)
    assert len(reqs.build_requirements) == 3
    assert len(reqs.test_requirements) == 2
    assert len(reqs.runtime_requirements) == 9
    meta: PackageMetadata = await package.metadata()
    assert meta.url == 'https://github.com/infobyte/faraday_agent_dispatcher'
    assert meta.description == 'Faraday agent dispatcher to communicate an agent to faraday'


@pytest.mark.asyncio
async def test_package_with_tuple_requirements():
    with tempfile.TemporaryDirectory() as dirname:
        with (Path(dirname) / 'setup.py').open('w') as fp:
            fp.write("""
from setuptools import setup
setup(
    setup_requires=('setuptools_scm',),
    tests_require=('pytest', 'pytest-cov'),
    install_requires=('flask', 'jinja', 'werkzeug'),
)
            """)
        reqs = await eval_path_requirements(Path(dirname))
        assert len(reqs.build_requirements) == 1
        assert len(reqs.test_requirements) == 2
        assert len(reqs.runtime_requirements) == 3
