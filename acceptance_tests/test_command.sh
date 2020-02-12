#!/usr/bin/env bats

setup(){
    TMPDIR="$(mktemp -d --suffix _pypi2nixpkgs_tests)"
    cd "${TMPDIR}"
}

teardown(){
    rm -rf "${TMPDIR}"
}

@test "sampleproject" {
    pypi2nixpkgs sampleproject==1.3.1
    nix-build pypi2nixpkgs/nixpkgs.nix -A python3.pkgs.sampleproject
    ./result/bin/sample | grep 'Call your main'
}
