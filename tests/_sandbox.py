"""테스트가 실제 data/ 폴더를 지우지 않도록 임시 폴더로 바꿔치기."""
import tempfile
from pathlib import Path

from bot import config

tmp = Path(tempfile.mkdtemp(prefix="bot-test-"))
config.DATA_DIR = tmp / "data"
config.DRAFTS_DIR = config.DATA_DIR / "drafts"
config.POSTS_DIR = config.DATA_DIR / "posts"
config.STATE_FILE = config.DATA_DIR / "state.json"
config.OUT_DIR = tmp / "_site"
