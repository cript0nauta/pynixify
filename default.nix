with (import <nixpkgs> {});

python3.pkgs.buildPythonPackage {
  pname = "pypi2nixpkgs";
  version = "0.1dev";
  src = lib.cleanSource ./.;
  doCheck = true;
  propagatedBuildInputs = (with python3.pkgs; [ packaging setuptools aiohttp aiofiles click ]);
  checkInputs = with python3.pkgs; [ pytest pytest-asyncio mypy bats nix ];
  checkPhase = ''
    mypy pypi2nixpkgs/ tests/ acceptance_tests/
    pytest tests/ -m 'not usesnix'
  '';
}
