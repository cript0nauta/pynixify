{ file, stdenv ? (import <nixpkgs> { }).stdenv
, python ? (import <nixpkgs> { }).python3, setupRequires ? [ ] }:

let
  removeExt = fileName: builtins.elemAt (builtins.split "\\." fileName) 0;

  pythonWithPackages = python.withPackages (ps:
    [ ps.setuptools ]
    ++ builtins.map (attr: builtins.getAttr attr ps) setupRequires);

in stdenv.mkDerivation {
  name = "egginfo_${removeExt (builtins.baseNameOf file)}";
  src = file;
  buildInputs = [ pythonWithPackages ];
  buildPhase = ''
    python setup.py egg_info
  '';
  installPhase = ''
    cp -rv *.egg-info $out
  '';
}
