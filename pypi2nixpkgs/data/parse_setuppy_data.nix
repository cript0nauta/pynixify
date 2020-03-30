{ file, stdenv ? (import <nixpkgs> { }).stdenv, lib ? (import <nixpkgs> { }).lib
, unzip ? (import <nixpkgs> { }).unzip, python ? (import <nixpkgs> { }).python3
}:

let
  removeExt = fileName: builtins.elemAt (builtins.split "\\." fileName) 0;

  patchedSetuptools = python.pkgs.setuptools.overrideAttrs (ps: {
    # src = (import <nixpkgs> {}).lib.cleanSource ./setuptools;
    patches = [ ./setuptools_patch.diff ];
  });

  pythonWithPackages = python.withPackages (ps: [ patchedSetuptools ]);

  cleanSource = src:
    lib.cleanSourceWith {
      filter = name: type:
        lib.cleanSourceFilter name type && builtins.baseNameOf (toString name)
        != "pypi2nixpkgs";
      name = builtins.baseNameOf src;
      inherit src;
    };

in stdenv.mkDerivation {
  name = "setup.py_data_${removeExt (builtins.baseNameOf file)}";
  src = cleanSource file;
  nativeBuildInputs = [ unzip ];
  buildInputs = [ pythonWithPackages ];
  buildPhase = ''
    mkdir -p $out
    PYPI2NIXKPGS=1 python setup.py install
  '';
  dontInstall = true;
}

