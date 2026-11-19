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
elif cmd == "shorts-due":  # 워크플로에서 숏츠를 만들 차례인지 확인 (0=만들기)
    from . import shorts
    sys.exit(0 if shorts.due(pipeline.load_state()) else 1)
else:
    print("usage: python -m bot [tick|build]")
    sys.exit(1)
