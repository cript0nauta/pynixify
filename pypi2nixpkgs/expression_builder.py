import asyncio
from pathlib import Path
from typing import Iterable, Mapping, List, Set, Optional, Tuple
from mako.template import Template
from pypi2nixpkgs.version_chooser import (
    VersionChooser,
    ChosenPackageRequirements,
)
from pypi2nixpkgs.base import PackageMetadata
from pypi2nixpkgs.pypi_api import PyPIPackage

expression_template = Template("""
    { ${', '.join(args)} }:
    buildPythonPackage rec {
        pname = "${package.pypi_name}";
        version = "${version}";

        % if package.local_source:
            src = lib.cleanSource ../..;
        % else:
            src = builtins.fetchurl {
                url = "${package.download_url}";
                sha256 = "${sha256}";
            };
        % endif

        # TODO FIXME
        doCheck = false;

        buildInputs = [ ${' '.join(build_requirements)} ];
        propagatedBuildInputs = [ ${' '.join(runtime_requirements)} ];

        meta = {
            % if metadata.description:
                description = "${metadata.description}";
            % endif
            % if metadata.url:
                homepage = "${metadata.url}";
            % endif
        };
    }
""")

overlayed_nixpkgs_template = Template("""
    { overlays ? [ ], ... }@args:
    let
        pypi2nixOverlay = self: super: {
            python3 = super.python3.override { inherit packageOverrides; };
        };

        nixpkgs =
            % if nixpkgs is None:
                <nixpkgs>;
            % else:
                <% (url, sha256) = nixpkgs %>
                builtins.fetchTarball {
                    url = "${url}";
                    sha256 = "${sha256}";
                };
            % endif

        packageOverrides = self: super: {
            % for (package_name, path) in overlays.items():
                ${package_name} =
                    self.callPackage
                        ${'' if path.is_absolute() else './'}${path} {};

            % endfor
        };

    in import nixpkgs (args // { overlays = [ pypi2nixOverlay ] ++ overlays; })
""")

def build_nix_expression(
        package: PyPIPackage,
        requirements: ChosenPackageRequirements,
        metadata: PackageMetadata,
        sha256: str,
    ) -> str:
    non_python_dependencies = ['lib', 'fetchPypi', 'buildPythonPackage']
    runtime_requirements: List[str] = [
            p.attr for p in requirements.runtime_requirements]
    build_requirements: List[str] = [
            p.attr for p in requirements.build_requirements]

    args: List[str]
    args = sorted(set(
        non_python_dependencies + runtime_requirements +
        build_requirements))

    version = str(package.version)
    return expression_template.render(**locals())


def build_overlayed_nixpkgs(
        overlays: Mapping[str, Path],
        nixpkgs: Optional[Tuple[str, str]] = None
        ) -> str:
    return overlayed_nixpkgs_template.render(**locals())


async def nixfmt(expr: str) -> str:
    proc = await asyncio.create_subprocess_exec(
        'nixfmt',
        stdout=asyncio.subprocess.PIPE,
        stdin=asyncio.subprocess.PIPE,
    )
    proc.stdin.write(expr.encode())  # type: ignore
    proc.stdin.write_eof()  # type: ignore
    (stdout, _) = await proc.communicate()
    status = await proc.wait()
    if status:
        raise TypeError(f'nixfmt failed')
    return stdout.decode()
