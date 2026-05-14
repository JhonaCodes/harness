#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HARNESS_HOME="${HARNESS_HOME:-$HOME/.harness}"
RUNTIME_DIR="$HARNESS_HOME/harness"
BIN_DIR="${BIN_DIR:-$HOME/.local/bin}"
CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
CLAUDE_HOME="${CLAUDE_HOME:-$HOME/.claude}"
GEMINI_HOME="${GEMINI_HOME:-$HOME/.gemini}"
OPENCODE_HOME="${OPENCODE_HOME:-$HOME/.config/opencode}"
TARGETS_RAW="${HARNESS_TARGETS:-}"

usage() {
  cat <<'EOF'
Install Harness runtime and optional LLM entrypoints.

Usage:
  ./install.sh
  ./install.sh --targets codex,claude,gemini,opencode
  ./install.sh --targets manual
  HARNESS_TARGETS=codex,opencode ./install.sh

Targets:
  codex       Install Codex skill in $CODEX_HOME/skills/harness.
  claude      Install Claude Code slash command in $CLAUDE_HOME/commands/harness.md.
  gemini      Add a managed Harness section to $GEMINI_HOME/GEMINI.md.
  opencode    Add a managed Harness section to $OPENCODE_HOME/AGENTS.md.
  manual      Print manual setup instructions for any LLM.
  all         Install all targets.
  none        Install only runtime and CLI.

The runtime and CLI are always installed. Targets control only tool-specific
entrypoints that let each LLM discover Harness automatically.
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --targets)
      if [ "$#" -lt 2 ]; then
        echo "Missing value for --targets" >&2
        exit 2
      fi
      TARGETS_RAW="$2"
      shift 2
      ;;
    --targets=*)
      TARGETS_RAW="${1#--targets=}"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

prompt_targets() {
  cat >&2 <<'EOF'
Where should Harness install LLM entrypoints?

Select one or more targets using numbers or names, separated by commas.

  1) codex      Codex skill
  2) claude     Claude Code slash command
  3) gemini     Gemini global context
  4) opencode   OpenCode global instructions
  5) none       Runtime and CLI only
  6) manual     Runtime, CLI, and manual setup instructions

Examples:
  1,2,4
  codex,claude
  manual
  all
  none

Default: all
EOF
  printf "> " >&2
  read -r answer
  printf '%s\n' "${answer:-all}"
}

normalize_targets() {
  local raw normalized token out
  raw="$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]' | tr '; ' ',,' | tr '\n' ',')"
  raw="${raw:-all}"
  out=""

  if [ "$raw" = "all" ]; then
    printf '%s\n' "codex claude gemini opencode"
    return
  fi
  if [ "$raw" = "none" ] || [ "$raw" = "no" ]; then
    printf '\n'
    return
  fi

  IFS=',' read -r -a tokens <<< "$raw"
  for token in "${tokens[@]}"; do
    token="${token#"${token%%[![:space:]]*}"}"
    token="${token%"${token##*[![:space:]]}"}"
    case "$token" in
      "" )
        continue
        ;;
      1|codex )
        normalized="codex"
        ;;
      2|claude|claude-code|claudecode )
        normalized="claude"
        ;;
      3|gemini|gemini-cli|geminicli )
        normalized="gemini"
        ;;
      4|opencode|open-code )
        normalized="opencode"
        ;;
      5|none|no )
        printf '\n'
        return
        ;;
      6|manual|manual-install|manual-installation )
        normalized="manual"
        ;;
      all )
        printf '%s\n' "codex claude gemini opencode"
        return
        ;;
      * )
        echo "Unknown install target: $token" >&2
        exit 2
        ;;
    esac

    case " $out " in
      *" $normalized "*) ;;
      *) out="${out:+$out }$normalized" ;;
    esac
  done

  printf '%s\n' "$out"
}

write_managed_section() {
  local file tmp
  file="$1"
  tmp="$(mktemp)"
  cat > "$tmp"
  mkdir -p "$(dirname "$file")"
  python3 - "$file" "$tmp" <<'PY'
from pathlib import Path
import re
import sys

target = Path(sys.argv[1])
section = Path(sys.argv[2]).read_text(encoding="utf-8").strip() + "\n"
begin = "<!-- BEGIN HARNESS_GLOBAL -->"
end = "<!-- END HARNESS_GLOBAL -->"

current = target.read_text(encoding="utf-8") if target.exists() else ""
if begin in current and end in current:
    pattern = re.compile(re.escape(begin) + r".*?" + re.escape(end), re.S)
    updated = pattern.sub(section.strip(), current).rstrip() + "\n"
else:
    updated = current.rstrip()
    if updated:
        updated += "\n\n"
    updated += section

target.write_text(updated, encoding="utf-8")
PY
  rm -f "$tmp"
}

install_runtime() {
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

  if [ ! -f "$HARNESS_HOME/projects.json" ]; then
    printf '{}\n' > "$HARNESS_HOME/projects.json"
  fi

  if [ ! -f "$HARNESS_HOME/skills.json" ]; then
    printf '[]\n' > "$HARNESS_HOME/skills.json"
  fi
}

install_codex() {
  mkdir -p "$CODEX_HOME/skills"
  rm -rf "$CODEX_HOME/skills/harness"
  cp -R "$RUNTIME_DIR" "$CODEX_HOME/skills/harness"
  echo "Codex skill installed at $CODEX_HOME/skills/harness"
}

install_claude() {
  mkdir -p "$CLAUDE_HOME/commands"
  cp "$RUNTIME_DIR/commands/harness.md" "$CLAUDE_HOME/commands/harness.md"
  echo "Claude Code command installed at $CLAUDE_HOME/commands/harness.md"
}

install_gemini() {
  write_managed_section "$GEMINI_HOME/GEMINI.md" <<'EOF'
<!-- BEGIN HARNESS_GLOBAL -->
## Harness

Harness is the universal project workflow runtime. When the user asks to install,
apply, inspect, or use Harness in a project:

1. Prefer the `harness` CLI from PATH.
2. If PATH is missing it, use `$HOME/.local/bin/harness`.
3. If the project is not specified, ask for a local path, Git URL, or `owner/repo`.
4. Run `harness inspect --project <project> --task "<task>"` before applying.
5. Run `harness run --project <project> --task "<task>"` when the user wants the project prepared.
6. Treat `HARNESS.md` and `.harness/ENTRYPOINT.md` in the target project as the source of truth.
7. Do not skip human checkpoints, TDD evidence, SDD approval, or the final audit verdict.
<!-- END HARNESS_GLOBAL -->
EOF
  echo "Gemini global context updated at $GEMINI_HOME/GEMINI.md"
}

install_opencode() {
  write_managed_section "$OPENCODE_HOME/AGENTS.md" <<'EOF'
<!-- BEGIN HARNESS_GLOBAL -->
## Harness

Harness is the universal project workflow runtime. When the user asks to install,
apply, inspect, or use Harness in a project:

1. Prefer the `harness` CLI from PATH.
2. If PATH is missing it, use `$HOME/.local/bin/harness`.
3. If the project is not specified, ask for a local path, Git URL, or `owner/repo`.
4. Run `harness inspect --project <project> --task "<task>"` before applying.
5. Run `harness run --project <project> --task "<task>"` when the user wants the project prepared.
6. Treat `HARNESS.md` and `.harness/ENTRYPOINT.md` in the target project as the source of truth.
7. Do not skip human checkpoints, TDD evidence, SDD approval, or the final audit verdict.
<!-- END HARNESS_GLOBAL -->
EOF
  echo "OpenCode global instructions updated at $OPENCODE_HOME/AGENTS.md"
}

print_manual_instructions() {
  cat <<EOF

Manual Harness setup for any LLM
================================

Harness runtime is installed at:
  $RUNTIME_DIR

Harness CLI is installed at:
  $BIN_DIR/harness

If $BIN_DIR is in PATH, use:
  harness inspect --project <path|url|owner/repo> --task "<task>"
  harness run --project <path|url|owner/repo> --task "<task>" --dry-run
  harness run --project <path|url|owner/repo> --task "<task>"

If it is not in PATH, use:
  $BIN_DIR/harness inspect --project <path|url|owner/repo> --task "<task>"

Prompt to paste into any LLM:
  Use the Harness CLI for this project.
  First run:
  harness inspect --project <path|url|owner/repo> --task "<task>"
  Then run a dry-run:
  harness run --project <path|url|owner/repo> --task "<task>" --dry-run
  If the dry-run is correct, apply it:
  harness run --project <path|url|owner/repo> --task "<task>"
  After Harness is applied, read HARNESS.md and .harness/ENTRYPOINT.md.

EOF
}

if [ -z "$TARGETS_RAW" ]; then
  if [ -t 0 ]; then
    TARGETS_RAW="$(prompt_targets)"
  else
    echo "No interactive terminal detected; installing all LLM entrypoints." >&2
    echo "Use --targets none or --targets codex,claude,gemini,opencode to choose explicitly." >&2
    TARGETS_RAW="all"
  fi
fi

TARGETS="$(normalize_targets "$TARGETS_RAW")"

echo "Installing Harness runtime..."
install_runtime

ENTRYPOINT_TARGETS=""
MANUAL_REQUESTED=0
add_entrypoint_target() {
  ENTRYPOINT_TARGETS="${ENTRYPOINT_TARGETS:+$ENTRYPOINT_TARGETS }$1"
}

for target in $TARGETS; do
  case "$target" in
    codex) install_codex; add_entrypoint_target codex ;;
    claude) install_claude; add_entrypoint_target claude ;;
    gemini) install_gemini; add_entrypoint_target gemini ;;
    opencode) install_opencode; add_entrypoint_target opencode ;;
    manual) MANUAL_REQUESTED=1; print_manual_instructions ;;
  esac
done

echo "Harness installed at $RUNTIME_DIR"
echo "CLI installed at $BIN_DIR/harness"
if [ -n "$ENTRYPOINT_TARGETS" ]; then
  echo "Installed LLM entrypoints: $ENTRYPOINT_TARGETS"
else
  echo "Installed LLM entrypoints: none"
fi
if [ "$MANUAL_REQUESTED" -eq 1 ]; then
  echo "Manual setup instructions printed."
fi
echo "Add $BIN_DIR to PATH if needed."
