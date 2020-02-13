import asyncio
import pytest
from typing import List
from packaging.requirements import Requirement
from pypi2nixpkgs.version_chooser import VersionChooser
from pypi2nixpkgs.nixpkgs_sources import (
    NixpkgsData,
)
from pypi2nixpkgs.pypi_api import (
    PyPIData,
)
from pypi2nixpkgs.expression_builder import build_nix_expression
from .test_pypi_api import DummyCache, SAMPLEPROJECT_DATA
from .test_version_chooser import (
    NIXPKGS_JSON,
    ChosenPackageRequirements,
    dummy_package_requirements,
)


DEFAULT_ARGS = {
    'fetchPypi': 'a: a',
    'buildPythonPackage': 'a: a',
}

NO_REQUIREMENTS = ChosenPackageRequirements(
    build_requirements=[],
    test_requirements=[],
    runtime_requirements=[]
)


async def is_valid_nix(expr: str, **kwargs) -> bool:
    extra_args: List[str] = []
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


@pytest.mark.asyncio
async def test_compiles(version_chooser):
    await version_chooser.require(Requirement("sampleproject"))
    result = build_nix_expression(
        version_chooser.package_for('sampleproject'),
        NO_REQUIREMENTS,
        sha256='aaaaaa')
    assert await is_valid_nix(result), "Invalid Nix expression"


@pytest.mark.asyncio
async def test_call(version_chooser):
    await version_chooser.require(Requirement("sampleproject"))
    result = build_nix_expression(
        version_chooser.package_for('sampleproject'),
        NO_REQUIREMENTS,
        sha256='aaaaaa')
    assert await is_valid_nix(result, **DEFAULT_ARGS), "Invalid Nix expression"
