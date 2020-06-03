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
    ABCPyPICache,
    PyPICache,
    PyPIData,
    PyPIPackage,
    get_path_hash,
)

class DummyCache(ABCPyPICache):
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

    async def fetch_url(self, url, sha256) -> Path:
        raise NotImplementedError()


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
    assert drv.pypi_name == 'sampleproject'
    assert drv.attr == 'sampleproject'

@pytest.mark.asyncio
async def test_canonicalize():
    data = PyPIData(DummyCache(**{"aA-bB_cC": SAMPLEPROJECT_DATA}))
    drvs = await data.from_requirement(Requirement('Aa_Bb-Cc==1.3.1'))
    assert drvs[0].pypi_name == 'aa-bb-cc'
    assert drvs[0].attr == 'aa-bb-cc'

@pytest.mark.asyncio
async def test_invalid_package():
    data = PyPIData(DummyCache(sampleproject=SAMPLEPROJECT_DATA))
    with pytest.raises(PackageNotFound):
        await data.from_requirement(Requirement('xxx==1.3.1'))

@pytest.mark.asyncio
async def test_fetch_blob():
    class Cache(DummyCache):
        async def fetch_url(self, url, sha256) -> Path:
            return Path(__file__).parent / "sampleproject_response.json"

    p = PyPIPackage(
        pypi_name='sampleproject',
        version=Version("1.3.1"),
        sha256='e95ad00f0fd5c0297b7a0b4000e1286994ee4db9df54d9b19ff440b0adbc1eb3',
        download_url='http://mockme',
        pypi_cache=Cache(sampleproject=SAMPLEPROJECT_DATA),
    )
    filename = await p.source()
    assert filename.exists()

@pytest.mark.asyncio
async def test_fetch_blob_fails():
    class Cache(DummyCache):
        async def fetch_url(self, url, sha256) -> Path:
            return Path('/dev/null')

    p = PyPIPackage(
        pypi_name='sampleproject',
        version=Version("1.3.1"),
        sha256='e95ad00f0fd5c0297b7a0b4000e1286994ee4db9df54d9b19ff440b0adbc1eb3',
        download_url='http://mockme',
        pypi_cache=Cache(sampleproject=SAMPLEPROJECT_DATA),
    )
    with pytest.raises(IntegrityError):
        await p.source()


def test_package_filename():
    p = PyPIPackage(
        pypi_name='sampleproject',
        version=Version("1.3.1"),
        sha256='e95ad00f0fd5c0297b7a0b4000e1286994ee4db9df54d9b19ff440b0adbc1eb3',
        download_url='https://files.pythonhosted.org/packages/7f/7b/7627af71aaf127014238040b78ad8eaf416facda3d0755af69f382399c36/faraday_agent_dispatcher-1.0.tar.gz',
        pypi_cache=None,  # type: ignore
    )
    assert p.filename == 'faraday_agent_dispatcher-1.0.tar.gz'


@pytest.mark.usesnix
@pytest.mark.asyncio
async def test_get_path_hash():
    path = (Path(__file__).parent / "random_file")
    hash_ = await get_path_hash(path)
    assert hash_ == '0adj0mj17yafd2imz49v3qklys2h8zf4hh443sx0ql8xibf8wpzq'


@pytest.mark.usesnix
@pytest.mark.asyncio
async def test_content_addressable_pypi_cache():
    cache = PyPICache()
    sha256 = 'f85f8edc8a1d510cba1e844048dc4750684f271e3b915fa3684ef9136405b229'  # sha256sum of ranodm_file
    path: Path = await cache.fetch_url(
        'http://ignoreme.com/random_file', sha256)
    assert path == Path('/nix/store/678nlplmwnm46ian5jh0yb3q7y7hj9vr-random_file')
    assert path.exists()
