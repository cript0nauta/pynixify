# WARNING: This file was automatically generated. You should avoid editing it.
# If you run pynixify again, the file will be either overwritten or
# deleted, and you will lose the changes you made to it.

{ Mako, aiofiles, aiohttp, buildPythonPackage, fetchPypi, lib, mypy, packaging
, pytest, pytest-asyncio, setuptools }:

buildPythonPackage rec {
  pname = "pynixify";
  version = "0.1";

  src = lib.cleanSource ../../..;

  propagatedBuildInputs = [ packaging setuptools aiohttp aiofiles Mako ];
  checkInputs = [ pytest pytest-asyncio mypy ];

  checkPhase = "true  # TODO fill with the real command for testing";

  meta = with lib; {
    description = "Nix expression generator for Python packages";
    homepage = "https://github.com/cript0nauta/pynixify";
  };
}
