import os
import sys
import types

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, 'backend'))
sys.path.insert(0, os.path.join(ROOT, 'reference'))

# reference/app.py imports streamlit at the top; a stub is enough to load
# its functions without running the UI.
sys.modules.setdefault('streamlit', types.ModuleType('streamlit'))
