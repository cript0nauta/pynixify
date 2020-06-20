with (import ./nix/nixpkgs.nix { });

python3.pkgs.toPythonApplication (python3.pkgs.pynixify.overridePythonAttrs
  (drv: {
    # Add system dependencies
    checkInputs = drv.checkInputs ++ [ nix nixfmt bats ];

    checkPhase = ''
      mypy pynixify/ tests/ acceptance_tests/
      pytest tests/ -m 'not usesnix'
    '';

    postInstall = ''
      # Add nixfmt to pynixify's PATH
      wrapProgram $out/bin/pynixify --prefix PATH : "${nixfmt}/bin"
    '';
  }))
