#!/bin/bash
set -e

echo "=== Vibe Coding 환경 셋업 시작 ==="

echo "▶ Python 패키지 설치..."
pip install --upgrade pip black isort pylint pytest pytest-cov ipykernel google-genai

echo "▶ npm 패키지 설치..."
npm install -g @anthropic-ai/claude-code @google/gemini-cli

echo "▶ git-lfs 설치..."
curl -fsSL https://packagecloud.io/install/repositories/github/git-lfs/script.deb.sh | sudo bash
sudo apt-get install -y git-lfs
git lfs install

echo "▶ Gemini MCP 연결..."
bash "$(dirname "$0")/setup-mcp.sh"

echo "▶ ttyd 설치..."
curl -fsSL https://github.com/tsl0922/ttyd/releases/download/1.7.7/ttyd.x86_64 -o /tmp/ttyd
chmod +x /tmp/ttyd
sudo mv /tmp/ttyd /usr/local/bin/ttyd

echo "=== 환경 셋업 완료 ==="
