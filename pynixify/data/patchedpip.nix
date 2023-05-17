{ buildPythonPackage, fetchFromGitHub, lib }:

buildPythonPackage rec {
  pname = "pip";
  version = "22.2.2";
  format = "other";

  src = fetchFromGitHub {
    owner = "pypa";
    repo = pname;
    rev = version;
    sha256 = "sha256-SLjmxFUFmvgy8E8kxfc6lxxCRo+GN4L77pqkWkRR8aE=";
    name = "${pname}-${version}-source";
  };

  postPatch = ''
    # Remove vendored Windows PE binaries
    # Note: These are unused but make the package unreproducible.
    find -type f -name '*.exe' -delete
  '';

  patches = [ ./pip_patch.diff ];
  phases = [ "unpackPhase" "patchPhase" ];
}
