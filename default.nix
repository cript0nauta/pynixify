# with (import ./pynixify/nixpkgs.nix { });  # Use this in projects other than pynixify
with (import ./nix/nixpkgs.nix { });

{ runMypy ? true }:

# Use pynixify's generated expression, but override it to add additional
# dependencies and to convert it to an application in order to improve the
# derivation name.
python3.pkgs.toPythonApplication (python3.pkgs.pynixify.overridePythonAttrs
  (drv: {
    # Add system dependencies
    checkInputs = drv.checkInputs ++ [ nix nixfmt bats ];

    checkPhase = ''
      ${if runMypy then "mypy pynixify/ tests/ acceptance_tests/" else ""}
      pytest tests/ -m 'not usesnix'  # We can't run Nix inside Nix builds
    '';

    postInstall = ''
      # Add nixfmt to pynixify's PATH
      wrapProgram $out/bin/pynixify --prefix PATH : "${nixfmt}/bin"
    '';
  }))
