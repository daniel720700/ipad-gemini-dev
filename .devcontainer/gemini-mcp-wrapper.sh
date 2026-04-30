#!/bin/bash
# API 키를 커맨드 인수 대신 환경변수에서 읽어 gemini-mcp 실행
# → claude mcp list 에 키가 노출되지 않음
exec npx -y gemini-mcp --api-key "$GEMINI_API_KEY"
