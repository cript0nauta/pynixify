import os
import shutil
import asyncio
from packaging.requirements import Requirement
from pypi2nixpkgs.pypi_api import (
    PyPIData,
    PyPICache,
)

async def main():
    data = PyPIData(PyPICache())
    req = Requirement('faraday-agent_dIspatcher==1.0')
    (package, ) = await data.from_requirement(req)
    print(package)
    assert package.sha256 == 'd7a549af9047f1af0d824cf29dd93c5449241266a24e8687d3399cb15bfc61ae'
    path = await package.download_source()
    shutil.copy(path, '/tmp/package.tar.gz')
    os.remove(path)


if __name__ == '__main__':
    asyncio.run(main())
