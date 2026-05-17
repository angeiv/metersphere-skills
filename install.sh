#!/bin/bash
set -euo pipefail

TARGET_DIR="${METERSPHERE_SKILL_TARGET_DIR:-$HOME/.codex/skills/metersphere}"
TARGET_PARENT="$(dirname "$TARGET_DIR")"
SRC_DIR="$(cd "$(dirname "$0")" && pwd)/skills"
TEMP_BASE_DIR="/tmp"
TMP_DIR=""
BACKUP_DIR=""
BACKUP_ROOT=""

cleanup() {
  local exit_code=$?

  if [[ -n "$TMP_DIR" && -d "$TMP_DIR" ]]; then
    rm -rf "$TMP_DIR"
  fi

  if [[ $exit_code -ne 0 && -n "$BACKUP_DIR" && -d "$BACKUP_DIR" && ! -e "$TARGET_DIR" ]]; then
    mv "$BACKUP_DIR" "$TARGET_DIR"
    BACKUP_DIR=""
  fi

  if [[ $exit_code -ne 0 && -n "$BACKUP_ROOT" && -d "$BACKUP_ROOT" ]]; then
    rm -rf "$BACKUP_ROOT"
  fi

  return "$exit_code"
}

trap cleanup EXIT

mkdir -p "$TARGET_PARENT"
TMP_DIR="$(mktemp -d "$TARGET_PARENT/.metersphere-install.XXXXXX")"
cp -R "$SRC_DIR"/. "$TMP_DIR"

if [[ -f "$TARGET_DIR/.env" && ! -f "$TMP_DIR/.env" ]]; then
  cp "$TARGET_DIR/.env" "$TMP_DIR/.env"
fi

if [[ -e "$TARGET_DIR" ]]; then
  BACKUP_ROOT="$(mktemp -d "$TEMP_BASE_DIR/metersphere-backup.XXXXXX")"
  BACKUP_DIR="$BACKUP_ROOT/$(basename "$TARGET_DIR")"
  mv "$TARGET_DIR" "$BACKUP_DIR"
fi

mv "$TMP_DIR" "$TARGET_DIR"
TMP_DIR=""

echo "已安装到: $TARGET_DIR"
if [[ -n "$BACKUP_ROOT" && -d "$BACKUP_ROOT" ]]; then
  echo "原安装内容已备份到: $BACKUP_ROOT"
  echo "如确认无需回滚，可稍后手动删除该临时备份目录。"
fi
if [[ -f "$TARGET_DIR/.env" ]]; then
  echo "已保留现有配置: $TARGET_DIR/.env"
else
  echo "下一步: 复制 .env.example 到 $TARGET_DIR/.env 并填写 MeterSphere 2.x 地址、AK/SK、workspace/project 配置。"
fi
