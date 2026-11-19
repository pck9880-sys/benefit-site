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
else:
    print("usage: python -m bot [tick|build]")
    sys.exit(1)
