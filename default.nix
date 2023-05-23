# with (import ./pynixify/nixpkgs.nix { });  # Use this in projects other than pynixify
with (import ./nix/nixpkgs.nix { });

let
  outerNixfmt = nixfmt;

  # Allow specifying a custom version of nixfmt
in { nixfmt ? null, runMypy ? true }:

let
  chosenNixfmt = if isNull nixfmt then outerNixfmt else nixfmt;

  # Use pynixify's generated expression, but override it to add additional
  # dependencies and to convert it to an application in order to improve the
  # derivation name.
in python3.pkgs.toPythonApplication (python3.pkgs.pynixify.overridePythonAttrs
  (drv:

    (if lib.versions.major lib.version >= "23" then {
      nativeBuildInputs = drv.nativeBuildInputs ++ [ nix chosenNixfmt bats ];
    } else {
      checkInputs = drv.nativeBuildInputs ++ [ nix chosenNixfmt bats ];
    }) // {

      checkPhase = ''
        ${if runMypy then "mypy pynixify/ tests/ acceptance_tests/" else ""}
        pytest tests/ -m 'not usesnix'  # We can't run Nix inside Nix builds
      '';

      postInstall = ''
        # Add nixfmt to pynixify's PATH
        wrapProgram $out/bin/pynixify --prefix PATH : "${chosenNixfmt}/bin"
      '';
    }))
