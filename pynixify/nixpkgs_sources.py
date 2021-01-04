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

import sys
import json
import asyncio
from pathlib import Path
from typing import Sequence, Any, Optional
from collections import defaultdict
from multiprocessing import cpu_count
from packaging.utils import canonicalize_name
from packaging.requirements import Requirement
from packaging.version import Version, parse
from pynixify.base import Package
from pynixify.exceptions import PackageNotFound, NixBuildError

NIXPKGS_URL: Optional[str] = None

class NixPackage(Package):
    def __init__(self, *, attr: str, version: Version):
        self.version = version
        self.__attr = attr  # Ugly hack to fix mypy errors

    @property
    def attr(self):
        # Ugly hack to fix mypy errors
        return self.__attr

    async def source(self, extra_args=[]):
        expr = """
        with import <nixpkgs> {};
        let
          pkg = python3Packages."ATTR";
        in
          if pkg ? "src" then
            pkg.src
          else
            # In some cases, a package can have no source. I this case, return
            # a dummy source so the requirements parser fails in an expected way
            writeTextFile {
              text = "raise RuntimeError('This is expected to fail')";
              name = "ATTR_dummy_src";
              destination = "/setup.py";
            }
        """.replace('ATTR', self.attr)
        args = [
            '--no-out-link',
            '--no-build-output',
            '-E',
            expr
        ]
        args += extra_args
        return await run_nix_build(*args)

    def __str__(self):
        return f'NixPackage(attr={self.attr}, version={self.version})'


class NixpkgsData:
    def __init__(self, data):
        data_defaultdict: Any = defaultdict(list)
        for (k, v) in data.items():
            data_defaultdict[canonicalize_name(k)] += v
        self.__data = dict(data_defaultdict)

    def from_pypi_name(self, name: str) -> Sequence[NixPackage]:
        try:
            data = self.__data[canonicalize_name(name)]
        except KeyError:
            raise PackageNotFound(f'{name} is not defined in nixpkgs')
        return [
            NixPackage(attr=drv['attr'], version=parse(drv['version']))
            for drv in data
        ]

    def from_requirement(self, req: Requirement) -> Sequence[NixPackage]:
        drvs = self.from_pypi_name(req.name)
        return [drv for drv in drvs if str(drv.version) in req.specifier]


async def load_nixpkgs_data(extra_args):
    nix_expression_path = Path(__file__).parent / "data" / "pythonPackages.nix"
    args = [
        '--eval',
        '--strict',
        '--json',
        str(nix_expression_path),
    ]
    args += extra_args
    if NIXPKGS_URL is not None:
        args += ['-I', f'nixpkgs={NIXPKGS_URL}']
    proc = await asyncio.create_subprocess_exec(
        'nix-instantiate', *args, stdout=asyncio.subprocess.PIPE)
    (stdout, _) = await proc.communicate()
    status = await proc.wait()
    assert status == 0
    ret = json.loads(stdout)
    return ret


async def _run_nix_build(*args: Sequence[str], retries=0, max_retries=5) -> Path:
    if NIXPKGS_URL is not None:
        # TODO fix mypy hack
        args_ = list(args) + ['-I', f'nixpkgs={NIXPKGS_URL}']
    else:
        args_ = list(args)
    # TODO remove mypy ignore below and fix compatibility with mypy 0.790
    proc = await asyncio.create_subprocess_exec(
        'nix-build', *args_, stdout=asyncio.subprocess.PIPE,  # type: ignore
        stderr=asyncio.subprocess.PIPE)
    (stdout, stderr) = await proc.communicate()
    status = await proc.wait()

    if b'all build users are currently in use' in stderr and retries < max_retries:
        # perform an expotential backoff and retry
        # TODO think a way to avoid relying in the error message
        sys.stderr.write(
            f'warning: All build users are currently in use. '
            f'Retrying in {2**retries} seconds\n'
        )
        await asyncio.sleep(2**retries)
        return await run_nix_build(
            *args,
            retries=retries+1,
            max_retries=max_retries
        )
    elif retries >= max_retries:
        sys.stderr.write(f'error: Giving up after {max_retries} failed retries\n')

    if status:
        print(stderr.decode(), file=sys.stderr)
        raise NixBuildError(f'nix-build failed with code {status}')
    return Path(stdout.strip().decode())


sem: Optional[asyncio.BoundedSemaphore] = None


def set_max_jobs(n: int):
    global sem
    sem = asyncio.BoundedSemaphore(n)


async def run_nix_build(*args: Sequence[str], retries=0, max_retries=5) -> Path:
    global sem
    if not sem:
        sem = asyncio.BoundedSemaphore(cpu_count())
    async with sem:
        return await _run_nix_build(*args, retries=retries, max_retries=5)
