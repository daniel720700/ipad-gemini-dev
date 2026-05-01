#!/bin/bash
# Gemini MCP 서버 연결 (Codespace 생성/시작 시 자동 실행)

# VIVE_GEMINI_API_KEY 또는 GEMINI_API_KEY 중 설정된 것 사용
KEY="${VIVE_GEMINI_API_KEY:-$GEMINI_API_KEY}"

if [ -z "$KEY" ]; then
  echo "⚠️  Gemini API Key 없음 — MCP 설정 건너뜀"
  echo "   → GitHub Codespace Secrets에 VIVE_GEMINI_API_KEY를 추가 후 재시작하세요"
  exit 0
fi

WRAPPER="$(cd "$(dirname "$0")" && pwd)/gemini-mcp-wrapper.sh"
chmod +x "$WRAPPER"

claude mcp remove gemini-pro 2>/dev/null || true

claude mcp add gemini-pro \
  -e "VIVE_GEMINI_API_KEY=$KEY" \
  -e "GEMINI_API_KEY=$KEY" \
  -- bash "$WRAPPER"

if [ $? -eq 0 ]; then
  echo "✅ Gemini MCP 연결 완료"
else
  echo "⚠️  Gemini MCP 연결 실패"
fi
