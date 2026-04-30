#!/usr/bin/env python3
"""Gemini 질문 CLI — 스트리밍 + 검색 자동 fallback."""

import os
import sys

from google import genai
from google.genai import types

API_KEY = os.environ.get("GEMINI_API_KEY")
MODEL = "models/gemini-2.5-flash"


def ask(prompt: str, use_search: bool = True) -> None:
    client = genai.Client(api_key=API_KEY)
    config = None

    if use_search:
        config = types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())]
        )

    try:
        for chunk in client.models.generate_content_stream(
            model=MODEL,
            contents=prompt,
            config=config,
        ):
            if chunk.text:
                print(chunk.text, end="", flush=True)
        print()
    except Exception as e:
        if use_search and "PERMISSION_DENIED" in str(e):
            # Search 권한 없을 때 일반 모드로 재시도
            ask(prompt, use_search=False)
        else:
            print(f"\n⚠️  오류: {e}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    if not API_KEY:
        print("⚠️  GEMINI_API_KEY 환경변수가 없습니다.", file=sys.stderr)
        sys.exit(1)
    if len(sys.argv) < 2:
        print("사용법: ask_gemini.py \"질문\"", file=sys.stderr)
        sys.exit(1)

    ask(" ".join(sys.argv[1:]))
