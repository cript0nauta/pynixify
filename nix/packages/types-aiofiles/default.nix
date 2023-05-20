# WARNING: This file was automatically generated. You should avoid editing it.
# If you run pynixify again, the file will be either overwritten or
# deleted, and you will lose the changes you made to it.

{ buildPythonPackage, fetchPypi, lib }:

buildPythonPackage rec {
  pname = "types-aiofiles";
  version = "23.1.0.2";

  src = fetchPypi {
    inherit pname version;
    sha256 = "0qhllm1zhrr562sqjiwq8s5q8g2xkllp0qg5lijrls6xgjgna2pa";
  };

  # TODO FIXME
  doCheck = false;

  meta = with lib; {
    description = "Typing stubs for aiofiles";
    homepage = "https://github.com/python/typeshed";
  };
}
