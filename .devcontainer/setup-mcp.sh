#!/bin/bash
# Gemini MCP 서버 연결 (Codespace 생성 시 자동 실행)

if [ -z "$GEMINI_API_KEY" ]; then
  echo "⚠️  GEMINI_API_KEY 없음 — MCP 설정 건너뜀"
  echo "   → GitHub Codespace Secrets에 GEMINI_API_KEY를 추가 후 재시작하세요"
  exit 0
fi

# 기존 등록 제거 후 재등록
claude mcp remove gemini-pro 2>/dev/null || true

claude mcp add gemini-pro \
  -e "GEMINI_API_KEY=$GEMINI_API_KEY" \
  -- npx -y gemini-mcp --api-key "$GEMINI_API_KEY"

if [ $? -eq 0 ]; then
  echo "✅ Gemini MCP 연결 완료"
else
  echo "⚠️  Gemini MCP 연결 실패"
fi
