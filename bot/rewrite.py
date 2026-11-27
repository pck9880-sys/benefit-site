"""기존 글을 현재 작성 규칙(writer.SYSTEM)으로 다시 쓴다. 주소·게시일은 유지.
사용: python -m bot.rewrite 105100000001,132000000006   또는   python -m bot.rewrite all 20"""
import sys

from . import config, gov24, writer
from .pipeline import load_json, save_json, now


def rewrite(sid):
    path = config.POSTS_DIR / f"{sid}.json"
    d = load_json(path, {})
    detail = gov24.service_detail(sid)
    svc = {"서비스ID": sid, "서비스명": d["source"].get("name"), **{k: v for k, v in detail.items() if v}}
    article, cost = writer.write_article(svc, detail)
    d["article"] = article.model_dump()
    d["rewritten_at"] = now().isoformat()
    save_json(path, d)
    print(f"[rewrite] {sid} 완료 (${cost:.3f})")
    return cost


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else ""
    if arg == "all":
        lim = int(sys.argv[2]) if len(sys.argv) > 2 else 20
        ids = [p.stem for p in sorted(config.POSTS_DIR.glob("*.json")) if not load_json(p, {}).get("rewritten_at")][:lim]
    else:
        ids = [x.strip() for x in arg.split(",") if x.strip()]
    tot = 0.0
    for sid in ids:
        try:
            tot += rewrite(sid)
        except Exception as e:
            print(f"[rewrite] {sid} 실패: {e}")
    print(f"[rewrite] {len(ids)}개 처리, 비용 ${tot:.2f}")
