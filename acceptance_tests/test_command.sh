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

    # Temporary files should be removed
    echo ${TMPDIR}/pypi2nixpkgs_*
    [[ -z "$(find "${TMPDIR}" -maxdepth 1 -name 'pypi2nixpkgs_*' -print -quit)" ]]
    grep "A sample Python project" pypi2nixpkgs/packages/sampleproject.nix
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
    grep 'fetchPypi {' pypi2nixpkgs/packages/faraday-agent-dispatcher.nix
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

@test "pin nixpkgs 2" {
    # This tests that the pinned nixpkgs is used not only in the generated
    # expression, but also when discovering nix packages
    NIXPKGS_COMMIT=f1f5247103494195d00afd0b0f4ae789dedfd0e4
    pypi2nixpkgs psycopg2==2.7.7 \
        --nixpkgs "https://github.com/nixos/nixpkgs/archive/$NIXPKGS_COMMIT.tar.gz"
    if [[ -f pypi2nixpkgs/packages/psycopg2.nix ]]; then
        echo "Didn't use nixpkgs version of psycopg2"
        exit 1
    fi
    nix-build pypi2nixpkgs/nixpkgs.nix -A python3.pkgs.psycopg2
}

@test "--output-dir" {
    pypi2nixpkgs sampleproject==1.3.1 --output-dir my-pypi2nixpkgs-dir
    nix-build my-pypi2nixpkgs-dir/nixpkgs.nix -A python3.pkgs.sampleproject
    ./result/bin/sample | grep 'Call your main'
}
