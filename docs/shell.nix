let
  pkgs = import <nixpkgs> {};
in pkgs.mkShell {
  packages = [
    pkgs.mkdocs
    (pkgs.python3.withPackages (python-pkgs: [
      python-pkgs.mkdocs-material
      python-pkgs.requests
    ]))
  ];
}

