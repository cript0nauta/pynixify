with (import <nixpkgs> { });

python3.pkgs.buildPythonPackage {
  pname = "pypi2nixpkgs";
  version = "0.1dev";
  src = lib.cleanSource ./.;
  doCheck = true;

  propagatedBuildInputs =
    with python3.pkgs; [ packaging setuptools aiohttp aiofiles click Mako ];

  checkInputs = with python3.pkgs; [ pytest pytest-asyncio mypy bats nix nixfmt ];

  checkPhase = ''
    mypy pypi2nixpkgs/ tests/ acceptance_tests/
    pytest tests/ -m 'not usesnix'
  '';

  postInstall = ''
    # Add nixfmt to pypi2nixpkgs' PATH
    wrapProgram $out/bin/pypi2nixpkgs --prefix PATH : "${nixfmt}/bin"
  '';
}
