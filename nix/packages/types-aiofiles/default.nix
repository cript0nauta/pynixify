# WARNING: This file was automatically generated. You should avoid editing it.
# If you run pynixify again, the file will be either overwritten or
# deleted, and you will lose the changes you made to it.

{ buildPythonPackage, fetchPypi, lib }:

buildPythonPackage rec {
  pname = "types-aiofiles";
  version = "0.7.3";

  src = fetchPypi {
    inherit pname version;
    sha256 = "1nhcm80pybyfg1a9lk67f87i0zalx3vxh51ypbsh48r58lvphm2w";
  };

  # TODO FIXME
  doCheck = false;

  meta = with lib; {
    description = "Typing stubs for aiofiles";
    homepage = "https://github.com/python/typeshed";
  };
}
