import sys
from pathlib import Path

# Make the engine importable as `corpus_pass` from any test.
SCRIPTS = Path(__file__).resolve().parent.parent / "plugins" / "content-brain" / "scripts"
sys.path.insert(0, str(SCRIPTS))
