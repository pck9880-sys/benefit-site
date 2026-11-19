import sys

from . import pipeline, site

cmd = sys.argv[1] if len(sys.argv) > 1 else "tick"
if cmd == "tick":
    pipeline.tick()
elif cmd == "build":
    site.build()
elif cmd == "indexnow":
    from . import indexnow
    indexnow.run()
elif cmd == "redirect":
    from . import config
    site.build_redirect(config.SITE_URL, config.ROOT / "_ghpages")
elif cmd == "shorts":
    from . import shorts
    shorts.run(force="--force" in sys.argv)
elif cmd == "typecast-check":  # 타입캐스트 키·목소리 확인 → 텔레그램으로 1번 알림
    from . import config, typecast
    st = pipeline.load_state()
    msg = typecast.check()
    print(msg)
    if config.TYPECAST_API_KEY and st.get("typecast_reported") != msg:
        pipeline.notify(st, "🎙 " + msg)
        st["typecast_reported"] = msg
        pipeline.save_json(config.STATE_FILE, st)
elif cmd == "shorts-due":  # 워크플로에서 숏츠를 만들 차례인지 확인 (0=만들기)
    from . import shorts
    sys.exit(0 if shorts.due(pipeline.load_state()) else 1)
else:
    print("usage: python -m bot [tick|build]")
    sys.exit(1)
