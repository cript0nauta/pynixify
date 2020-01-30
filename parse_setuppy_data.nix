{ file, stdenv ? (import <nixpkgs> { }).stdenv
, unzip ? (import <nixpkgs> { }).unzip, python ? (import <nixpkgs> { }).python3
}:

let
  removeExt = fileName: builtins.elemAt (builtins.split "\\." fileName) 0;

  patchedSetuptools = python.pkgs.setuptools.overrideAttrs (ps: {
    # src = (import <nixpkgs> {}).lib.cleanSource ./setuptools;
    patches = [ ./setuptools_patch.diff ];
  });

  pythonWithPackages = python.withPackages (ps: [ patchedSetuptools ]);

in stdenv.mkDerivation {
  name = "setup.py_data_${removeExt (builtins.baseNameOf file)}";
  src = file;
  nativeBuildInputs = [ unzip ];
  buildInputs = [ pythonWithPackages ];
  buildPhase = ''
    mkdir -p $out
    PYPI2NIXKPGS=1 python setup.py install
  '';
  dontInstall = true;
}

