#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cmd="${1:-}"
if [[ -z "$cmd" ]]; then
  python3 "$SCRIPT_DIR/ms.py" --help
  exit 1
fi

if [[ "$cmd" == "functional-case" ]]; then
  action="${2:-}"
  case "$action" in
    generate)
      [[ $# -eq 5 ]] || { echo "用法: ms functional-case generate <projectId> <moduleId> <requirement-file>" >&2; exit 1; }
      exec python3 "$SCRIPT_DIR/ms_generate.py" functional-cases "$3" "$4" "$5"
      ;;
    batch-create)
      [[ $# -eq 3 ]] || { echo "用法: ms functional-case batch-create <json-file>" >&2; exit 1; }
      exec python3 "$SCRIPT_DIR/ms_batch.py" functional-cases "$3"
      ;;
    generate-create)
      [[ $# -eq 5 ]] || { echo "用法: ms functional-case generate-create <projectId> <moduleId> <requirement-file>" >&2; exit 1; }
      tmp_json="$(mktemp)"
      python3 "$SCRIPT_DIR/ms_generate.py" functional-cases "$3" "$4" "$5" > "$tmp_json"
      python3 "$SCRIPT_DIR/ms_batch.py" functional-cases "$tmp_json"
      rm -f "$tmp_json"
      exit 0
      ;;
  esac
fi

if [[ "$cmd" == "api" ]]; then
  action="${2:-}"
  case "$action" in
    import-generate)
      [[ $# -eq 5 ]] || { echo "用法: ms api import-generate <projectId> <moduleId> <openapi-file-or-url>" >&2; exit 1; }
      exec python3 "$SCRIPT_DIR/ms_generate.py" api-import "$3" "$4" "$5"
      ;;
    batch-create)
      [[ $# -eq 3 ]] || { echo "用法: ms api batch-create <json-file>" >&2; exit 1; }
      exec python3 "$SCRIPT_DIR/ms_batch.py" api-import "$3"
      ;;
    import-create)
      [[ $# -eq 5 ]] || { echo "用法: ms api import-create <projectId> <moduleId> <openapi-file-or-url>" >&2; exit 1; }
      tmp_json="$(mktemp)"
      python3 "$SCRIPT_DIR/ms_generate.py" api-import "$3" "$4" "$5" > "$tmp_json"
      python3 "$SCRIPT_DIR/ms_batch.py" api-import "$tmp_json"
      rm -f "$tmp_json"
      exit 0
      ;;
  esac
fi

exec python3 "$SCRIPT_DIR/ms.py" "$@"
