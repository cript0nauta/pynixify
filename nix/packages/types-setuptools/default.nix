# WARNING: This file was automatically generated. You should avoid editing it.
# If you run pynixify again, the file will be either overwritten or
# deleted, and you will lose the changes you made to it.

{ buildPythonPackage, fetchPypi, lib }:

buildPythonPackage rec {
  pname = "types-setuptools";
  version = "57.4.5";

  src = fetchPypi {
    inherit pname version;
    sha256 = "00kfgpsnzz3a5f8pw03x3bkawqvdjvcky24wml2358v8rbyhwq54";
  };

  # TODO FIXME
  doCheck = false;

  meta = with lib; {
    description = "Typing stubs for setuptools";
    homepage = "https://github.com/python/typeshed";
  };
}
