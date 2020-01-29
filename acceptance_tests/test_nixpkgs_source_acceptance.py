import pytest
from pathlib import Path
from packaging.requirements import Requirement
from packaging.version import parse
from pypi2nixpkgs.nixpkgs_sources import (
    load_nixpkgs_data,
    NixpkgsData,
)
from pypi2nixpkgs.package_requirements import (
    eval_path_requirements,
)
from pypi2nixpkgs.version_chooser import (
    VersionChooser,
    evaluate_package_requirements,
)
from tests.test_version_chooser import assert_version

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
    c = VersionChooser(repo, f)
    await c.require(Requirement('flask'))
    assert_version(c, 'flask', '1.0.4')
    assert_version(c, 'itsdangerous', '1.1.0')
    assert_version(c, 'Werkzeug', '0.15.5')
