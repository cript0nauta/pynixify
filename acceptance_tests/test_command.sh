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

@test "pin nixpkgs" {
    NIXPKGS_COMMIT=f1f5247103494195d00afd0b0f4ae789dedfd0e4
    pypi2nixpkgs flask \
        --nixpkgs "https://github.com/nixos/nixpkgs/archive/$NIXPKGS_COMMIT.tar.gz"
    cat pypi2nixpkgs/nixpkgs.nix
    nix-build pypi2nixpkgs/nixpkgs.nix -A python3.pkgs.flask
    if ! ./result/bin/flask --version | grep 'Flask 1.0.4'
    then
        echo Invalid Flask version:
        ./result/bin/flask --version
        exit 1
    fi
}
