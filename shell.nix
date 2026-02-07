{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {    
  nativeBuildInputs = with pkgs.buildPackages; [
    gcc14
    python312Full
    nodejs_23
    wabt
    fasm-bin
    musl
    python312Packages.pytest
  ];
}