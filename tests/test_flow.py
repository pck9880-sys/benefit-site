"""텔레그램 승인 흐름 테스트 (네트워크 없이 가짜 텔레그램 사용). 실행: MOCK=1 python -m tests.test_flow"""
import shutil
from datetime import timedelta

from bot import config, pipeline, telegram

sent, edits, queue = [], [], []
telegram.enabled = lambda: True
telegram.send = lambda chat, text, buttons=None, html=False: sent.append((chat, text, buttons)) or len(sent)
telegram.edit = lambda chat, mid, text: edits.append((mid, text))
telegram.answer_callback = lambda *a: None
telegram.get_updates = lambda offset: [u for u in queue if u["update_id"] >= offset]

shutil.rmtree(config.DATA_DIR, ignore_errors=True)
config.POSTS_PER_DAY = 3
config.SCHEDULE = "daily"
config.REQUIRE_APPROVAL = True
config.AUTO_APPROVE_HOURS = 12  # 테스트는 12시간 기준

# 1) 첫 메시지 → 주인 등록, 아직 7시 이전이면 생성 안 될 수 있으니 /now 사용
queue[:] = [{"update_id": 1, "message": {"chat": {"id": 42, "type": "private"}, "text": "안녕"}},
            {"update_id": 2, "message": {"chat": {"id": 42, "type": "private"}, "text": "/now"}}]
pipeline.tick()
st = pipeline.load_state()
assert st["owner_chat_id"] == 42, st
assert len(pipeline.drafts()) == 3, "초안 3개 생성"
ids = [p.stem for p in pipeline.drafts()]

# 2) 낯선 사람의 버튼은 무시, 주인 승인 1개 + 거절 1개
queue[:] = [{"update_id": 3, "callback_query": {"id": "a", "data": f"ok:{ids[0]}", "message": {"chat": {"id": 999}}}},
            {"update_id": 4, "callback_query": {"id": "b", "data": f"ok:{ids[0]}", "message": {"chat": {"id": 42}}}},
            {"update_id": 5, "callback_query": {"id": "c", "data": f"no:{ids[1]}", "message": {"chat": {"id": 42}}}}]
pipeline.tick()
assert (config.POSTS_DIR / f"{ids[0]}.json").exists()
assert not (config.POSTS_DIR / f"{ids[1]}.json").exists()
assert len(pipeline.drafts()) == 1

# 3) 12시간 지나면 남은 초안 자동 게시 (실행 시각과 무관하게: 새 글 생성은 막아둠)
config.GENERATE_HOUR_KST = 24
real_now = pipeline.now
pipeline.now = lambda: real_now() + timedelta(hours=13)
queue[:] = []
pipeline.tick()
assert (config.POSTS_DIR / f"{ids[2]}.json").exists() and not pipeline.drafts()
pipeline.now = real_now

# 4) /pause 후엔 생성 안 함
queue[:] = [{"update_id": 6, "message": {"chat": {"id": 42, "type": "private"}, "text": "/pause"}},
            {"update_id": 7, "message": {"chat": {"id": 42, "type": "private"}, "text": "/now"}}]
pipeline.tick()
assert not pipeline.drafts()
print("ALL OK — 메시지", len(sent), "개, 수정", len(edits), "개")
print("마지막 초안 메시지 예시:\n", [s for s in sent if s[2]][0][1])
