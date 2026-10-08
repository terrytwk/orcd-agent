#!/usr/bin/env bash
set -euo pipefail

install_dir="${ORCD_AGENT_HOME:-$HOME/.orcd-agent}"
repo_url="${ORCD_AGENT_REPO_URL:-https://github.com/mit-orcd/orcd-agent.git}"
branch="${ORCD_AGENT_BRANCH:-main}"

copy_tree() {
  local source="$1"
  mkdir -p "$install_dir"
  for path in AGENTS.md bin docs templates scripts README.md; do
    if [ -e "$source/$path" ]; then
      rm -rf "$install_dir/$path"
      cp -R "$source/$path" "$install_dir/$path"
    fi
  done
}

if [ -f "./AGENTS.md" ] && [ -d "./bin" ]; then
  copy_tree "$(pwd)"
else
  tmp="$(mktemp -d)"
  cleanup() {
    rm -rf "$tmp"
  }
  trap cleanup EXIT
  if command -v git >/dev/null 2>&1; then
    git clone --depth 1 --branch "$branch" "$repo_url" "$tmp/orcd-agent"
  else
    archive="https://github.com/${repo_url#https://github.com/}"
    archive="${archive%.git}/archive/refs/heads/$branch.tar.gz"
    curl -fsSL "$archive" | tar -xz -C "$tmp"
    mv "$tmp"/* "$tmp/orcd-agent"
  fi
  copy_tree "$tmp/orcd-agent"
fi

chmod +x "$install_dir"/bin/orcd-* 2>/dev/null || true

echo "Installed ORCD Agent to $install_dir"
case ":$PATH:" in
  *":$install_dir/bin:"*) ;;
  *)
    echo
    echo "Add this to your shell profile:"
    echo "  export PATH=\"$install_dir/bin:\$PATH\""
    echo
    echo "For this shell, run:"
    echo "  export PATH=\"$install_dir/bin:\$PATH\""
    ;;
esac
