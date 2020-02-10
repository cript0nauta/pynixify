from typing import Iterable
from pypi2nixpkgs.version_chooser import VersionChooser
from pypi2nixpkgs.pypi_api import PyPIPackage

def build_nix_expression(
        package: PyPIPackage,
        package_name: str,
        package_deps: Iterable[str],
        sha256: str
    ) -> str:
    non_python_dependencies = ['fetchPypi', 'buildPythonPackage']
    args = ','.join(non_python_dependencies + list(package_deps))
    version = str(package.version)
    return f"""
    {{ {args} }}:
    buildPythonPackage rec {{
        pname = "{package_name}";
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
