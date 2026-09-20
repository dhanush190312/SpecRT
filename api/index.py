"""
Vercel Serverless Function Entrypoint for SpecRt
"""
import sys
from pathlib import Path

# Ensure root workspace directory is at front of sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from web_server import app
