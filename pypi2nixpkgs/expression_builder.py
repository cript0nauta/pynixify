from pathlib import Path
from typing import Iterable, Mapping, List, Set
from pypi2nixpkgs.version_chooser import (
    VersionChooser,
    ChosenPackageRequirements,
)
from pypi2nixpkgs.pypi_api import PyPIPackage

def build_nix_expression(
        package: PyPIPackage,
        requirements: ChosenPackageRequirements,
        sha256: str
    ) -> str:
    non_python_dependencies = ['lib', 'fetchPypi', 'buildPythonPackage']
    runtime_requirements: List[str] = [
            p.attr for p in requirements.runtime_requirements]
    build_requirements: List[str] = [
            p.attr for p in requirements.build_requirements]

    args: Set[str]
    args = set(non_python_dependencies + runtime_requirements + build_requirements)

    version = str(package.version)
    if package.local_source:
        src_part = f"""
            src = lib.cleanSource ../..;
        """
    else:
        src_part = f"""
            src = builtins.fetchurl {{
                url = "{package.download_url}";
                sha256 = "{sha256}";
            }};
        """
    return f"""
    {{ {', '.join(args)} }}:
    buildPythonPackage rec {{
        pname = "{package.pypi_name}";
        version = "{version}";
{src_part}

        # TODO FIXME
        doCheck = false;

        buildInputs = [{' '.join(build_requirements)}];
        propagatedBuildInputs = [{' '.join(runtime_requirements)}];
    }}
    """


def build_overlayed_nixpkgs(overlays: Mapping[str, Path]) -> str:
    header = """{ overlays ? [ ], ...}@args:
    let
        pypi2nixOverlay = self: super: {
            python3 = super.python3.override { inherit packageOverrides; };
        };

        packageOverrides = self: super: {
    """
    footer = """
        };
    in import <nixpkgs> (args // { overlays = [ pypi2nixOverlay ] ++ overlays; })
    """

    parts = [header]

    for (package_name, path) in overlays.items():
        parts.append(f"""
            {package_name} =
                self.callPackage {'' if path.is_absolute() else './'}{path} {{ }};
        """)

    parts.append(footer)
    return '\n'.join(parts)
