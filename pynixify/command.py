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
import os
import asyncio
import argparse
from pathlib import Path
from urllib.parse import urlparse
from typing import List, Dict, Optional, Tuple
from pkg_resources import parse_requirements
import pynixify.nixpkgs_sources
from pynixify.base import Package
from pynixify.nixpkgs_sources import (
    NixpkgsData,
    load_nixpkgs_data,
    load_nixpkgs_version,
    set_max_jobs,
)
from pynixify.pypi_api import (
    PyPICache,
    PyPIData,
)
from pynixify.version_chooser import (
    VersionChooser,
    ChosenPackageRequirements,
    evaluate_package_requirements,
)
from pynixify.expression_builder import (
    build_nix_expression,
    build_overlayed_nixpkgs,
    build_overlay_expr,
    build_shell_nix_expression,
    nixfmt,
)
from pynixify.pypi_api import (
    PyPIPackage,
    get_path_hash,
)
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name


async def _build_version_chooser(
        load_test_requirements_for: List[str],
        ignore_test_requirements_for: List[str],
        load_all_test_requirements: bool) -> VersionChooser:
    nixpkgs_data = NixpkgsData(await load_nixpkgs_data({}))
    pypi_cache = PyPICache()
    pypi_data = PyPIData(pypi_cache)
    def should_load_tests(package_name):
        if canonicalize_name(package_name) in [
                canonicalize_name(n)
                for n in ignore_test_requirements_for
                ]:
            return False
        return load_all_test_requirements or canonicalize_name(package_name) in [
            canonicalize_name(n)
            for n in load_test_requirements_for]
    version_chooser = VersionChooser(
        nixpkgs_data, pypi_data,
        req_evaluate=evaluate_package_requirements,
        should_load_tests=should_load_tests,
    )
    return version_chooser


def main():
    parser = argparse.ArgumentParser(
        description=(
            'Nix expression generator for Python packages.'
        ))
    parser.add_argument('requirement', nargs='*')
    parser.add_argument(
        '-l', '--local',
        metavar='NAME',
        help=(
            'Create a "python.pkgs.NAME" derivation using the current '
            'directory as source. Useful for packaging projects with a '
            'setup.py.'
        ))
    parser.add_argument(
        '--nixpkgs',
        help=(
            'URL to a tarball containing the nixpkgs source. When specified, '
            'the generated expressions will use it instead of <nixpkgs>, '
            'improving reproducibility.'
        ))
    parser.add_argument(
        '-o', '--output',
        metavar='DIR',
        default='pynixify/',
        help=(
            "Directory in which pynixify will save the generated Nix "
            "expressions. If if doesn't exist, it will be automatically "
            "created. [default. pynixify/]"
        ))
    parser.add_argument(
        '-O', '--overlay-only',
        action='store_true',
        help=(
            "Generate only overlay expresion."
        ))
    parser.add_argument(
        '--all-tests',
        action='store_true',
        help=(
            "Include test requirements in all generated expressions, "
            "except for those explicitly excluded with --ignore-tests."
        ))
    parser.add_argument(
        '--ignore-tests',
        metavar='PACKAGES',
        help=(
            "Comma-separated list of packages for which we don't want "
            "their test requirements to be loaded."
        ))
    parser.add_argument(
        '--tests',
        metavar='PACKAGES',
        help=(
            "Comma-separated list of packages for which we do want "
            "their test requirements to be loaded."
        ))
    parser.add_argument(
        '-r',
        metavar='REQUIREMENTS_FILE',
        action='append',
        help=(
            "A filename whose content is a PEP 508 compliant list of "
            "dependencies. It can be specified multiple times to use more "
            "than one file. Note that pip-specific options, such as "
            "'-e git+https....' are not supported."
        ))
    parser.add_argument(
        '--max-jobs',
        type=int,
        help=(
            "Sets the maximum number of concurrent nix-build processes "
            "executed by pynixify. If it isn't specified, it will be set to "
            "the number of CPUs in the system."
        ))
    args = parser.parse_args()

    asyncio.run(_main_async(
        requirements=args.requirement,
        requirement_files=args.r or [],
        local=args.local,
        output_dir=args.output,
        nixpkgs=args.nixpkgs,
        load_all_test_requirements=args.all_tests,
        load_test_requirements_for=args.tests.split(',') if args.tests else [],
        ignore_test_requirements_for=args.ignore_tests.split(',') if args.ignore_tests else [],
        max_jobs=args.max_jobs,
        generate_only_overlay=args.overlay_only,
    ))

async def _main_async(
        requirements: List[str],
        requirement_files: List[str],
        local: Optional[str],
        nixpkgs: Optional[str],
        output_dir: Optional[str],
        load_test_requirements_for: List[str],
        ignore_test_requirements_for: List[str],
        load_all_test_requirements: bool,
        max_jobs: Optional[int],
        generate_only_overlay:bool):

    if nixpkgs is not None:
        pynixify.nixpkgs_sources.NIXPKGS_URL = nixpkgs

    if max_jobs is not None:
        set_max_jobs(max_jobs)

    version_chooser: VersionChooser = await _build_version_chooser(
        load_test_requirements_for, ignore_test_requirements_for,
        load_all_test_requirements)

    if local is not None:
        await version_chooser.require_local(local, Path.cwd())

    all_requirements: List[Requirement] = []
    for requirement_file in requirement_files:
        with open(requirement_file) as fp:
            for r in parse_requirements(fp.read()):
                # Convert from Requirement.parse to Requirement
                all_requirements.append(Requirement(str(r)))
    for req_ in requirements:
        all_requirements.append(Requirement(req_))

    await asyncio.gather(*(
        version_chooser.require(req)
        for req in all_requirements
    ))

    output_dir = output_dir or 'pynixify'
    base_path = Path.cwd() / output_dir
    packages_path = base_path / 'packages'
    packages_path.mkdir(parents=True, exist_ok=True)

    overlays: Dict[str, Path] = {}
    package: PyPIPackage

    async def write_package_expression(package: PyPIPackage):
        reqs: ChosenPackageRequirements
        reqs = ChosenPackageRequirements.from_package_requirements(
            await evaluate_package_requirements(package),
            version_chooser=version_chooser,
            load_tests=version_chooser.should_load_tests(package.pypi_name),
        )

        sha256 = await get_path_hash(await package.source())
        meta = await package.metadata()
        version = await load_nixpkgs_version()
        try:
            (pname, ext) = await get_pypi_data(
                package.download_url,
                str(package.version),
                sha256
            )
        except RuntimeError:
            expr = build_nix_expression(
                package, reqs, meta, sha256, version)
        else:
            expr = build_nix_expression(
                package, reqs, meta, sha256, version, fetchPypi=(pname, ext))
        expression_dir = (packages_path / f'{package.pypi_name}/')
        expression_dir.mkdir(exist_ok=True)
        expression_path = expression_dir / 'default.nix'
        with expression_path.open('w') as fp:
            fp.write(await nixfmt(expr))
        expression_path = expression_path.relative_to(base_path)
        overlays[package.attr] = expression_path

    await asyncio.gather(*(
        write_package_expression(package)
        for package in version_chooser.all_pypi_packages()
    ))

    if generate_only_overlay:
        with (base_path / 'overlay.nix').open('w') as fp:
            expr = build_overlay_expr(overlays)
            fp.write(await nixfmt(expr))
            return


    with (base_path / 'nixpkgs.nix').open('w') as fp:
        if nixpkgs is None:
            expr = build_overlayed_nixpkgs(overlays)
        else:
            sha256 = await get_url_hash(nixpkgs)
            expr = build_overlayed_nixpkgs(overlays, (nixpkgs, sha256))
        fp.write(await nixfmt(expr))

    packages: List[Package] = []
    for req in all_requirements:
        p: Optional[Package] = version_chooser.package_for(req.name)
        assert p is not None
        packages.append(p)
    if local is not None:
        p = version_chooser.package_for(local)
        assert p is not None
        packages.append(p)

    with (base_path / 'shell.nix').open('w') as fp:
        expr = build_shell_nix_expression(packages)
        fp.write(await nixfmt(expr))


async def get_url_hash(url: str, unpack=True) -> str:
    cmd = ['nix-prefetch-url']
    if unpack:
        cmd.append('--unpack')
    cmd.append(url)

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
    )
    (stdout, _) = await proc.communicate()
    status = await proc.wait()
    if status != 0:
        raise RuntimeError(f'Could not get hash of URL: {url}')
    return stdout.decode().strip()


async def get_pypi_data(url: str, version: str, sha256: str) -> Tuple[str, str]:
    """Try to form a fetchPypi pname and extension to avoid using builtins.fetchurl.

    If this fails, the generated expression will use builtins.fetchurl. It will
    work perfectly, but the code of the expression won't be of nixpkgs quality.
    Most Python expressions in nixpkgs use fetchPypi instead of raw
    builtins.fetchurl, so our generated expression should do it too.
    """
    filename = Path(urlparse(url).path).name
    match = re.match(
        f'(?P<pname>.+)-{re.escape(version)}\\.(?P<ext>.+)',
        filename
    )
    if match is None:
        raise RuntimeError(f'Cannot build mirror://pypi URL from original URL: {url}')

    pname, ext = match.group('pname'), match.group('ext')
    # See <nixpkgs>/pkgs/development/python-modules/ansiwrap/default.nix
    # "mirror://pypi/${builtins.substring 0 1 pname}/${pname}/${pname}-${version}.${extension}";
    url = f'mirror://pypi/{pname[0]}/{pname}/{pname}-{version}.{ext}'
    newhash = await get_url_hash(url, unpack=False)
    if newhash != sha256:
        raise RuntimeError(f'Invalid hash for URL: {url}')
    return (pname, ext)

if __name__ == '__main__':
    main()
