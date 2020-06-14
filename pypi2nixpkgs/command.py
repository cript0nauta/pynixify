import re
import os
import click
import asyncio
from pathlib import Path
from urllib.parse import urlparse
from typing import List, Dict, Optional, Tuple
import pypi2nixpkgs.nixpkgs_sources
from pypi2nixpkgs.nixpkgs_sources import (
    NixpkgsData,
    load_nixpkgs_data,
)
from pypi2nixpkgs.pypi_api import (
    PyPICache,
    PyPIData,
)
from pypi2nixpkgs.version_chooser import (
    VersionChooser,
    ChosenPackageRequirements,
    evaluate_package_requirements,
)
from pypi2nixpkgs.expression_builder import (
    build_nix_expression,
    build_overlayed_nixpkgs,
    nixfmt,
)
from pypi2nixpkgs.pypi_api import (
    PyPIPackage,
    get_path_hash,
)
from packaging.requirements import Requirement


async def _build_version_chooser(
        load_test_requirements: List[str]) -> VersionChooser:
    nixpkgs_data = NixpkgsData(await load_nixpkgs_data({}))
    pypi_cache = PyPICache()
    pypi_data = PyPIData(pypi_cache)
    def should_load_tests(package_name):
        return package_name in load_test_requirements
    version_chooser = VersionChooser(
        nixpkgs_data, pypi_data,
        req_evaluate=evaluate_package_requirements,
        should_load_tests=should_load_tests,
    )
    return version_chooser


@click.command()
@click.argument('requirements', nargs=-1)
@click.option('--local', nargs=1)
@click.option('--nixpkgs', nargs=1)
@click.option('--output-dir', nargs=1)
@click.option('--load-test-requirements-for', multiple=True)
def main(**kwargs):
    asyncio.run(_main_async(**kwargs))

async def _main_async(
        requirements,
        local: Optional[str],
        nixpkgs: Optional[str],
        output_dir: Optional[str],
        load_test_requirements_for: List[str]):

    if nixpkgs is not None:
        pypi2nixpkgs.nixpkgs_sources.NIXPKGS_URL = nixpkgs

    version_chooser: VersionChooser = await _build_version_chooser(load_test_requirements_for)

    if local is not None:
        await version_chooser.require_local(local, Path.cwd())

    await asyncio.gather(*(
        version_chooser.require(Requirement(req))
        for req in requirements
    ))

    output_dir = output_dir or 'pypi2nixpkgs'
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
        try:
            (pname, ext) = await get_pypi_data(
                package.download_url,
                str(package.version),
                sha256
            )
        except RuntimeError:
            expr = build_nix_expression(
                package, reqs, meta, sha256)
        else:
            expr = build_nix_expression(
                package, reqs, meta, sha256, fetchPypi=(pname, ext))
        expression_path = (packages_path / f'{package.pypi_name}.nix')
        with expression_path.open('w') as fp:
            fp.write(await nixfmt(expr))
        expression_path = expression_path.relative_to(base_path)
        overlays[package.attr] = expression_path

    await asyncio.gather(*(
        write_package_expression(package)
        for package in version_chooser.all_pypi_packages()
    ))

    with (base_path / 'nixpkgs.nix').open('w') as fp:
        if nixpkgs is None:
            expr = build_overlayed_nixpkgs(overlays)
        else:
            sha256 = await get_url_hash(nixpkgs)
            expr = build_overlayed_nixpkgs(overlays, (nixpkgs, sha256))
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
