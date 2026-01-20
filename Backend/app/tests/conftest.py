import os
import sys

# Asegura que la raíz del proyecto esté en sys.path cuando se ejecuta pytest desde app/tests
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
