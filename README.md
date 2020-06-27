# pynixify - Nix expression generator for Python projects

## Why another Python-to-Nix tool?

pynixify has the following objectives, which other alternatives don't satisfy
(at least from my point of view):

* Be usable in big projects: pynixify was initially developed to build a Nix
  expression for Faraday, a project with [lots of dependencies][deps], some of which
  weren't packaged in Nixpkgs. Most alternatives to this tool didn't work properly
  because they weren't reusing Nixpkgs packages.
* Reuse Nixpkgs expressions: instead of writing expressions for all transitive
  dependencies from scratch, take as much as possible from Nixpkgs. This makes
  it possible to use packages with system dependencies or with complex build steps,
  such as Pillow.
* Generate human-readable expressions: the generated code is properly formatted and
  uses Nixpkgs best practices (such as adding package metadata and including test
  dependencies). This facilitates contributing to Nixpkgs, since the generated
  expression will be of "Nixpkgs quality". [Here][expression] is an example of the
  expression of pynixify itself. 

[expression]: https://github.com/cript0nauta/pynixify/blob/master/nix/packages/pynixify/default.nix
[deps]: https://github.com/infobyte/faraday/blob/master/requirements.txt

## Installation

The only supported installation method is using Nix:

```
$ git clone https://github.com/cript0nauta/pynixify.git
$ cd pynixify
$ nix-env -if .
```

## Usage

### Using a PyPI package not available in Nixpkgs

Lets suppose you want to use pypa's [sampleproject][sampleproject]. Sadly,
Nixpkgs doesn't provide a `python3Packages.sampleproject` attribute yet. This
means you'll have to write it. This isn't too difficult, but can be tedious,
especially with projects with many dependencies. Instead, you can use pynixify
to build the expression for you:

```
$ pynixify sampleproject
Resolving sampleproject
Resolving peppercorn (from PyPIPackage(attr=sampleproject, version=2.0.0))

$ nix-build pynixify/nixpkgs.nix -A python3Packages.sampleproject
/nix/store/fpa32bnl2r5vwdsybrz8bvw7qhcvvik3-python3.7-sampleproject-2.0.0

$ ./result/bin/sample
Call your main application code here
```

The generated [`pynixify/nixpkgs.nix`][nixpkgs.nix] file should be used as a
replacement of `<nixpkgs>`. It includes an overlay with all package definitions
generated in `pynixify/packages/`. In this case, it will include the definition
for `sampleproject`.

[sampleproject]: https://pypi.org/project/sampleproject/
[nixpkgs.nix]: https://github.com/cript0nauta/pynixify/blob/master/nix/nixpkgs.nix

### Developing a Python package

When you're developing, is isn't useful to fetch the package source from PyPI.
It would be better to use a local directory, so the changes you made are
instantly reflected. When you use the `--local` option, pynixify will use the
current directory as the package source, making package development easier:

```
$ git clone https://github.com/pypa/sampleproject.git

$ cd sampleproject/

$ pynixify --local sampleproject
Resolving sampleproject
Resolving peppercorn (from PyPIPackage(attr=sampleproject, version=0.1dev))

$ nix-shell pynixify/nixpkgs.nix -A python3Packages.sampleproject

[nix-shell:/tmp/sampleproject]$ echo "    print('Hello from pynixify!')" >>src/sample/__init__.py

[nix-shell:/tmp/sampleproject]$ sample
Call your main application code here
Hello from pynixify!
```

Using both `nix-shell` and `nix-build` will use the current directory as
source. The `--local` option is also useful if you include your `pynixify/`
directory inside your Git repository. This facilitates setting up a development
environment of your project.

### Pinning Nixpkgs

If you include the `pynixify/` directory inside your Git repository, it is
recommended to use a pinned version of Nixpkgs. This will improve
reproducibility between different machines. pynixify's `--nixpkgs` option
makes the generated expression use an exact version of nixpkgs:

```
$ pynixify sampleproject --nixpkgs https://github.com/NixOS/nixpkgs/archive/748c9e0e3ebc97ea0b46a06295465eff2fb5ef92.tar.gz

$ cat pynixify/nixpkgs.nix
[...]
  nixpkgs =

    builtins.fetchTarball {
      url =
        "https://github.com/NixOS/nixpkgs/archive/748c9e0e3ebc97ea0b46a06295465eff2fb5ef92.tar.gz";
      sha256 = "158xblbbjv54n9a7b1y88jjjag2w5lb77dqfx0d4z2b32ss0p7mc";
    };
[...]
```
