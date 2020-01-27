import json
import pytest
from pathlib import Path
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name
from packaging.version import Version
from pypi2nixpkgs.exceptions import (
    PackageNotFound,
    IntegrityError,
)
from pypi2nixpkgs.pypi_api import (
    PyPIData,
    PyPIPackage,
)

class DummyCache:
    def __init__(self, **hardcoded_data):
        self.data = {
            canonicalize_name(k): v
            for (k,v) in hardcoded_data.items()
        }

    async def fetch(self, package):
        try:
            return self.data[package]
        except KeyError:
            raise PackageNotFound()


with (Path(__file__).parent / "sampleproject_response.json").open() as fp:
    SAMPLEPROJECT_DATA = json.load(fp)


@pytest.mark.asyncio
async def test_simple_from_requirement():
    data = PyPIData(DummyCache(sampleproject=SAMPLEPROJECT_DATA))
    drvs = await data.from_requirement(Requirement('sampleproject==1.3.1'))
    assert len(drvs) == 1
    drv = drvs[0]
    assert str(drv.version) == '1.3.1'
    assert drv.download_url ==  "https://files.pythonhosted.org/packages/6f/5b/2f3fe94e1c02816fe23c7ceee5292fb186912929e1972eee7fb729fa27af/sampleproject-1.3.1.tar.gz"
    assert drv.sha256 == "3593ca2f1e057279d70d6144b14472fb28035b1da213dde60906b703d6f82c55"

@pytest.mark.asyncio
async def test_canonicalize():
    data = PyPIData(DummyCache(**{"aA-bB_cC": SAMPLEPROJECT_DATA}))
    drvs = await data.from_requirement(Requirement('Aa_Bb-Cc==1.3.1'))

@pytest.mark.asyncio
async def test_invalid_package():
    data = PyPIData(DummyCache(sampleproject=SAMPLEPROJECT_DATA))
    with pytest.raises(PackageNotFound):
        await data.from_requirement(Requirement('xxx==1.3.1'))

@pytest.mark.asyncio
async def test_fetch_blob():
    class Cache(DummyCache):
        async def fetch_url(self, url, filename) -> Path:
            return Path(__file__).parent / "sampleproject_response.json"

    p = PyPIPackage(
        version=Version("1.3.1"),
        sha256='e95ad00f0fd5c0297b7a0b4000e1286994ee4db9df54d9b19ff440b0adbc1eb3',
        download_url='http://mockme',
        pypi_cache=Cache(sampleproject=SAMPLEPROJECT_DATA),
    )
    filename = await p.download_source()
    assert filename.exists()

@pytest.mark.asyncio
async def test_fetch_blob_fails():
    class Cache(DummyCache):
        async def fetch_url(self, url, filename) -> Path:
            return Path('/dev/null')

    p = PyPIPackage(
        version=Version("1.3.1"),
        sha256='e95ad00f0fd5c0297b7a0b4000e1286994ee4db9df54d9b19ff440b0adbc1eb3',
        download_url='http://mockme',
        pypi_cache=Cache(sampleproject=SAMPLEPROJECT_DATA),
    )
    with pytest.raises(IntegrityError):
        await p.download_source()


def test_package_filename():
    p = PyPIPackage(
        version=Version("1.3.1"),
        sha256='e95ad00f0fd5c0297b7a0b4000e1286994ee4db9df54d9b19ff440b0adbc1eb3',
        download_url='https://files.pythonhosted.org/packages/7f/7b/7627af71aaf127014238040b78ad8eaf416facda3d0755af69f382399c36/faraday_agent_dispatcher-1.0.tar.gz',
        pypi_cache=None,
    )
    assert p.filename == 'faraday_agent_dispatcher-1.0.tar.gz'
