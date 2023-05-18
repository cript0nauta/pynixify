{ file, pkgs ? import (builtins.fetchGit {
  name = "nixos-22.11";
  url = "https://github.com/nixos/nixpkgs/";
  # `git ls-remote https://github.com/nixos/nixpkgs nixos-unstable`
  ref = "refs/heads/nixos-22.11";
  rev = "6c591e7adc514090a77209f56c9d0c551ab8530d";
}) { } }:

let
  removeExt = fileName: builtins.elemAt (builtins.split "\\." fileName) 0;

  patchedSetuptools = pkgs.python3.pkgs.setuptools.overrideAttrs (ps: {
    patches = [ ./setuptools_patch.diff ];
    patchFlags = pkgs.lib.optionals
      (pkgs.lib.versionOlder "61" pkgs.python3.pkgs.setuptools.version) [
        "--merge"
        "-p1"
      ];
  });

  setuptoolsscm = pkgs.python3.pkgs.buildPythonPackage rec {
    pname = "setuptools-scm";
    version = "7.0.5";

    src = pkgs.python3.pkgs.fetchPypi {
      pname = "setuptools_scm";
      inherit version;
      sha256 = "sha256-Ax4Tr3cdb4krlBrbbqBFRbv5Hrxc5ox4qvP/9uH7SEQ=";
    };

    propagatedBuildInputs = [
      pkgs.python3.pkgs.packaging
      pkgs.python3.pkgs.typing-extensions
      pkgs.python3.pkgs.tomli
      patchedSetuptools
    ];

    pythonImportsCheck = [ "setuptools_scm" ];

    # check in passthru.tests.pytest to escape infinite recursion on pytest
    doCheck = false;
  };
  hatchling = pkgs.python3.pkgs.hatchling.overrideAttrs
    (ps: { patches = [ ./hatchling_patch.diff ]; });
  hatchvcs = pkgs.python3.pkgs.buildPythonPackage rec {
    pname = "hatch-vcs";
    version = "0.2.0";
    format = "pyproject";

    disabled = pkgs.python3.pkgs.pythonOlder "3.7";

    src = pkgs.python3.pkgs.fetchPypi {
      pname = "hatch_vcs";
      inherit version;
      sha256 = "sha256-mRPXM7NO7JuwNF0GJsoyFlpK0t4V0c5kPDbQnKkIq/8=";
    };

    nativeBuildInputs = [ hatchling ];

    propagatedBuildInputs = [ hatchling setuptoolsscm ];

    checkInputs = [ pkgs.git pkgs.python3.pkgs.pytestCheckHook ];

    disabledTests = [
      # incompatible with setuptools-scm>=7
      # https://github.com/ofek/hatch-vcs/issues/8
      "test_write"
    ];

    pythonImportsCheck = [ "hatch_vcs" ];
  };
  patchedflitcore = pkgs.python3.pkgs.flit-core.overrideAttrs
    (ps: { patches = [ ./flitcore_patch.diff ]; });
  flitscm = pkgs.python3.pkgs.buildPythonPackage rec {
    pname = "flit-scm";
    version = "1.7.0";

    format = "pyproject";

    src = pkgs.fetchFromGitLab {
      owner = "WillDaSilva";
      repo = "flit_scm";
      rev = version;
      sha256 = "sha256-K5sH+oHgX/ftvhkY+vIg6wUokAP96YxrTWds3tnEtyg=";
      leaveDotGit = true;
    };

    nativeBuildInputs =
      [ patchedflitcore setuptoolsscm pkgs.python3.pkgs.tomli pkgs.git ];
    propagatedBuildInputs = [ patchedflitcore setuptoolsscm ]
      ++ pkgs.lib.optionals (pkgs.python3.pkgs.pythonOlder "3.11")
      [ pkgs.python3.pkgs.tomli ];
  };
  patchedpip = pkgs.python3.pkgs.pip.overrideAttrs
    (ps: { patches = [ ./pip_patch_final.diff ]; });

  pythonWithPackages = pkgs.python3.withPackages (ps: [
    patchedSetuptools
    setuptoolsscm
    hatchling
    hatchvcs
    flitscm
    patchedpip
  ]);

  cleanSource = src:
    pkgs.lib.cleanSourceWith {
      filter = name: type:
        pkgs.lib.cleanSourceFilter name type
        && builtins.baseNameOf (toString name) != "pynixify";
      name = builtins.baseNameOf src;
      inherit src;
    };

in pkgs.stdenv.mkDerivation {
  name = "setup.py_data_${removeExt (builtins.baseNameOf file)}";
  src = cleanSource file;
  nativeBuildInputs = [ pkgs.unzip ];
  buildInputs = [ pythonWithPackages pkgs.hatch ];
  configurePhase = ''
    true  # We don't want to execute ./configure
  '';
  buildPhase = ''
    mkdir -p $out
    if PYNIXIFY=1 python setup.py install; then
        exit 0
    fi
    #${patchedpip}/bin/pip --no-cache-dir wheel --config-settings PYNIXIFY_OUT=$out --no-build-isolation $PWD
    if ${patchedpip}/bin/pip --no-cache-dir wheel --config-settings PYNIXIFY_OUT=$out --no-build-isolation $PWD; then
        exit 0
    fi
    # Indicate that fetching the result failed, but let the build succeed
    touch $out/failed
  '';
  dontInstall = true;
}

