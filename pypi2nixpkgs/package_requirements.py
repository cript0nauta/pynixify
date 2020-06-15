from pathlib import Path
from typing import List
from dataclasses import dataclass
from packaging.requirements import Requirement
from pkg_resources import parse_requirements
from pypi2nixpkgs.nixpkgs_sources import run_nix_build
from pypi2nixpkgs.exceptions import NixBuildError


@dataclass
class PackageRequirements:
    build_requirements: List[Requirement]
    test_requirements: List[Requirement]
    runtime_requirements: List[Requirement]

    @classmethod
    def from_result_path(cls, result_path: Path):
        attr_mapping = {
            'build_requirements': Path('setup_requires.txt'),
            'test_requirements': Path('tests_requires.txt'),
            'runtime_requirements': Path('install_requires.txt'),
        }
        kwargs = {}
        for (attr, filename) in attr_mapping.items():
            with (result_path / filename).open() as fp:
                # Convert from Requirement.parse to Requirement
                reqs = [Requirement(str(r)) for r in parse_requirements(fp)]
                kwargs[attr] = reqs
        return cls(**kwargs)


async def eval_path_requirements(path: Path) -> PackageRequirements:
    nix_expression_path = Path(__file__).parent / "data" / "parse_setuppy_data.nix"
    assert nix_expression_path.exists()
    nix_store_path = await run_nix_build(
        str(nix_expression_path),
        '--no-out-link',
        '--no-build-output',
        '--arg',
        'file',
        str(path.resolve())
    )
    if (nix_store_path / 'failed').exists():
        print(f'Error parsing requirements of {path}. Assuming it has no dependencies.')
        return PackageRequirements(
            build_requirements=[],
            test_requirements=[],
            runtime_requirements=[],
        )
    return PackageRequirements.from_result_path(nix_store_path)
