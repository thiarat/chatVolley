import sys
import os

# Add project root to sys.path so Vercel can find main.py and chatpdf_pipeline.py
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app  # noqa: F401 — Vercel entry point
