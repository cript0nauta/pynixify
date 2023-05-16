{ file, pkgs ? import <nixpkgs> { } }:

let
  removeExt = fileName: builtins.elemAt (builtins.split "\\." fileName) 0;

  patchedSetuptools = pkgs.python3.pkgs.setuptools.overrideAttrs (ps: {
    # src = (import <nixpkgs> {}).lib.cleanSource ./setuptools;

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

  pythonWithPackages =
    pkgs.python3.withPackages (ps: [ patchedSetuptools hatchling hatchvcs ]);

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
    if test -f pyproject.toml && grep "hatchling.build" pyproject.toml; then
        echo 'mode = "local"' > config.toml
        if PYNIXIFY=1 hatch --config config.toml --data-dir $out/data --cache-dir $out/cache build; then
            exit 0
        fi
    fi
    # Indicate that fetching the result failed, but let the build succeed
    touch $out/failed
  '';
  dontInstall = true;
}

