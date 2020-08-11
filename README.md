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

[expression]: https://github.com/cript0nauta/pynixify/blob/main/nix/packages/pynixify/default.nix
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
[nixpkgs.nix]: https://github.com/cript0nauta/pynixify/blob/main/nix/nixpkgs.nix

### Developing a Python package

When you're developing a package, fetching its source from PyPI won't be
useful. It would be better to use a local directory, so the changes you made in
your machine are instantly reflected. When you use the `--local` option,
pynixify will use the current directory as the package source, making package
development easier:

```
$ git clone https://github.com/pypa/sampleproject.git

$ cd sampleproject/

$ pynixify --local sampleproject
Resolving sampleproject
Resolving peppercorn (from PyPIPackage(attr=sampleproject, version=0.1dev))

$ nix-shell pynixify/nixpkgs.nix -A python3Packages.sampleproject

[nix-shell:/tmp/sampleproject]$ echo "    print('Hello from pynixify! ')" >>src/sample/__init__.py

[nix-shell:/tmp/sampleproject]$ sample
Call your main application code here
Hello from pynixify!
```

Using both `nix-shell` and `nix-build` will use the current directory as
source. The `--local` option is also useful if you include your `pynixify/`
directory inside your Git repository. This facilitates setting up a development
environment of your project.

<a id="pinning-nixpkgs"></a>
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

### Developing a project without a setup.py

Some Python projects don't have a `setup.py` file to indicate how should they
be built. In most cases, they just have a `requirements.txt` file indicating
which packages need to be installed. If this is the case of your project, you
can use the `pynixify/shell.nix` file to setup a virtualenv-like environment
with all requirements installed:

```
$ pynixify -r requirements.txt
$ nix-shell pynixify/shell.nix
```

You can also specify which version of Python you want:
```
$ nix-shell pynixify/shell.nix --argstr python python36
```

## Suggested structure for your existing project

Using pynixify can be a great way to introduce Nix to your team. Instead of
complex Dockerfiles and install scripts, developers can just run `nix-shell`
and set up a reproducible development environment immediately!

In addition to adding the `pynixify/` directory to your Git repo, it is
suggested to manually create a `default.nix` similar to [pynixify's
one][defaultnix] (you may also want to [pin Nixpkgs](#pinning-nixpkgs)). This
provides some advantages over using the `pynixify/` files directly:

* Want to build the project? Just run `nix-build` with no arguments. There is
  no more `nix-build pynixify/nixpkgs.nix -A yourProjectName`.
* There is no need for an additional `shell.nix` file, since
  `buildPythonPackage` activates the development mode automatically when using
  `nix-shell`. Just a `default.nix` file is good enough.
* As detailed in the [example file][defaultnix], you can override the generated
  package to add system dependencies in case they're needed .

For a real life example, you can look at [Faraday's release.nix
file][releasenix]. It uses pynixify's generated definition, overrides a few
things and adds instructions to build a Docker image and a Systemd unit for
the project.

[defaultnix]: https://github.com/cript0nauta/pynixify/blob/main/default.nix
[releasenix]: https://github.com/infobyte/faraday/blob/dev/release.nix

## Limitations

pynixify tries to reuse Nixpkgs packages whenever possible. Although this is
mostly consireded a good thing, it has some drawbacks:

* **You won't be using the latest PyPI packages**, but the versions available in
  Nixpkgs, which can be older. If you must a newer version of a library,
  consider adding `>=` to its requirement. If the library has a standard build mechanism,
  that will work fine. Otherwise, it is recommended to manually change the
  library's version in the Nixpkgs repository.
* Your requirements file shouldn't be the output of `pip freeze` because it has
  `==` in all requirements. Therefore, it makes reusing Nixpkgs packages harder. You
  shouldn't treat your requirements file as a lockfile, but as an abstract 
  definition indicating the minimum and maximum versions of each library. Keep in mind that
  **you don't need a lockfile**: you can just [pin Nixpkgs](#pinning-nixpkgs) to have something
  with the reproducibility of lockfiles. Or even better than it, since Nix also
  tracks the system dependencies of each library!

```
# A bad requirements.txt file
certifi==2020.6.20
chardet==3.0.4
idna==2.10
requests==2.24.0
tqdm==4.48.2
urllib3==1.25.10
```

```
# A great requirements.txt file
requests
tqdm>=4.47.0
```


## Similar software

* [mach-nix][mach-nix]: A good alternative to pynixify. It is more focused on
  non-Nix users, while pynixify targets users with experience using Nix, and
  wanting to contribute to its ecosystem via Nixpkgs Pull requests.
* [pypi2nix][pypi2nix]

[mach-nix]: https://github.com/DavHau/mach-nix
[pypi2nix]: https://github.com/nix-community/pypi2nix


## Contributing

PRs and issues describing bugs packaging some libraries are more than welcome!

To setup a development environment, just clone this repo and run `nix shell`.

pynixify has three different test suites:

* unit tests, which are designed to be fast and isolated
* "acceptance" tests which require network access and are slower
* [bats][bats] end to end tests, which test running the `pynixify` command with different options

You can run all three of them inside nix-shell:

```
$ pytest tests/ acceptance_tests/
$ bats acceptance_tests/test_command.sh
```

They're also run on each push using GitHub actions.

[bats]: https://github.com/sstephenson/bats
