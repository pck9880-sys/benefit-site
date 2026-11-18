"""모든 설정은 환경변수(GitHub Secrets / Variables)에서 읽습니다."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DRAFTS_DIR = DATA_DIR / "drafts"
POSTS_DIR = DATA_DIR / "posts"
STATE_FILE = DATA_DIR / "state.json"
OUT_DIR = ROOT / "_site"


def _env(name, default=""):
    v = os.environ.get(name, "")
    return v.strip() if v and v.strip() else default


# --- 비밀값 (GitHub Secrets) ---
ANTHROPIC_API_KEY = _env("ANTHROPIC_API_KEY")
DATA_GO_KR_KEY = _env("DATA_GO_KR_KEY")
TELEGRAM_BOT_TOKEN = _env("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = _env("TELEGRAM_CHAT_ID")  # 비워두면 봇에 처음 메시지 보낸 사람으로 자동 등록

# --- 일반 설정 (GitHub Variables) ---
SITE_NAME = _env("SITE_NAME", "정부혜택 한눈에")
_repo = os.environ.get("GITHUB_REPOSITORY", "")
_default_url = f"https://{_repo.split('/')[0]}.github.io/{_repo.split('/')[1]}" if "/" in _repo else "http://localhost:8000"
SITE_URL = _env("SITE_URL", _default_url).rstrip("/")
SITE_DESCRIPTION = _env(
    "SITE_DESCRIPTION",
    "내가 받을 수 있는 정부 지원금·혜택을 쉽게 정리합니다. 지원 대상, 금액, 신청 방법까지 한눈에.",
)
CLAUDE_MODEL = _env("CLAUDE_MODEL", "claude-haiku-5-5")
POSTS_PER_DAY = int(_env("POSTS_PER_DAY", "5"))
GENERATE_HOUR_KST = int(_env("GENERATE_HOUR_KST", "7"))
AUTO_APPROVE_HOURS = float(_env("AUTO_APPROVE_HOURS", "12"))  # 0이면 승인 없이는 게시 안 함
MAX_MONTHLY_USD = float(_env("MAX_MONTHLY_USD", "5"))  # 월 API 비용 상한
ADSENSE_CLIENT = _env("ADSENSE_CLIENT")  # 예: ca-pub-1234567890123456
GOOGLE_SITE_VERIFICATION = _env("GOOGLE_SITE_VERIFICATION")
NAVER_SITE_VERIFICATION = _env("NAVER_SITE_VERIFICATION")
MOCK = _env("MOCK") == "1"  # 테스트용: 외부 API 호출 없이 동작

# 모델별 단가 (USD / 1M 토큰) - 비용 추적용
PRICES = {
    "claude-haiku-5-5": (0.10, 0.50),
    "claude-sonnet-5-5": (2.00, 10.00),
    "claude-opus-5-5": (4.00, 20.00),
}
