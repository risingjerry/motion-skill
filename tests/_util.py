import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "scripts")
for p in (SCRIPTS, os.path.join(SCRIPTS, "audio"), os.path.join(SCRIPTS, "blender")):
    if p not in sys.path:
        sys.path.insert(0, p)
