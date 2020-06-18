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
    grep "A sample Python project" pypi2nixpkgs/packages/sampleproject/default.nix
}

@test "sampleproject in python 3.8" {
    pypi2nixpkgs sampleproject==1.3.1
    nix-build pypi2nixpkgs/nixpkgs.nix -A python38.pkgs.sampleproject
    ./result/bin/sample | grep 'Call your main'
}

@test "sampleproject in python 2.7" {
    pypi2nixpkgs sampleproject==1.3.1
    nix-build pypi2nixpkgs/nixpkgs.nix -A python27.pkgs.sampleproject
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
    grep 'fetchPypi {' pypi2nixpkgs/packages/faraday-agent-dispatcher/default.nix
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
    if [[ -f pypi2nixpkgs/packages/psycopg2/default.nix ]]; then
        echo "Didn't use nixpkgs version of psycopg2"
        exit 1
    fi
    nix-build pypi2nixpkgs/nixpkgs.nix -A python3.pkgs.psycopg2
}

@test "--output-dir" {
    pypi2nixpkgs sampleproject==1.3.1 -o my-pypi2nixpkgs-dir
    nix-build my-pypi2nixpkgs-dir/nixpkgs.nix -A python3.pkgs.sampleproject
    ./result/bin/sample | grep 'Call your main'
}

@test "no --load-test-requirements-for" {
    pypi2nixpkgs pytest 'textwrap3==0.9.1'
    ! grep 'pytest' pypi2nixpkgs/packages/textwrap3/default.nix
    nix-build pypi2nixpkgs/nixpkgs.nix -A python3.pkgs.textwrap3
}

@test "--load-test-requirements-for" {
    pypi2nixpkgs --tests=teXtwrap3 'textwrap3==0.9.1'
    nix-build pypi2nixpkgs/nixpkgs.nix -A python3.pkgs.textwrap3
    nix-store -qR result | { ! grep pytest; }
    grep 'pytest' pypi2nixpkgs/packages/textwrap3/default.nix
    git clone https://github.com/jonathaneunice/textwrap3
    cd textwrap3
    git checkout f6cd3e05be255011a5ef1bd442574d104a0050cb
    nix-shell ../pypi2nixpkgs/nixpkgs.nix -A python3.pkgs.textwrap3 --command py.test
}

@test "--load-all-test-requirements" {
    pypi2nixpkgs --all-tests 'textwrap3==0.9.1'
    nix-build pypi2nixpkgs/nixpkgs.nix -A python3.pkgs.textwrap3
    nix-store -qR result | { ! grep pytest; }
    grep 'pytest' pypi2nixpkgs/packages/textwrap3/default.nix
    git clone https://github.com/jonathaneunice/textwrap3
    cd textwrap3
    git checkout f6cd3e05be255011a5ef1bd442574d104a0050cb
    nix-shell ../pypi2nixpkgs/nixpkgs.nix -A python3.pkgs.textwrap3 --command py.test
}

@test "--ignore-test-requirements-for" {
    # filedepot depends on boto3, which depends on botocore, which isn't
    # compatible with the nixpkgs version of docutils (actually, it is, but it
    # requires patching the source)
    pypi2nixpkgs --all-tests --ignore-tests=filedepot \
        docutils filedepot
    nix-build pypi2nixpkgs/nixpkgs.nix -A python3.pkgs.filedepot
}
