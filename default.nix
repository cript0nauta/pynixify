with (import <nixpkgs> { });

python3.pkgs.buildPythonPackage {
  pname = "pynixify";
  version = "0.1dev";
  src = lib.cleanSource ./.;
  doCheck = true;

  propagatedBuildInputs =
    with python3.pkgs; [ packaging setuptools aiohttp aiofiles docopt Mako ];

  checkInputs = with python3.pkgs; [ pytest pytest-asyncio mypy bats nix nixfmt ];

  checkPhase = ''
    mypy pynixify/ tests/ acceptance_tests/
    pytest tests/ -m 'not usesnix'
  '';

  postInstall = ''
    # Add nixfmt to pynixify's PATH
    wrapProgram $out/bin/pynixify --prefix PATH : "${nixfmt}/bin"
  '';
}
