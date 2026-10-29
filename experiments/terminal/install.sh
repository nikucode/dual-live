#!/usr/bin/env bash
set -euo pipefail

source_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
target_dir="${HOME}/.local/bin"
target="${target_dir}/dual-live"

if [[ -e "$target" && ! -L "$target" ]]; then
  printf 'Ya existe un archivo en %s; no se reemplazó.\n' "$target" >&2
  exit 1
fi

mkdir -p -- "$target_dir"
ln -sfn -- "$source_dir/dual-live" "$target"
printf 'Comando instalado: %s\n' "$target"
printf 'Prueba: dual-live\n'
