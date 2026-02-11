#!/usr/bin/env bash
# Wrapper to run whatsapp MCP server using Nix-native Python
# This avoids the NixOS FHS incompatibility with uv-downloaded Python

cd "$(dirname "$0")"

exec nix-shell -p "python313.withPackages (ps: with ps; [ fastmcp httpx requests ])" \
  --run "python main.py"
