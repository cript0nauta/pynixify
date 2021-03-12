with (import <nixpkgs> { });

let
  allPackages = python3Packages;

  validPackages =
    lib.filterAttrs (k: v: (builtins.tryEval v).success) allPackages;

  attrsToList = a:
    builtins.attrValues (lib.mapAttrs (key: value: { inherit key value; })
    # Note: __unfix__ is not a python package, it is related to fixed point stuff
      (builtins.removeAttrs a [ "__unfix__" ]));


  lookUpSource = name: value:
    let 
      d = {attr=name; version=value.version;};
    in
      if !value ? src then [ (d // {src=null;})]
      else if !(builtins.tryEval value.src ).success then [ ]
      else if !value.src ? urls then [(d // {src=null;})]
      else [ (d // {src=builtins.head value.src.urls;})];

  sources = packages:
    lib.concatMap ({ key, value }:
    if !(builtins.tryEval value).success  then [ ]
    else if builtins.isNull value then
      # Example: python3Packages.backports_lzma
        [ ]
      else if !value ? version then
      # Example: python3Packages.dlib
        [ ]
      else lookUpSource key value) (attrsToList packages);

  urlToPypiName = url:
    if builtins.isNull url then
      null
    else
      let
        match = builtins.match "mirror://pypi/./([^/]+)/.*" url;
        match2 = builtins.match
          "https://files.pythonhosted.org/packages/[^/]+/./([^/]+)/.*" url;
      in if !(builtins.isNull match) then
        builtins.head match
      else if !(builtins.isNull match2) then
        builtins.head match2
      else
        null;

  keepPypi = sources:
    # Filter the result of sources by only keeping entries whose source
    # belongs to pypi. Add the pypiName attr to each kept entry
    builtins.filter (e: !(builtins.isNull e.pypiName))
    (builtins.map (e: e // { pypiName = urlToPypiName e.src; }) sources);

  usePypiNameIfPossible = sources:
    # Get the PyPI name of a derivation from its source URL. If it's not
    # possible, use the attr name
    builtins.map (e:
      e // {
        pypiName = if (builtins.isNull (urlToPypiName e.src)) then
          e.attr
        else
          urlToPypiName e.src;
      }) sources;

  pipe = l:
    let
      elem = builtins.head l;
      funcChain = builtins.tail l;
    in lib.foldl (acc: f: f acc) elem funcChain;

  # lib.groupBy (x: x.pypiName) (keepPypi (sources validPackages))
in pipe [
  python3Packages
  sources
  # keepPypi
  usePypiNameIfPossible
  (lib.groupBy (x: x.pypiName))
]
