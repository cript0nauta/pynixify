# pynixify - Nix expression generator for Python packages
# Copyright (C) 2020 Matías Lang

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import re
import sys
import pytest
import asyncio
import tempfile
from pathlib import Path
from packaging.requirements import Requirement
from packaging.version import Version, parse
from pynixify.nixpkgs_sources import (
    load_nixpkgs_data,
    load_nixpkgs_version,
    NixpkgsData,
)
from pynixify.pypi_api import (
    PyPICache,
    PyPIData,
)
from pynixify.package_requirements import (
    eval_path_requirements,
)
from pynixify.version_chooser import (
    VersionChooser,
    ChosenPackageRequirements,
    evaluate_package_requirements,
)
from pynixify.expression_builder import (
    build_nix_expression,
    build_overlayed_nixpkgs,
)
from pynixify.pypi_api import PyPIPackage, get_path_hash
from tests.test_version_chooser import assert_version, dummy_pypi

PINNED_NIXPKGS_ARGS = ['-I', 'nixpkgs=https://github.com/NixOS/nixpkgs/archive/4364ff933ebec0ef856912b182f4f9272aa7f98f.tar.gz']


@pytest.mark.asyncio
async def test_all():
    data = await load_nixpkgs_data(PINNED_NIXPKGS_ARGS)
    repo = NixpkgsData(data)
    django = repo.from_requirement(Requirement('django>=2.0'))[0]
    assert django.version == parse('2.2.14')
    nix_store_path = await django.source(PINNED_NIXPKGS_ARGS)
    assert nix_store_path == Path('/nix/store/1b47170f04xir2vfwxjl2a59mjsrskaq-Django-2.2.14.tar.gz')
    reqs = await eval_path_requirements(nix_store_path)
    assert not reqs.build_requirements
    assert not reqs.test_requirements
    assert len(reqs.runtime_requirements) == 2

    async def f(pkg):
        return await evaluate_package_requirements(pkg, PINNED_NIXPKGS_ARGS)
    c = VersionChooser(repo, dummy_pypi, f)
    await c.require(Requirement('flask'))
    assert_version(c, 'flask', '1.1.1')
    assert_version(c, 'itsdangerous', '1.1.0')
    assert_version(c, 'Werkzeug', '0.16.1')


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


@pytest.mark.asyncio
async def test_parse_single_requirements():
    data = await load_nixpkgs_data(PINNED_NIXPKGS_ARGS)
    nixpkgs = NixpkgsData(data)
    pypi = PyPIData(PyPICache())
    async def f(pkg):
        return await evaluate_package_requirements(pkg, PINNED_NIXPKGS_ARGS)
    c = VersionChooser(nixpkgs, pypi, f)
    await c.require(Requirement('passlib'))
    assert c.package_for('passlib')


@pytest.mark.asyncio
async def test_parse_requirements_nixpkgs_with_wheel_source():
    data = await load_nixpkgs_data(PINNED_NIXPKGS_ARGS)
    nixpkgs = NixpkgsData(data)
    pypi = PyPIData(PyPICache())
    async def f(pkg):
        return await evaluate_package_requirements(pkg, PINNED_NIXPKGS_ARGS)
    c = VersionChooser(nixpkgs, pypi, f)
    await c.require(Requirement('testpath'))
    pkg = c.package_for('testpath')
    assert pkg is not None
    await pkg.metadata()


@pytest.mark.asyncio
async def test_parse_requirements_nixpkgs_with_no_source():
    data = await load_nixpkgs_data(PINNED_NIXPKGS_ARGS)
    nixpkgs = NixpkgsData(data)
    pypi = PyPIData(PyPICache())
    async def f(pkg):
        return await evaluate_package_requirements(pkg, PINNED_NIXPKGS_ARGS)
    c = VersionChooser(nixpkgs, pypi, f)
    await c.require(Requirement('pycrypto'))
    pkg = c.package_for('pycrypto')
    assert pkg is not None
    await pkg.metadata()


@pytest.mark.asyncio
async def test_metadata_with_null_version():
    data = await load_nixpkgs_data(PINNED_NIXPKGS_ARGS)
    nixpkgs = NixpkgsData(data)
    pypi = PyPIData(PyPICache())
    async def f(pkg):
        return await evaluate_package_requirements(pkg, PINNED_NIXPKGS_ARGS)
    c = VersionChooser(nixpkgs, pypi, f)
    await c.require(Requirement('daiquiri==2.1.1'))
    pkg = c.package_for('daiquiri')
    assert pkg is not None
    await pkg.metadata()
    assert pkg.version == Version('2.1.1')


@pytest.mark.asyncio
async def test_packages_with_configure():
    data = await load_nixpkgs_data(PINNED_NIXPKGS_ARGS)
    nixpkgs = NixpkgsData(data)
    pypi = PyPIData(PyPICache())
    async def f(pkg):
        return await evaluate_package_requirements(pkg, PINNED_NIXPKGS_ARGS)
    c = VersionChooser(nixpkgs, pypi, f)
    await c.require(Requirement('brotli'))
    pkg = c.package_for('brotli')


@pytest.mark.asyncio
@pytest.mark.skipif(sys.platform != 'linux', reason='doit requires pyinotify only in linux')
async def test_packages_with_markers_in_extras_require():
    data = await load_nixpkgs_data(PINNED_NIXPKGS_ARGS)
    nixpkgs = NixpkgsData(data)
    pypi = PyPIData(PyPICache())
    async def f(pkg):
        return await evaluate_package_requirements(pkg, PINNED_NIXPKGS_ARGS)
    c = VersionChooser(nixpkgs, pypi, f)
    await c.require(Requirement('doit==0.32.0'))
    assert c.package_for('doit')
    assert c.package_for('pyinotify')
    assert c.package_for('macfsevents') is None


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
@pytest.mark.parametrize('fetchPypi', [
        None, ('sampleproject', 'tar.gz'), ('./sampleproject', 'tar.gz')
    ])
async def test_build_sampleproject_expression(fetchPypi):
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
    meta = await package.metadata()
    expr = build_nix_expression(package, reqs, meta, sha256, await load_nixpkgs_version(), fetchPypi)

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
async def test_build_textwrap3_expression():
    data = await load_nixpkgs_data(PINNED_NIXPKGS_ARGS)
    nixpkgs = NixpkgsData(data)
    pypi = PyPIData(PyPICache())
    async def f(pkg):
        return await evaluate_package_requirements(pkg, PINNED_NIXPKGS_ARGS)
    c = VersionChooser(nixpkgs, pypi, f)
    await c.require(Requirement('textwrap3==0.9.1'))
    package: PyPIPackage = c.package_for('textwrap3')  # type: ignore
    sha256 = await get_path_hash(await package.source())
    reqs = ChosenPackageRequirements(
        build_requirements=[],
        test_requirements=[],
        runtime_requirements=[],
    )
    meta = await package.metadata()
    expr = build_nix_expression(package, reqs, meta, sha256, await load_nixpkgs_version(), ('textwrap3', 'zip'))
    print(expr)
    wrapper_expr = f'(import <nixpkgs> {{}}).python3.pkgs.callPackage ({expr}) {{}}'
    print(wrapper_expr)
    result = await run_nix_build(wrapper_expr)

@pytest.mark.asyncio
async def test_build_sampleproject_nixpkgs():
    data = await load_nixpkgs_data(PINNED_NIXPKGS_ARGS)
    nixpkgs = NixpkgsData(data)
    pypi = PyPIData(PyPICache())
    async def f(pkg):
        return await evaluate_package_requirements(pkg, PINNED_NIXPKGS_ARGS)
    c = VersionChooser(nixpkgs, pypi, f)
    await c.require(Requirement('pytest'))
    await c.require(Requirement('sampleproject==1.3.1'))
    package: PyPIPackage = c.package_for('sampleproject')  # type: ignore
    sha256 = await get_path_hash(await package.source())
    reqs = ChosenPackageRequirements(
        build_requirements=[],
        test_requirements=[c.package_for('pytest')],  # type: ignore
        runtime_requirements=[c.package_for('peppercorn')]  # type: ignore
    )
    package.version = Version('1.2.3')
    meta = await package.metadata()
    assert package.version == Version('1.3.1')
    sampleproject_expr = build_nix_expression(
        package, reqs, meta, sha256, await load_nixpkgs_version())

    with tempfile.NamedTemporaryFile(suffix='.nix') as fp:
        fp.write(sampleproject_expr.encode())
        fp.flush()
        nixpkgs_expr = build_overlayed_nixpkgs({'sampleproject': Path(fp.name)})
        print(nixpkgs_expr)
        wrapper_expr = f"""(({nixpkgs_expr}) {{}}).python3.pkgs.sampleproject"""
        result = await run_nix_build(wrapper_expr)

    assert 'default.nix' not in nixpkgs_expr

    proc = await asyncio.create_subprocess_shell(
        f'{result}/bin/sample',
        stdout=asyncio.subprocess.PIPE)
    stdout, stderr = await proc.communicate()
    assert (await proc.wait()) == 0
    assert b'Call your main application code here' in stdout

@pytest.mark.asyncio
async def test_nixpkgs_version():
    ver = await load_nixpkgs_version()
    assert re.match(r'^\d{2}\.\d{2}', ver) is not None
