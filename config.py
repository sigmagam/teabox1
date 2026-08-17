"""
config.py — Configuration for the standalone TeraBox API.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / '.env')

# ── Server ──────────────────────────────────────────────────────────
PORT = int(os.getenv('PORT', 5001))
HOST = os.getenv('HOST', '0.0.0.0')
DEBUG = os.getenv('DEBUG', 'false').lower() == 'true'

# ── CORS ────────────────────────────────────────────────────────────
CORS_HEADERS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
}

# ── API Branding ────────────────────────────────────────────────────
API_AUTHOR = os.getenv('API_AUTHOR', 'AccelPedia X シ')
API_CONTACT = os.getenv('API_CONTACT', 'https://t.me/todict')

# ── TeraBox ─────────────────────────────────────────────────────────
# Empty string / "self" => stream downloads through this server's own
# /terabox/download endpoint (see routes/terabox.py) instead of an
# external Cloudflare Worker.
CORS_DOWNLOAD_BASE = os.getenv('TERABOX_CORS_DOWNLOAD_BASE', 'self')
TERABOX_DOWNLOAD_TOKEN_TTL_SECONDS = 60 * 60
TERABOX_DOWNLOAD_LINK_BATCH_SIZE = 5
TERABOX_SCAN_TIMEOUT_SECONDS = int(os.getenv('TERABOX_SCAN_TIMEOUT_SECONDS', '25'))
