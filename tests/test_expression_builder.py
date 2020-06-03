import json
import asyncio
import pytest
from typing import List
from packaging.requirements import Requirement
from pypi2nixpkgs.base import PackageMetadata
from pypi2nixpkgs.version_chooser import VersionChooser
from pypi2nixpkgs.nixpkgs_sources import (
    NixpkgsData,
)
from pypi2nixpkgs.pypi_api import (
    PyPIData,
    nix_instantiate,
)
from pypi2nixpkgs.expression_builder import (
    build_nix_expression,
    escape_string,
    nixfmt
)
from .test_pypi_api import DummyCache, SAMPLEPROJECT_DATA
from .test_version_chooser import (
    NIXPKGS_JSON,
    ChosenPackageRequirements,
    dummy_package_requirements,
)


DEFAULT_ARGS = {
    'fetchPypi': 'a: a',
    'buildPythonPackage': 'a: a',
    'lib': 'a: a',
}

NO_REQUIREMENTS = ChosenPackageRequirements(
    build_requirements=[],
    test_requirements=[],
    runtime_requirements=[]
)

NO_METADATA = PackageMetadata(
    url=None,
    description=None,
    license=None,
)


async def is_valid_nix(expr: str, attr=None, **kwargs) -> bool:
    extra_args: List[str] = []
    if attr is not None:
        extra_args += ['--attr', attr]
    for (k, v) in kwargs.items():
        extra_args += ['--arg', k, v]

    proc = await asyncio.create_subprocess_exec(
        'nix-instantiate', '--eval', '-', *extra_args,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.DEVNULL,
    )
    proc.stdin.write(expr.encode())  # type: ignore
    proc.stdin.write_eof()  # type: ignore
    status = await proc.wait()
    return status == 0


@pytest.fixture
def version_chooser():
    nixpkgs = NixpkgsData(NIXPKGS_JSON)
    pypi = PyPIData(DummyCache(sampleproject=SAMPLEPROJECT_DATA))
    return VersionChooser(nixpkgs, pypi, dummy_package_requirements())


@pytest.mark.usesnix
@pytest.mark.asyncio
async def test_compiles(version_chooser):
    await version_chooser.require(Requirement("sampleproject"))
    result = build_nix_expression(
        version_chooser.package_for('sampleproject'),
        NO_REQUIREMENTS,
        NO_METADATA,
        sha256='aaaaaa')
    assert await is_valid_nix(result), "Invalid Nix expression"


@pytest.mark.usesnix
@pytest.mark.asyncio
async def test_duplicate_parameter(version_chooser):
    await version_chooser.require(Requirement('pytest'))
    await version_chooser.require(Requirement("sampleproject"))
    pytest = version_chooser.package_for('pytest')  # type: ignore
    requirements = ChosenPackageRequirements(
        build_requirements=[pytest],
        test_requirements=[pytest],
        runtime_requirements=[pytest]
    )
    result = build_nix_expression(
        version_chooser.package_for('sampleproject'),
        requirements,
        NO_METADATA,
        sha256='aaaaaa')
    assert await is_valid_nix(result), "Invalid Nix expression"


@pytest.mark.usesnix
@pytest.mark.asyncio
async def test_call(version_chooser):
    await version_chooser.require(Requirement("sampleproject"))
    result = build_nix_expression(
        version_chooser.package_for('sampleproject'),
        NO_REQUIREMENTS,
        NO_METADATA,
        sha256='aaaaaa')
    assert await is_valid_nix(result, **DEFAULT_ARGS), "Invalid Nix expression"


@pytest.mark.usesnix
@pytest.mark.asyncio
async def test_nixfmt():
    expr = await nixfmt('{}: 1 + 1')
    assert await is_valid_nix(expr)

@pytest.mark.usesnix
@pytest.mark.asyncio
async def test_metadata(version_chooser):
    await version_chooser.require(Requirement("sampleproject"))
    desc = "${builtins.abort builtins.currentSystem}"
    result = build_nix_expression(
        version_chooser.package_for('sampleproject'),
        NO_REQUIREMENTS,
        sha256='aaaaaa',
        metadata=PackageMetadata(
            description=desc,
            url=None,
            license=None,
        ))
    assert await nix_instantiate(
        result,
        attr='meta.description',
        **DEFAULT_ARGS) == desc

@pytest.mark.usesnix
@pytest.mark.asyncio
@pytest.mark.parametrize('string', [
    'test',
    '\\',
    '"',
    "'",
    'a\n',
    '${builtins.abort builtins.currentSystem}',
])
async def test_escape_string(string):
    expr = escape_string(string)
    assert await nix_instantiate(expr) == string
