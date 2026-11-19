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
elif cmd == "photos":  # 사진 검색 점검: python -m bot photos "검색어"
    import tempfile
    from pathlib import Path
    from . import photos
    q = sys.argv[2] if len(sys.argv) > 2 else "baseball stadium"
    print(photos.find(q, set(), Path(tempfile.mkdtemp()) / "t.jpg"))
elif cmd == "shorts-sample":  # 저장된 대본·이미지로 숏츠 렌더링 (틀 테스트): python -m bot shorts-sample 폴더
    from . import shorts
    shorts.render_sample(sys.argv[2])
elif cmd == "bgm-add":  # 배경음악 즐겨찾기 추가 (텔레그램 /bgmadd 와 같음): python -m bot bgm-add "곡 - 아티스트"
    from . import config
    st = pipeline.load_state()
    pipeline.handle_bgm_command(st, "/bgmadd " + " ".join(sys.argv[2:]))
    pipeline.save_json(config.STATE_FILE, st)
    print("favs:", st.get("bgm_favs"))
elif cmd == "typecast-test":  # 타입캐스트 음성 1문장만 실제로 만들어 보기 (차단 여부 확인)
    import tempfile
    from pathlib import Path
    from . import typecast
    try:
        f = typecast.tts("테스트 한 문장이야", Path(tempfile.mkdtemp()) / "t.mp3")
        print(f"✅ 타입캐스트 음성 정상 ({f.stat().st_size // 1024}KB)")
    except Exception as e:
        print("❌", str(e)[:600])
elif cmd == "shorts-due":  # 워크플로에서 숏츠를 만들 차례인지 확인 (0=만들기)
    from . import shorts
    sys.exit(0 if shorts.due(pipeline.load_state()) else 1)
else:
    print("usage: python -m bot [tick|build]")
    sys.exit(1)
