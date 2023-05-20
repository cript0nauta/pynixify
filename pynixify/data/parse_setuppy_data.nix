{ file, stdenv ? (import <nixpkgs> { }).stdenv, lib ? (import <nixpkgs> { }).lib
, unzip ? (import <nixpkgs> { }).unzip, python ? (import <nixpkgs> { }).python3
}:

let
  removeExt = fileName: builtins.elemAt (builtins.split "\\." fileName) 0;

  patchedSetuptools = python.pkgs.setuptools.overrideAttrs (ps: {
    # src = (import <nixpkgs> {}).lib.cleanSource ./setuptools;

    patches = [
      (if lib.versionOlder "66" python.pkgs.setuptools.version then
        ./setuptools_patch.diff
      else
        ./old_setuptools_patch.diff)
    ];
    patchFlags =
      lib.optionals (lib.versionOlder "61" python.pkgs.setuptools.version) [
        "--merge"
        "-p1"
      ];

  });
  setuptoolsscm = python.pkgs.buildPythonPackage rec {
    pname = "setuptools-scm";
    version = "7.0.5";

    src = python.pkgs.fetchPypi {
      pname = "setuptools_scm";
      inherit version;
      sha256 = "sha256-Ax4Tr3cdb4krlBrbbqBFRbv5Hrxc5ox4qvP/9uH7SEQ=";
    };

    propagatedBuildInputs = [
      python.pkgs.packaging
      python.pkgs.typing-extensions
      python.pkgs.tomli
      patchedSetuptools
    ];

    pythonImportsCheck = [ "setuptools_scm" ];

    # check in passthru.tests.pytest to escape infinite recursion on pytest
    doCheck = false;
  };
  hatchling = python.pkgs.hatchling.overrideAttrs
    (ps: { patches = [ ./hatchling_patch.diff ]; });
  hatchvcs = python.pkgs.buildPythonPackage rec {
    pname = "hatch-vcs";
    version = "0.2.0";
    format = "pyproject";

    disabled = python.pkgs.pythonOlder "3.7";

    src = python.pkgs.fetchPypi {
      pname = "hatch_vcs";
      inherit version;
      sha256 = "sha256-mRPXM7NO7JuwNF0GJsoyFlpK0t4V0c5kPDbQnKkIq/8=";
    };

    nativeBuildInputs = [ hatchling ];

    propagatedBuildInputs = [ hatchling setuptoolsscm ];

    checkInputs = [ pkgs.git python.pkgs.pytestCheckHook ];

    disabledTests = [
      # incompatible with setuptools-scm>=7
      # https://github.com/ofek/hatch-vcs/issues/8
      "test_write"
    ];

    pythonImportsCheck = [ "hatch_vcs" ];
  };
  patchedflitcore = python.pkgs.flit-core.overrideAttrs
    (ps: { patches = [ ./flitcore_patch.diff ]; });
  flitscm = python.pkgs.buildPythonPackage rec {
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
      [ patchedflitcore setuptoolsscm python.pkgs.tomli pkgs.git ];
    propagatedBuildInputs = [ patchedflitcore setuptoolsscm ]
      ++ pkgs.lib.optionals (python.pkgs.pythonOlder "3.11")
      [ python.pkgs.tomli ];
  };

  pythonWithPackages = python.withPackages (ps: [
    patchedSetuptools
    setuptoolsscm
    hatchling
    hatchvcs
    flitscm
    python.pkgs.pip
  ]);

  cleanSource = src:
    lib.cleanSourceWith {
      filter = name: type:
        lib.cleanSourceFilter name type && builtins.baseNameOf (toString name)
        != "pynixify";
      name = builtins.baseNameOf src;
      inherit src;
    };

in stdenv.mkDerivation {
  name = "setup.py_data_${removeExt (builtins.baseNameOf file)}";
  src = cleanSource file;
  nativeBuildInputs = [ unzip ];
  buildInputs = [ pythonWithPackages ];
  configurePhase = ''
    true  # We don't want to execute ./configure
  '';
  buildPhase = ''
    mkdir -p $out
    if PYNIXIFY=1 python setup.py install; then
        exit 0
    fi
    if ${python.pkgs.pip}/bin/pip --no-cache-dir wheel --config-settings PYNIXIFY_OUT=$out --no-build-isolation $PWD; then
        exit 0
    fi
    # Indicate that fetching the result failed, but let the build succeed
    touch $out/failed
  '';
  dontInstall = true;
}

