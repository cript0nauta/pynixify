import pytest
from packaging.requirements import Requirement
from pypi2nixpkgs.nixpkgs_sources import (
    NixpkgsData,
)
from pypi2nixpkgs.version_chooser import (
    VersionChooser,
)
from pypi2nixpkgs.exceptions import (
    PackageNotFound,
    NoMatchingVersionFound,
)


ZSTD_DATA = {
    'zstd': [{
        'attr': 'zstd',
        'pypiName': 'zstd',
        'src': "mirror://pypi/z/zstd/zstd-1.4.4.0.tar.gz",
        'version': "1.4.4.0",
    }]
}


MULTIVERSION_DATA = {
    "a": [
        {"attr": "a1", "pypiName": "a", "version": "1.0.1"},
        {"attr": "a24", "pypiName": "a", "version": "2.4"},
        {"attr": "a3", "pypiName": "a", "version": "3.0.0"},
        {"attr": "a2", "pypiName": "a", "version": "2.3"},
    ]
}


@pytest.mark.asyncio
async def test_nixpkgs_package():
    nixpkgs = NixpkgsData(ZSTD_DATA)
    c = VersionChooser(nixpkgs)
    await c.require(Requirement('zstd==1.4.4.0'))

@pytest.mark.asyncio
async def test_invalid_package():
    nixpkgs = NixpkgsData({})
    c = VersionChooser(nixpkgs)
    with pytest.raises(PackageNotFound):
        await c.require(Requirement('zstd==1.4.4.0'))

@pytest.mark.asyncio
async def test_no_matching_version():
    nixpkgs = NixpkgsData(ZSTD_DATA)
    c = VersionChooser(nixpkgs)
    with pytest.raises(NoMatchingVersionFound):
        await c.require(Requirement('zstd>1.4.4.0'))

@pytest.mark.asyncio
async def test_multi_nixpkgs_versions():
    nixpkgs = NixpkgsData(MULTIVERSION_DATA)
    c = VersionChooser(nixpkgs)
    pkg = await c.require(Requirement('a>=2.0.0'))
    assert str(pkg.version) == '3.0.0'
