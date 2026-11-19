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
CF_PAGES_PROJECT = _env("CF_PAGES_PROJECT", "jiwon-hyetaek")
if _env("CLOUDFLARE_API_TOKEN"):  # Cloudflare Pages 를 쓰면 그 주소가 기본
    _default_url = f"https://{CF_PAGES_PROJECT}.pages.dev"
SITE_URL = _env("SITE_URL", _default_url).rstrip("/")
SITE_DESCRIPTION = _env(
    "SITE_DESCRIPTION",
    "내가 받을 수 있는 정부 지원금·혜택을 쉽게 정리합니다. 지원 대상, 금액, 신청 방법까지 한눈에.",
)
CLAUDE_MODEL = _env("CLAUDE_MODEL", "claude-sonnet-5-5")
POSTS_PER_DAY = int(_env("POSTS_PER_DAY", "5"))  # SCHEDULE=daily 일 때 하루 생성 수
SCHEDULE = _env("SCHEDULE", "hourly")  # hourly: 매시간 POSTS_PER_HOUR 개 / daily: 하루 1번 POSTS_PER_DAY 개
POSTS_PER_HOUR = int(_env("POSTS_PER_HOUR", "2"))  # 한 번 생성할 때 만드는 글 수
GENERATE_EVERY_HOURS = int(_env("GENERATE_EVERY_HOURS", "4"))  # 몇 시간마다 생성할지
SLOWDOWN_AFTER_POSTS = int(_env("SLOWDOWN_AFTER_POSTS", "150"))  # 글이 이만큼 쌓이면 한 번에 1개로 줄임
REQUIRE_APPROVAL = _env("REQUIRE_APPROVAL", "0") == "1"  # 0이면 승인 없이 바로 게시
GENERATE_HOUR_KST = int(_env("GENERATE_HOUR_KST", "7"))
AUTO_APPROVE_HOURS = float(_env("AUTO_APPROVE_HOURS", "0.0833"))  # 5분  # 0이면 승인 없이는 게시 안 함
MAX_MONTHLY_USD = float(_env("MAX_MONTHLY_USD", "80"))  # 월 API 비용 상한
CONTACT_EMAIL = _env("CONTACT_EMAIL", "info17476@naver.com")  # 문의 페이지에 표시 (스팸 수집기 방지용으로 나눠서 출력)
ADSENSE_CLIENT = _env("ADSENSE_CLIENT")  # 예: ca-pub-1234567890123456
GOOGLE_SITE_VERIFICATION = _env("GOOGLE_SITE_VERIFICATION")
NAVER_SITE_VERIFICATION = _env("NAVER_SITE_VERIFICATION")
BLOG_PER_DAY = int(_env("BLOG_PER_DAY", "2"))  # 하루에 보낼 네이버 블로그용 글 수 (0이면 끔)
CONTESTS_PER_DAY = int(_env("CONTESTS_PER_DAY", "3"))  # 하루에 출품안 만들 공모전 수
CONTEST_HOUR_KST = int(_env("CONTEST_HOUR_KST", "8"))
SHORTS_PER_DAY = int(_env("SHORTS_PER_DAY", "1"))  # 하루 숏츠 수 (0이면 끔)
SHORTS_HOUR_KST = int(_env("SHORTS_HOUR_KST", "12"))  # 이 시각 이후 첫 실행 때 제작
SHORTS_VOICE = _env("SHORTS_VOICE", "ko-KR-InJoonNeural")  # 무료 음성 (여성: ko-KR-SunHiNeural)
SHORTS_PRIVACY = _env("SHORTS_PRIVACY", "public")  # public / unlisted / private
SHORTS_KEEP = _env("SHORTS_KEEP") == "1"  # 테스트용: 영상 파일을 남김
UPLOAD_POST_API_KEY = _env("UPLOAD_POST_API_KEY")  # Upload-Post (유튜브 자동 업로드, 무료 월 10개)
UPLOAD_POST_USER = _env("UPLOAD_POST_USER")  # Upload-Post 프로필 이름
SHORTS_CHANNEL = _env("SHORTS_CHANNEL", "")  # 영상 맨 위에 작게 표시할 채널 이름 (예: @내채널)
SHORTS_BGM_VOLUME = float(_env("SHORTS_BGM_VOLUME", "0.12"))  # (예전 설정, 미사용)
SHORTS_BGM = _env("SHORTS_BGM", "1") == "1"  # 배경음악 사용 (즐겨찾기 곡만: Born Free - Pokki DJ, 연주곡)
SHORTS_BGM_LUFS = float(_env("SHORTS_BGM_LUFS", "-33"))  # 배경음악 크기 (목소리 -14 기준, 낮을수록 작게)
SHORTS_SFX = _env("SHORTS_SFX", "0") == "1"  # 효과음 사용 여부 (현재 끔)
SHORTS_SFX_VOLUME = float(_env("SHORTS_SFX_VOLUME", "0.35"))  # 효과음 크기 (assets/sfx)
YOUTUBE_API_KEY = _env("YOUTUBE_API_KEY")  # 인기 쇼츠 분석용 (없으면 구글 검색어만 사용)
OPENAI_API_KEY = _env("OPENAI_API_KEY")  # GPT 이미지 (있으면 최우선 사용)
OPENAI_IMAGE_MODEL = _env("OPENAI_IMAGE_MODEL", "gpt-image-1.5")
SHORTS_PHOTOS = _env("SHORTS_PHOTOS", "0") == "1"  # 무료 실사 사진 검색 (끔: 장면은 GPT 이미지만)
OPENAI_IMAGE_QUALITY = _env("OPENAI_IMAGE_QUALITY", "medium")  # low / medium / high
HIGGSFIELD_KEY = _env("HIGGSFIELD_KEY")  # 힉스필드 API "키ID:시크릿" (없으면 글자 카드 화면)
HIGGSFIELD_MODEL = _env("HIGGSFIELD_MODEL", "kling-video/v3.0-turbo/text-to-video")
HIGGSFIELD_CLIPS = int(_env("HIGGSFIELD_CLIPS", "1"))  # 숏츠 1개당 AI 영상 수 (첫 장면에만 사용, 0이면 사진만)
HIGGSFIELD_IMAGE_MODEL = _env("HIGGSFIELD_IMAGE_MODEL", "higgsfield-ai/soul/standard")
JAMENDO_CLIENT_ID = _env("JAMENDO_CLIENT_ID")  # 무료 배경음악 API (없으면 assets/bgm)
PEXELS_API_KEY = _env("PEXELS_API_KEY")  # 무료 실사 사진 (없으면 Openverse CC 사진)
TYPECAST_API_KEY = _env("TYPECAST_API_KEY")  # 타입캐스트 음성 (없으면 무료 음성)
TYPECAST_VOICE_ID = _env("TYPECAST_VOICE_ID")  # 타입캐스트 voice_id (비우면 이름으로 검색)
TYPECAST_VOICE_NAME = _env("TYPECAST_VOICE_NAME", "용식")
SHORTS_VOICE_CHAR = _env("SHORTS_VOICE_CHAR", "용식")  # 숏츠 기본 목소리 (용식·박창수: 다들 ~해요잉~ / 태우: 다들 ~하자!)
TYPECAST_ONLY = _env("TYPECAST_ONLY", "1") == "1"  # 1이면 항상 타입캐스트(박창수)만 — 실패하면 무료 음성으로 바꾸지 않고 중단
TYPECAST_CREDIT = _env("TYPECAST_CREDIT", "0") == "1"  # 무료 플랜일 때만 출처 표기 필요 (베이직 유료라 끔)
VOICE_FILE_TEMPO = float(_env("VOICE_FILE_TEMPO", "1.4"))  # 직접 만든 음성 파일(1.0배속)을 이 배속으로
TTS_WORKERS = int(_env("TTS_WORKERS", "2"))  # 음성 동시 생성 수 (타입캐스트 무료 플랜 최대 2)
TYPECAST_TEMPO = float(_env("TYPECAST_TEMPO", "1.0"))  # 목소리 배속 (1.0 = 원래 속도)
HIGGSFIELD_SECONDS = int(_env("HIGGSFIELD_SECONDS", "5"))
MOCK = _env("MOCK") == "1"  # 테스트용: 외부 API 호출 없이 동작

# 모델별 단가 (USD / 1M 토큰) - 비용 추적용
PRICES = {
    "claude-haiku-5-5": (0.10, 0.50),
    "claude-sonnet-5-5": (2.00, 10.00),
    "claude-opus-5-5": (4.00, 20.00),
}
