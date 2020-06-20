# WARNING: This file was automatically generated. You should avoid editing it.
# If you run pynixify again, the file will be either overwritten or
# deleted, and you will lose the changes you made to it.

{ Mako, aiofiles, aiohttp, buildPythonPackage, docopt, fetchPypi, lib, mypy
, packaging, pytest, pytest-asyncio, setuptools }:
buildPythonPackage rec {
  pname = "pynixify";
  version = "0.1dev";

  src = lib.cleanSource ../../..;

  doCheck = true;
  checkPhase = "true  # TODO fill with the real command for testing";

  propagatedBuildInputs = [ packaging setuptools aiohttp aiofiles docopt Mako ];
  checkInputs = [ pytest pytest-asyncio mypy ];

  meta = { description = "Nix expression generator for Python packages"; };
}
