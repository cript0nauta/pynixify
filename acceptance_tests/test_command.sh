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

@test "sampleproject-local" {
    git clone https://github.com/pypa/sampleproject
    cd sampleproject
    sed -i 's/your/my/' src/sample/__init__.py
    pypi2nixpkgs --local sampleproject
    nix-build pypi2nixpkgs/nixpkgs.nix -A python3.pkgs.sampleproject
    ./result/bin/sample | grep 'Call my main'
}

@test "faraday-agent-dispatcher" {
    pypi2nixpkgs faraday-agent-dispatcher
    nix-build pypi2nixpkgs/nixpkgs.nix -A python3.pkgs.faraday-agent-dispatcher
    ./result/bin/faraday-dispatcher --help
}
