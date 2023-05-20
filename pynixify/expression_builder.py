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

import asyncio
from pathlib import Path
from typing import Iterable, Mapping, List, Set, Optional, Tuple
from mako.template import Template
from pynixify.version_chooser import (
    VersionChooser,
    ChosenPackageRequirements,
)
from pynixify.base import PackageMetadata, Package
from pynixify.pypi_api import PyPIPackage

DISCLAIMER = """
# WARNING: This file was automatically generated. You should avoid editing it.
# If you run pynixify again, the file will be either overwritten or
# deleted, and you will lose the changes you made to it.

"""

expression_template = Template("""${DISCLAIMER}
    { ${', '.join(args)} }:

    buildPythonPackage rec {
        pname = ${package.pypi_name | nix};
        version = ${version | nix};

        % if package.local_source:
            src = lib.cleanSource ../../..;
        % elif fetchPypi is not None:
            src = fetchPypi {
                % if fetchPypi[0] == package.pypi_name:
                    inherit pname version;
                % else:
                    inherit version;
                    pname = ${fetchPypi[0] | nix};
                % endif
                % if fetchPypi[1] != "tar.gz":
                    extension = ${fetchPypi[1] | nix};
                % endif
                sha256 = "${sha256}";
            };
        % else:
            # TODO use fetchPypi
            src = builtins.fetchurl {
                url = ${package.download_url | nix};
                sha256 = "${sha256}";
            };
        % endif

        % if build_requirements:
            buildInputs = [ ${' '.join(build_requirements)} ];
        % endif
        % if runtime_requirements:
            propagatedBuildInputs = [ ${' '.join(runtime_requirements)} ];
        % endif
        % if test_requirements:
            ${ 'checkInputs' if is_old_nixpkgs else 'nativeBuildInputs' } = [ ${' '.join(test_requirements)} ];
        % endif

        % if test_requirements:
            checkPhase = "true  # TODO fill with the real command for testing";
        % else:
            # TODO FIXME
            doCheck = false;
        % endif

        meta = with lib; {
            % if metadata.description:
                description = ${metadata.description | nix };
            % endif
            % if metadata.url:
                homepage = ${metadata.url | nix};
            % endif
        };
    }
""")

overlayed_nixpkgs_template = Template("""${DISCLAIMER}
    { overlays ? [ ], ... }@args:
    let
        pynixifyOverlay = self: super: {
            % for interpreter in interpreters:
                ${interpreter} = super.${interpreter}.override { inherit packageOverrides; };
            % endfor
        };

        nixpkgs =
            % if nixpkgs is None:
                <nixpkgs>;
            % else:
                <% (url, sha256) = nixpkgs %>
                builtins.fetchTarball {
                    url = ${url | nix};
                    sha256 = "${sha256}";
                };
            % endif

        packageOverrides = self: super: {
            % for (package_name, path) in overlays.items():
                ${package_name} =
                    self.callPackage
                        ${'' if path.is_absolute() else './'}${str(path).replace('/default.nix', '')} {};

            % endfor
        };

    in import nixpkgs (args // { overlays = [ pynixifyOverlay ] ++ overlays; })
""")

shell_nix_template = Template("""${DISCLAIMER}
    { python ? "${interpreter | nix}" }:
    let
        pkgs = import ./nixpkgs.nix {};
        pythonPkg = builtins.getAttr python pkgs;
    in
    pkgs.mkShell {
        name = "pynixify-env";
        buildInputs = [
            (pythonPkg.withPackages (ps: with ps; [
                % for package in packages:
                    ${package.attr}
                % endfor
            ]))
        ];
    }
""")

def build_nix_expression(
        package: PyPIPackage,
        requirements: ChosenPackageRequirements,
        metadata: PackageMetadata,
        sha256: str,
        nixpkgs_version: str,
        fetchPypi: Optional[Tuple[str, str]] = None,
    ) -> str:
    non_python_dependencies = ['lib', 'fetchPypi', 'buildPythonPackage']
    runtime_requirements: List[str] = [
            p.attr for p in requirements.runtime_requirements]
    build_requirements: List[str] = [
            p.attr for p in requirements.build_requirements]
    test_requirements: List[str] = [
            p.attr for p in requirements.test_requirements]

    args: List[str]
    args = sorted(set(
        non_python_dependencies + runtime_requirements +
        test_requirements + build_requirements))

    version = str(package.version)
    nix = escape_string
    is_old_nixpkgs = int(nixpkgs_version.split('.')[0]) <= 22
    return expression_template.render(DISCLAIMER=DISCLAIMER, **locals())

def build_overlay_expr(overlays: Mapping[str, Path]):
    return Template("""
    self: super: {
            % for (package_name, path) in overlays.items():
                ${package_name} =
                    self.callPackage
                        ${'' if path.is_absolute() else './'}${str(path).replace('/default.nix', '')} {};

            % endfor
    }""").render(overlays=overlays)

def build_overlayed_nixpkgs(
        overlays: Mapping[str, Path],
        nixpkgs: Optional[Tuple[str, str]] = None
        ) -> str:
    nix = escape_string

    # Sort dictionary keys to ensure pynixify/nixpkgs.nix will have the
    # same contents in different pynixify runs.
    overlays = {
        k: overlays[k]
        for k in sorted(overlays.keys())
    }

    # Taken from Interpreters section in https://nixos.org/nixpkgs/manual/#reference
    interpreters = [
        'python2',
        'python27',
        'python3',
        'python35',
        'python36',
        'python37',
        'python38',
        'python39',
        'python310'
    ]

    return overlayed_nixpkgs_template.render(DISCLAIMER=DISCLAIMER, **locals())


def build_shell_nix_expression(packages: List[Package], interpreter: str) -> str:
    return shell_nix_template.render(DISCLAIMER=DISCLAIMER, packages=packages, interpreter=interpreter)


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

def escape_string(string: str) -> str:
    # Based on the documentation in https://nixos.org/nix/manual/#idm140737322106128
    string = string.replace('\\', '\\\\')
    string = string.replace('"', '\\"')
    string = string.replace('\n', '\\n')
    string = string.replace('\t', '\\t')
    string = string.replace('\r', '\\r')
    string = string.replace('${', '\\${')
    return f'"{string}"'
