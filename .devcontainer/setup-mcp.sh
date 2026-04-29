#!/bin/bash
# Gemini MCP 서버 연결 (Codespace 최초 생성 시 자동 실행)

if [ -z "$GEMINI_API_KEY" ]; then
  echo "⚠️  GEMINI_API_KEY 없음 — MCP 설정 건너뜀"
  echo "   → GitHub Codespace Secrets에 GEMINI_API_KEY를 추가 후 재시작하세요"
  exit 0
fi

echo "🔗 Gemini MCP 서버 연결 중..."

claude mcp add gemini-pro \
  --command "npx" \
  --args "-y,@yuhuangou/mcp-gemini-pro" \
  --env "GEMINI_API_KEY=$GEMINI_API_KEY" \
  2>/dev/null || echo "⚠️  MCP 자동 연결 실패 — 아래 명령어를 터미널에서 수동으로 실행하세요:"

echo ""
echo "  claude mcp add gemini-pro \\"
echo "    --command npx \\"
echo "    --args \"-y,@yuhuangou/mcp-gemini-pro\" \\"
echo "    --env GEMINI_API_KEY=\$GEMINI_API_KEY"
