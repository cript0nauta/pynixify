import os
import shutil
import pytest
from packaging.requirements import Requirement
from pypi2nixpkgs.pypi_api import (
    PyPIData,
    PyPICache,
)
from pypi2nixpkgs.package_requirements import (
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
