import click
import asyncio
from pathlib import Path
from typing import List, Dict, Optional
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
)
from pypi2nixpkgs.pypi_api import (
    PyPIPackage,
    get_path_hash,
)
from packaging.requirements import Requirement


async def _build_version_chooser() -> VersionChooser:
    nixpkgs_data = NixpkgsData(await load_nixpkgs_data({}))
    pypi_cache = PyPICache()
    pypi_data = PyPIData(pypi_cache)
    version_chooser = VersionChooser(
        nixpkgs_data, pypi_data, evaluate_package_requirements)
    return version_chooser


@click.command()
@click.argument('requirements', nargs=-1)
@click.option('--local', nargs=1)
def main(**kwargs):
    asyncio.run(_main_async(**kwargs))

async def _main_async(requirements, local: Optional[str]):
    version_chooser: VersionChooser = await _build_version_chooser()

    if local is not None:
        await version_chooser.require_local(local, Path.cwd())

    for req in requirements:
        await version_chooser.require(Requirement(req))

    base_path = Path.cwd() / 'pypi2nixpkgs'
    packages_path = base_path / 'packages'
    packages_path.mkdir(parents=True, exist_ok=True)

    overlays: Dict[str, Path] = {}
    package: PyPIPackage
    for package in version_chooser.all_pypi_packages():

        reqs: ChosenPackageRequirements
        reqs = ChosenPackageRequirements.from_package_requirements(
            await evaluate_package_requirements(package),
            version_chooser
        )

        sha256 = await get_path_hash(await package.source())
        expr = build_nix_expression(
            package, reqs, sha256)
        expression_path = (packages_path / f'{package.pypi_name}.nix')
        with expression_path.open('w') as fp:
            fp.write(expr)
        expression_path = expression_path.relative_to(base_path)
        overlays[package.attr] = expression_path


    with (base_path / 'nixpkgs.nix').open('w') as fp:
        fp.write(build_overlayed_nixpkgs(overlays))
