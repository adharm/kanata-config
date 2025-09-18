Installation on MacOS:
https://github.com/jtroo/kanata/discussions/1537

Cheatsheet generation (UV):
- Requires uv (https://github.com/astral-sh/uv)
- Generate HTML: `uv run -s render-layers`
- Output: `docs/kenkyo_layers.html`

Deterministic env with Nix Flake
- Requirements: Nix with flakes enabled (on macOS), optionally nix-darwin.
- Build/run Kanata with pinned release:
  - `nix run .` runs Kanata with `kenkyo.kbd`.
  - `nix run .#kanata -- --help` runs the raw binary.
- Install Karabiner (pinned DMG) via helper script:
  - `nix develop -c install-karabiner` (uses `sudo` and `installer`)
  - Approve system extensions in System Settings if prompted.
- Update pinned hashes:
  - First build will fail with a fixed-output hash mismatch and print the correct `sha256`.
  - Replace `lib.fakeSha256` in `flake.nix` with the printed value, then re-run.
- Optional nix-darwin module:
  - Import `darwinModules.kanata-karabiner` in your nix-darwin config to launch Kanata at login using this repo's `kenkyo.kbd`.
