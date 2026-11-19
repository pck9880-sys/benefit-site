"""텔레그램 /post 요청 테스트. 실행: MOCK=1 python -m tests.test_request"""
import shutil

from bot import config, pipeline, telegram

sent, queue = [], []
telegram.enabled = lambda: True
telegram.send = lambda chat, text, buttons=None, html=False: sent.append(text) or len(sent)
telegram.edit = lambda *a: None
telegram.answer_callback = lambda *a: None
telegram.get_updates = lambda offset: [u for u in queue if u["update_id"] >= offset]
shutil.rmtree(config.DATA_DIR, ignore_errors=True)
config.GENERATE_EVERY_HOURS = 24 * 365  # 정기 생성은 막고 요청만 확인
config.REQUIRE_APPROVAL = False

msg = lambda i, t: {"update_id": i, "message": {"chat": {"id": 7, "type": "private"}, "text": t}}
queue[:] = [msg(1, "안녕"), msg(2, "/post 2")]
st = pipeline.load_state(); st["last_generate_hour"] = None
pipeline.save_json(config.STATE_FILE, st)
pipeline.tick()
n = len(list(config.POSTS_DIR.glob("*.json")))
assert n >= 2, n
queue[:] = [msg(3, "/post 청년월세")]
pipeline.tick()
assert any("청년월세" in m or "요청하신 글" in m or "찾지 못했어요" in m for m in sent), sent[-2:]
print("OK posts", len(list(config.POSTS_DIR.glob("*.json"))), "| 마지막 메시지:", sent[-1][:80].replace("\n", " "))
