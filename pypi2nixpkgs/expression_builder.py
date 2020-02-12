from pathlib import Path
from typing import Iterable, Mapping
from pypi2nixpkgs.version_chooser import VersionChooser
from pypi2nixpkgs.pypi_api import PyPIPackage

def build_nix_expression(
        package: PyPIPackage,
        package_deps: Iterable[str],
        sha256: str
    ) -> str:
    non_python_dependencies = ['fetchPypi', 'buildPythonPackage']
    args = ','.join(non_python_dependencies + list(package_deps))
    version = str(package.version)
    return f"""
    {{ {args} }}:
    buildPythonPackage rec {{
        pname = "{package.pypi_name}";
        version = "{version}";
        src = fetchPypi {{
            inherit pname version;
            sha256 = "{sha256}";
        }};

        # TODO FIXME
        doCheck = false;

        buildInputs = [{' '.join(package_deps)}];
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
                self.callPackage {path.resolve()} {{ }};
        """)

    parts.append(footer)
    return '\n'.join(parts)
