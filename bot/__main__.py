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
    args = [a for a in sys.argv[2:] if a != "--replace"]
    if "--replace" in sys.argv:
        st["bgm_favs"] = []  # 이 곡만 쓰기
    pipeline.handle_bgm_command(st, "/bgmadd " + " ".join(args))
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
elif cmd == "bgm-get":  # 즐겨찾기 배경음악 받기 / calm: 잔잔한 연주곡 후보 받기 (확인용)
    from pathlib import Path
    from . import music
    if len(sys.argv) > 2 and sys.argv[2] == "calm":
        for t in music.calm_candidates()[:3]:
            print(music.download(t, Path(".")))
    elif len(sys.argv) > 2 and sys.argv[2].startswith("tag:"):  # 예: tag:epic → 해당 장르 연주곡 후보 3개
        for t in music.search(sys.argv[2][4:], n=3):
            print(music.download(t, Path(".")))
    else:
        f, credit = music.pick(Path("."))
        print(f, credit)
elif cmd == "shorts-upload":  # 완성 영상 올리기: python -m bot shorts-upload 영상.mp4 plan.json "음악 출처"
    from . import shorts
    shorts.upload_file(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else "")
elif cmd == "youtube-connect":  # Upload-Post 에 유튜브 연결 링크를 만들어 텔레그램으로만 보냄 (로그에 남기지 않음)
    import requests
    from . import config
    r = requests.post("https://api.upload-post.com/api/uploadposts/users/generate-jwt", timeout=30,
                      headers={"Authorization": f"Apikey {config.UPLOAD_POST_API_KEY}"},
                      json={"username": config.UPLOAD_POST_USER, "platforms": ["youtube"]})
    ok = r.ok and r.json().get("access_url")
    print("연결 링크 생성:", "성공" if ok else f"실패 HTTP {r.status_code}")
    st = pipeline.load_state()
    if ok:
        pipeline.notify(st, "🔗 유튜브 연결 링크 (48시간 유효)\n아래 링크를 눌러 숏츠를 올릴 유튜브 채널로 로그인·허용해주세요.\n"
                            + r.json()["access_url"])
elif cmd == "cc-find":  # CC 영상 후보 찾기: python -m bot cc-find "검색어1" "검색어2" ...
    from pathlib import Path
    from . import ccvideo
    ccvideo.find_cli(sys.argv[2:], Path("cc_out"))
elif cmd == "shorts-due":  # 워크플로에서 숏츠를 만들 차례인지 확인 (0=만들기)
    from . import shorts
    sys.exit(0 if shorts.due(pipeline.load_state()) else 1)
else:
    print("usage: python -m bot [tick|build]")
    sys.exit(1)
