{ file, python, stdenv ? (import <nixpkgs> { }).stdenv, lib ? (import <nixpkgs> { }).lib
, unzip ? (import <nixpkgs> { }).unzip, git ? (import <nixpkgs> { }).git
, fetchFromGitLab ? (import <nixpkgs> { }).fetchFromGitLab
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

  pythonWithPackages = python.withPackages (ps: [ patchedSetuptools ]);

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
    if ! PYNIXIFY=1 python setup.py install; then
      # Indicate that fetching the result failed, but let the build succeed
      touch $out/failed
    fi
  '';
  dontInstall = true;
}

