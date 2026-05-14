#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HARNESS_HOME="${HARNESS_HOME:-$HOME/.harness}"
RUNTIME_DIR="$HARNESS_HOME/harness"
BIN_DIR="${BIN_DIR:-$HOME/.local/bin}"
CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"

mkdir -p "$HARNESS_HOME" "$BIN_DIR"
rm -rf "$RUNTIME_DIR"
mkdir -p "$RUNTIME_DIR"

cp -R "$ROOT"/. "$RUNTIME_DIR"/
chmod +x "$RUNTIME_DIR/scripts/harness.py"

cat > "$BIN_DIR/harness" <<EOF
#!/usr/bin/env bash
exec python3 "$RUNTIME_DIR/scripts/harness.py" "\$@"
EOF
chmod +x "$BIN_DIR/harness"

if [ -d "$CODEX_HOME" ]; then
  mkdir -p "$CODEX_HOME/skills"
  rm -rf "$CODEX_HOME/skills/harness"
  cp -R "$RUNTIME_DIR" "$CODEX_HOME/skills/harness"
fi

if [ ! -f "$HARNESS_HOME/projects.json" ]; then
  printf '{}\n' > "$HARNESS_HOME/projects.json"
fi

if [ ! -f "$HARNESS_HOME/skills.json" ]; then
  printf '[]\n' > "$HARNESS_HOME/skills.json"
fi

echo "Harness installed at $RUNTIME_DIR"
echo "CLI installed at $BIN_DIR/harness"
echo "Add $BIN_DIR to PATH if needed."
