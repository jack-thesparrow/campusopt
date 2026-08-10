{
  description = "CampusOpt dev environment";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs { inherit system; };
      in
      {
        devShells.default = pkgs.mkShell {
          buildInputs = [
            pkgs.python311
            pkgs.python311Packages.pip
            pkgs.python311Packages.virtualenv
            pkgs.nodejs_22 # only needed for the optional React v2 frontend
            pkgs.act
          ];

          shellHook = ''
            if [ ! -d .venv-nix-extras ]; then
              echo "Creating .venv-nix-extras ..."
              python -m venv .venv-nix-extras
            fi
            source .venv-nix-extras/bin/activate
            if [ -f backend/requirements.txt ]; then
              pip install -q -r backend/requirements.txt
            fi
            echo "CampusOpt dev shell ready. See docs/Toolchain.md."
          '';
        };
      });
}
