#!/usr/bin/env bash
set -euo pipefail

repo_url="${ORCD_AGENT_REPO_URL:-https://github.com/terrytwk/orcd-agent.git}"
install_url="${ORCD_AGENT_INSTALL_URL:-https://raw.githubusercontent.com/terrytwk/orcd-agent/main/install.sh}"
install_dir="${ORCD_AGENT_HOME:-$HOME/.orcd-agent}"
update_profile="${ORCD_AGENT_UPDATE_PROFILE:-1}"

run_step() {
  printf '\n==> %s\n' "$*"
  "$@"
}

ensure_module_command() {
  if type module >/dev/null 2>&1; then
    return 0
  fi
  for init_script in /etc/profile.d/modules.sh /usr/share/Modules/init/bash; do
    if [ -r "$init_script" ]; then
      # shellcheck disable=SC1090
      source "$init_script"
      break
    fi
  done
}

profile_file() {
  case "${SHELL:-}" in
    */zsh) printf '%s\n' "$HOME/.zshrc" ;;
    */bash) printf '%s\n' "$HOME/.bashrc" ;;
    *) printf '%s\n' "$HOME/.profile" ;;
  esac
}

persist_path() {
  if [ "$update_profile" = "0" ]; then
    printf '\n==> skipping shell profile update because ORCD_AGENT_UPDATE_PROFILE=0\n'
    return 0
  fi

  local profile marker_start marker_end path_line backup
  profile="$(profile_file)"
  marker_start="# >>> orcd-agent >>>"
  marker_end="# <<< orcd-agent <<<"
  path_line="export PATH=\"$install_dir/bin:\$PATH\""

  mkdir -p "$(dirname "$profile")"
  touch "$profile"

  if grep -Fq "$marker_start" "$profile"; then
    printf '\n==> shell profile already contains an ORCD Agent PATH block: %s\n' "$profile"
    return 0
  fi

  backup="${profile}.orcd-agent.bak.$(date +%Y%m%d%H%M%S)"
  cp "$profile" "$backup"

  printf '\n==> adding ORCD Agent PATH block to %s\n' "$profile"
  {
    printf '\n%s\n' "$marker_start"
    printf '%s\n' "$path_line"
    printf '%s\n' "$marker_end"
  } >> "$profile"
  printf 'Backed up previous profile to %s\n' "$backup"
}

printf 'ORCD Agent bootstrap\n'
printf 'Repository: %s\n' "$repo_url"
printf 'Install dir: %s\n' "$install_dir"

printf '\n==> curl -fsSL %s | bash\n' "$install_url"
curl -fsSL "$install_url" | bash

export PATH="$install_dir/bin:$PATH"
printf '\n==> export PATH="%s/bin:$PATH"\n' "$install_dir"
persist_path

ensure_module_command
if type module >/dev/null 2>&1; then
  printf '\n==> module load miniforge\n'
  module load miniforge
else
  printf '\nERROR: module command is not available in this shell.\n' >&2
  printf 'Run this from an ORCD login shell, or load Miniforge manually before syncing docs.\n' >&2
  exit 1
fi

run_step python3 "$install_dir/scripts/sync_docs.py"

cat <<EOF

ORCD Agent is installed.

For this shell, run this if orcd-agent is not already found:
  export PATH="$install_dir/bin:\$PATH"

For future shells, the bootstrap added a managed PATH block to:
  $(profile_file)

Try:
  orcd-agent docs index
  orcd-agent docs grep "miniforge"
EOF
