# CLAUDE.md — Vibe Coding 트리플 스택 규칙

## 역할 분담

| 에이전트 | 역할 |
|---------|------|
| **Gemini Pro** | 아키텍처 설계, 대용량 컨텍스트 분석, 코드 리뷰 |
| **Claude (나)** | 실제 코드 구현, 터미널 실행, 파일 생성/수정 |

## 워크플로우

```
[iPad Gemini 앱]
    ↓ 설계도 작성
ARCHITECTURE.md
    ↓ claude "ARCHITECTURE.md 읽고 구현해줘"
[Claude 구현]
    ↓ 완료 후 리뷰 요청 (MCP)
[Gemini 리뷰]
```

## Python 코딩 규칙

- 타입 힌트 필수: `def func(x: int) -> str:`
- Black 포매터 (line-length=88)
- docstring: Google 스타일
- 테스트: pytest, 커버리지 80% 이상
- 가상환경: `.venv/`
- 패키지 관리: `requirements.txt` 유지

## 파일 구조

```
project/
├── src/             # 소스 코드
├── tests/           # pytest 테스트
├── docs/            # 문서
├── ARCHITECTURE.md  # Gemini 설계도 (Claude는 수정 금지)
├── CLAUDE.md        # 이 파일
└── requirements.txt
```

## 금지 사항

- `ARCHITECTURE.md` 직접 수정 금지 — Gemini 담당
- `.env` 파일 커밋 금지
- `node_modules/`, `__pycache__/`, `.venv/` 수정 금지

## Gemini MCP 사용법

```bash
# Gemini에게 코드 리뷰 요청
claude "MCP로 Gemini에게 현재 src/ 코드 리뷰 요청해줘"

# Gemini에게 리팩토링 방안 요청
claude "Gemini한테 이 코드 최적화 방법 물어봐줘"
```
