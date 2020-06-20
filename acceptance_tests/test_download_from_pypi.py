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
