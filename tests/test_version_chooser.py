import json
import pytest
from pathlib import Path
from pypi2nixpkgs.base import Package
from packaging.requirements import Requirement
from pypi2nixpkgs.package_requirements import PackageRequirements
from pypi2nixpkgs.nixpkgs_sources import (
    NixpkgsData,
    NixPackage,
)
from pypi2nixpkgs.pypi_api import (
    PyPIData,
    PyPIPackage,
)
from pypi2nixpkgs.version_chooser import (
    VersionChooser,
)
from pypi2nixpkgs.exceptions import (
    NoMatchingVersionFound,
    PackageNotFound,
)
from .test_pypi_api import DummyCache, SAMPLEPROJECT_DATA


ZSTD_DATA = {
    'zstd': [{
        'attr': 'zstd',
        'pypiName': 'zstd',
        'src': "mirror://pypi/z/zstd/zstd-1.4.4.0.tar.gz",
        'version': "1.4.4.0",
    }]
}

NIXPKGS_SAMPLEPROJECT = {
    'sampleproject': [{
        'attr': 'anything',
        'pypiName': 'sampleproject',
        'src': "mirror://pypi/s/sampleproject/sampleproject-1.0.tar.gz",
        'version': "1.0",
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

dummy_pypi = PyPIData(DummyCache())


with (Path(__file__).parent / "nixpkgs_packages.json").open() as fp:
    NIXPKGS_JSON = json.load(fp)


def dummy_package_requirements(hardcoded_reqs={}):
    async def f(package: Package) -> PackageRequirements:
        nonlocal hardcoded_reqs
        if isinstance(package, NixPackage):
            key = package.attr
        elif isinstance(package, PyPIPackage):
            key = Path(package.download_url).name.split('-')[0]
        else:
            raise NotImplementedError()
        (b, t, r) = hardcoded_reqs.get(key, ([], [], []))
        reqs = PackageRequirements(b, t, r)
        return reqs
    return f


def assert_version(c: VersionChooser, package_name: str, version: str):
    p = c.package_for(package_name)
    assert p is not None
    assert str(p.version) == version


@pytest.mark.asyncio
async def test_nixpkgs_package():
    nixpkgs = NixpkgsData(ZSTD_DATA)
    c = VersionChooser(nixpkgs, dummy_pypi, dummy_package_requirements())
    await c.require(Requirement('zstd==1.4.4.0'))


@pytest.mark.asyncio
async def test_package_for_canonicalizes():
    nixpkgs = NixpkgsData(ZSTD_DATA)
    c = VersionChooser(nixpkgs, dummy_pypi, dummy_package_requirements())
    await c.require(Requirement('ZSTD==1.4.4.0'))
    assert c.package_for('zstd') is c.package_for('ZSTD')


@pytest.mark.asyncio
async def test_invalid_package():
    nixpkgs = NixpkgsData({})
    c = VersionChooser(nixpkgs, dummy_pypi, dummy_package_requirements())
    with pytest.raises(PackageNotFound):
        await c.require(Requirement('zstd==1.4.4.0'))


@pytest.mark.asyncio
async def test_no_matching_version():
    nixpkgs = NixpkgsData(ZSTD_DATA)
    c = VersionChooser(nixpkgs, dummy_pypi, dummy_package_requirements())
    with pytest.raises(NoMatchingVersionFound):
        await c.require(Requirement('zstd>1.4.4.0'))


@pytest.mark.asyncio
async def test_no_matching_version_on_second_require():
    nixpkgs = NixpkgsData(ZSTD_DATA)
    c = VersionChooser(nixpkgs, dummy_pypi, dummy_package_requirements())
    await c.require(Requirement('zstd==1.4.4.0'))
    with pytest.raises(NoMatchingVersionFound):
        await c.require(Requirement('zstd<1.4.4.0'))

@pytest.mark.asyncio
async def test_no_matching_version_with_previous_requirements():
    nixpkgs = NixpkgsData(NIXPKGS_JSON)
    c = VersionChooser(nixpkgs, dummy_pypi, dummy_package_requirements())
    await c.require(Requirement('django==2.1.14'))
    with pytest.raises(NoMatchingVersionFound):
        await c.require(Requirement('django>=2.2'))


@pytest.mark.asyncio
async def test_multi_nixpkgs_versions():
    nixpkgs = NixpkgsData(MULTIVERSION_DATA)
    c = VersionChooser(nixpkgs, dummy_pypi, dummy_package_requirements())
    await c.require(Requirement('a>=2.0.0'))
    assert_version(c, 'a', '3.0.0')


@pytest.mark.asyncio
async def test_uses_runtime_dependencies():
    nixpkgs = NixpkgsData(NIXPKGS_JSON)
    c = VersionChooser(nixpkgs, dummy_pypi, dummy_package_requirements({
        "django_2_2": ([], [], [Requirement('pytz')]),
    }))
    await c.require(Requirement('django>=2.2'))
    assert c.package_for('django')
    assert c.package_for('pytz')
    assert_version(c, 'pytz', '2019.3')


@pytest.mark.asyncio
@pytest.mark.xfail(reason='Test dependencies are not used for now')
async def test_uses_test_dependencies():
    nixpkgs = NixpkgsData(NIXPKGS_JSON)
    c = VersionChooser(nixpkgs, dummy_pypi, dummy_package_requirements({
        "django_2_2": ([], [Requirement('pytest')], []),
    }))
    await c.require(Requirement('django>=2.2'))
    assert c.package_for('django')
    assert c.package_for('pytest') is not None


@pytest.mark.asyncio
async def test_does_not_user_build_dependencies():
    nixpkgs = NixpkgsData(NIXPKGS_JSON)
    c = VersionChooser(nixpkgs, dummy_pypi, dummy_package_requirements({
        "pytz": ([Requirement('setuptools_scm')], [], []),
    }))
    await c.require(Requirement('pytz'))
    assert c.package_for('pytz')
    assert c.package_for('setuptools_scm') is None

@pytest.mark.asyncio
async def test_nixpkgs_transitive():
    nixpkgs = NixpkgsData(NIXPKGS_JSON)
    c = VersionChooser(nixpkgs, dummy_pypi, dummy_package_requirements({
        'flask': ([], [], [Requirement("itsdangerous")]),
        'itsdangerous': ([], [], [Requirement('Werkzeug')]),
    }))
    await c.require(Requirement('flask'))
    assert c.package_for('flask')
    assert c.package_for('itsdangerous')
    assert c.package_for('Werkzeug')


@pytest.mark.asyncio
async def test_circular_dependencies():
    nixpkgs = NixpkgsData(NIXPKGS_JSON)
    c = VersionChooser(nixpkgs, dummy_pypi, dummy_package_requirements({
        'flask': ([], [], [Requirement("itsdangerous")]),
        'itsdangerous': ([], [Requirement('flask')], []),
    }))
    await c.require(Requirement('flask'))
    assert c.package_for('flask')
    assert c.package_for('itsdangerous')

@pytest.mark.asyncio
async def test_pypi_package():
    nixpkgs = NixpkgsData(NIXPKGS_JSON)
    pypi = PyPIData(DummyCache(sampleproject=SAMPLEPROJECT_DATA))
    c = VersionChooser(nixpkgs, pypi, dummy_package_requirements())
    await c.require(Requirement('sampleproject'))
    assert_version(c, 'sampleproject', '1.3.1')

@pytest.mark.asyncio
async def test_prefer_nixpkgs_older_version():
    nixpkgs = NixpkgsData(NIXPKGS_SAMPLEPROJECT)
    pypi = PyPIData(DummyCache(sampleproject=SAMPLEPROJECT_DATA))
    c = VersionChooser(nixpkgs, pypi, dummy_package_requirements())
    await c.require(Requirement('sampleproject'))
    assert_version(c, 'sampleproject', '1.0')
    with pytest.raises(NoMatchingVersionFound):
        await c.require(Requirement('sampleproject>1.0'))

@pytest.mark.asyncio
async def test_pypi_dependency_uses_nixpkgs_dependency():
    nixpkgs = NixpkgsData(NIXPKGS_JSON)
    pypi = PyPIData(DummyCache(sampleproject=SAMPLEPROJECT_DATA))
    c = VersionChooser(nixpkgs, pypi, dummy_package_requirements({
        "sampleproject": ([], [], [Requirement('flask')]),
    }))
    await c.require(Requirement('sampleproject'))
    assert c.package_for('sampleproject')
    assert c.package_for('flask')

@pytest.mark.asyncio
async def test_conflicting_versions():
    data = NIXPKGS_JSON.copy()
    data.update(NIXPKGS_SAMPLEPROJECT)
    nixpkgs = NixpkgsData(data)
    pypi = PyPIData(DummyCache(sampleproject=SAMPLEPROJECT_DATA))
    c = VersionChooser(nixpkgs, pypi, dummy_package_requirements({
        "flask": ([], [], [Requirement('sampleproject==1.0')]),
        "click": ([], [], [Requirement('sampleproject>1.0')]),
    }))
    await c.require(Requirement('flask'))
    assert c.package_for('flask')
    with pytest.raises(NoMatchingVersionFound):
        await c.require(Requirement('click'))

@pytest.mark.asyncio
async def test_python_version_marker():
    nixpkgs = NixpkgsData(NIXPKGS_JSON)
    c = VersionChooser(nixpkgs, dummy_pypi, dummy_package_requirements())
    await c.require(Requirement("flask; python_version<'3'"))
    assert c.package_for('flask') is None
