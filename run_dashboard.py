"""SA Dashboard 실행 진입점."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src", "sa_dashboard"))

from server import create_app

if __name__ == "__main__":
    port = int(os.environ.get("SA_PORT", 5050))
    print(f"✅ SA Dashboard → http://localhost:{port}")
    print("   브라우저에서 Seeking Alpha 이메일/비밀번호로 로그인하세요.")
    create_app().run(host="0.0.0.0", port=port, debug=False)
