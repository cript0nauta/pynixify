with (import <nixpkgs> {});

python3.pkgs.buildPythonPackage {
  pname = "pypi2nixpkgs";
  version = "0.1dev";
  src = lib.cleanSource ./.;
  doCheck = true;
  checkInputs = with python3.pkgs; [ pytest ];
  checkPhase = ''
    pytest tests/
  '';
}
