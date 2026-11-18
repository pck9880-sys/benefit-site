import sys

from . import pipeline, site

cmd = sys.argv[1] if len(sys.argv) > 1 else "tick"
if cmd == "tick":
    pipeline.tick()
elif cmd == "build":
    site.build()
else:
    print("usage: python -m bot [tick|build]")
    sys.exit(1)
