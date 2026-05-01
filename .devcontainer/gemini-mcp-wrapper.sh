#!/bin/bash
# API 키를 환경변수에서 읽어 gemini-mcp 실행 (두 이름 모두 지원)
KEY="${VIVE_GEMINI_API_KEY:-$GEMINI_API_KEY}"
exec npx -y gemini-mcp --api-key "$KEY"
