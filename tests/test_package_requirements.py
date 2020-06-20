import pytest
from pathlib import Path
from typing import Sequence
from packaging.requirements import Requirement
from pynixify.package_requirements import PackageRequirements

@pytest.mark.asyncio
async def test_package_requirements():
    reqs = PackageRequirements.from_result_path(
        Path(__file__).parent / "parse_setuppy_data_result")

    def has_requirement(r: str, l: Sequence[Requirement]):
        return any(str(e) == r for e in l)

    assert has_requirement('pytest', reqs.test_requirements)
    assert not has_requirement('pytest', reqs.runtime_requirements)
    assert has_requirement('setuptools_scm', reqs.build_requirements)
    assert has_requirement('Click>=6.0', reqs.runtime_requirements)

