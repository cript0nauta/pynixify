import pytest
import asyncio
import tempfile
from pathlib import Path
from packaging.requirements import Requirement
from packaging.version import parse
from pypi2nixpkgs.nixpkgs_sources import (
    load_nixpkgs_data,
    NixpkgsData,
)
from pypi2nixpkgs.pypi_api import (
    PyPICache,
    PyPIData,
)
from pypi2nixpkgs.package_requirements import (
    eval_path_requirements,
)
from pypi2nixpkgs.version_chooser import (
    VersionChooser,
    ChosenPackageRequirements,
    evaluate_package_requirements,
)
from pypi2nixpkgs.expression_builder import (
    build_nix_expression,
    build_overlayed_nixpkgs,
)
from pypi2nixpkgs.pypi_api import PyPIPackage, get_path_hash
from tests.test_version_chooser import assert_version, dummy_pypi

PINNED_NIXPKGS_ARGS = ['-I', 'nixpkgs=https://github.com/NixOS/nixpkgs/archive/845b911ac2150066538e1063ec3c409dbf8647bc.tar.gz']


@pytest.mark.asyncio
async def test_all():
    data = await load_nixpkgs_data(PINNED_NIXPKGS_ARGS)
    repo = NixpkgsData(data)
    (django, ) = repo.from_requirement(Requirement('django>=2.2'))
    assert django.version == parse('2.2.9')
    assert django.attr == 'django_2_2'
    nix_store_path = await django.source(PINNED_NIXPKGS_ARGS)
    assert nix_store_path == Path('/nix/store/560jpg1ilahfs1j0xw4s0z6fld2a8fq5-Django-2.2.9.tar.gz')
    reqs = await eval_path_requirements(nix_store_path)
    assert not reqs.build_requirements
    assert not reqs.test_requirements
    assert len(reqs.runtime_requirements) == 2

    async def f(pkg):
        return await evaluate_package_requirements(pkg, PINNED_NIXPKGS_ARGS)
    c = VersionChooser(repo, dummy_pypi, f)
    await c.require(Requirement('flask'))
    assert_version(c, 'flask', '1.0.4')
    assert_version(c, 'itsdangerous', '1.1.0')
    assert_version(c, 'Werkzeug', '0.15.5')


@pytest.mark.asyncio
async def test_version_chooser_pypi_and_nixpkgs():
    data = await load_nixpkgs_data(PINNED_NIXPKGS_ARGS)
    nixpkgs = NixpkgsData(data)
    pypi = PyPIData(PyPICache())
    async def f(pkg):
        return await evaluate_package_requirements(pkg, PINNED_NIXPKGS_ARGS)
    c = VersionChooser(nixpkgs, pypi, f)

    await c.require(Requirement('faraday-agent-dispatcher==1.0'))
    assert c.package_for('faraday-agent-dispatcher')
    assert c.package_for('click')
    assert c.package_for('websockets')
    assert c.package_for('syslog_rfc5424_formatter')


async def run_nix_build(expr: str) -> Path:
    proc = await asyncio.create_subprocess_exec(
        'nix-build', '-Q', '-E', '-',
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE)
    proc.stdin.write(expr.encode())  # type: ignore
    proc.stdin.write_eof()  # type: ignore
    stdout, stderr = await proc.communicate()
    assert (await proc.wait()) == 0
    return Path(stdout.splitlines()[-1].decode())


@pytest.mark.asyncio
async def test_run_nix_build():
    result = await run_nix_build('with (import <nixpkgs> {}); hello')
    proc = await asyncio.create_subprocess_shell(
        f'{result}/bin/hello',
        stdout=asyncio.subprocess.PIPE)
    stdout, stderr = await proc.communicate()
    assert (await proc.wait()) == 0
    assert b'Hello, world!' in stdout


@pytest.mark.asyncio
async def test_build_sampleproject_expression():
    data = await load_nixpkgs_data(PINNED_NIXPKGS_ARGS)
    nixpkgs = NixpkgsData(data)
    pypi = PyPIData(PyPICache())
    async def f(pkg):
        return await evaluate_package_requirements(pkg, PINNED_NIXPKGS_ARGS)
    c = VersionChooser(nixpkgs, pypi, f)
    await c.require(Requirement('sampleproject==1.3.1'))
    package: PyPIPackage = c.package_for('sampleproject')  # type: ignore
    sha256 = await get_path_hash(await package.source())
    reqs = ChosenPackageRequirements(
        build_requirements=[],
        test_requirements=[],
        runtime_requirements=[c.package_for('peppercorn')]  # type: ignore
    )
    expr = build_nix_expression(package, reqs, sha256)

    print(expr)
    wrapper_expr = f'(import <nixpkgs> {{}}).python3.pkgs.callPackage ({expr}) {{}}'
    print(wrapper_expr)

    result = await run_nix_build(wrapper_expr)
    proc = await asyncio.create_subprocess_shell(
        f'{result}/bin/sample',
        stdout=asyncio.subprocess.PIPE)
    stdout, stderr = await proc.communicate()
    assert (await proc.wait()) == 0
    assert b'Call your main application code here' in stdout


@pytest.mark.asyncio
async def test_build_sampleproject_nixpkgs():
    data = await load_nixpkgs_data(PINNED_NIXPKGS_ARGS)
    nixpkgs = NixpkgsData(data)
    pypi = PyPIData(PyPICache())
    async def f(pkg):
        return await evaluate_package_requirements(pkg, PINNED_NIXPKGS_ARGS)
    c = VersionChooser(nixpkgs, pypi, f)
    await c.require(Requirement('sampleproject==1.3.1'))
    package: PyPIPackage = c.package_for('sampleproject')  # type: ignore
    sha256 = await get_path_hash(await package.source())
    reqs = ChosenPackageRequirements(
        build_requirements=[],
        test_requirements=[],
        runtime_requirements=[c.package_for('peppercorn')]  # type: ignore
    )
    sampleproject_expr = build_nix_expression(
        package, reqs, sha256)

    with tempfile.NamedTemporaryFile(suffix='.nix') as fp:
        fp.write(sampleproject_expr.encode())
        fp.flush()
        nixpkgs_expr = build_overlayed_nixpkgs({'sampleproject': Path(fp.name)})
        print(nixpkgs_expr)
        wrapper_expr = f"""(({nixpkgs_expr}) {{}}).python3.pkgs.sampleproject"""
        result = await run_nix_build(wrapper_expr)

    proc = await asyncio.create_subprocess_shell(
        f'{result}/bin/sample',
        stdout=asyncio.subprocess.PIPE)
    stdout, stderr = await proc.communicate()
    assert (await proc.wait()) == 0
    assert b'Call your main application code here' in stdout
