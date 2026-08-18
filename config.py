"""
config.py — Configuration for the standalone TeraBox API.
Vercel-safe version.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# ── Server ──────────────────────────────────────────────────────────
PORT = int(os.getenv("PORT", "5001"))
HOST = os.getenv("HOST", "0.0.0.0")
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

# ── CORS ────────────────────────────────────────────────────────────
CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, X-API-Key",
}

# ── API Branding ────────────────────────────────────────────────────
API_AUTHOR = os.getenv("API_AUTHOR", "AccelPedia X シ")
API_CONTACT = os.getenv("API_CONTACT", "https://t.me/todict")

# ── Optional API keys ───────────────────────────────────────────────
# README says the API does not require a key. If VALID_API_KEYS is
# empty/unset, authentication is disabled. If you set a comma-separated
# list, requests must provide one of those keys.
VALID_API_KEYS = {
    key.strip()
    for key in os.getenv("VALID_API_KEYS", "").split(",")
    if key.strip()
}

# ── Optional static outbound proxy ─────────────────────────────────
# Leave empty to connect directly from Vercel.
STATIC_OUTBOUND_PROXY_URL = os.getenv("STATIC_OUTBOUND_PROXY_URL", "PRABOWO").strip()

# ── TeraBox ─────────────────────────────────────────────────────────
# "self" / empty means the API returns its own /terabox/dl proxy URL.
CORS_DOWNLOAD_BASE = os.getenv("TERABOX_CORS_DOWNLOAD_BASE", "self").strip() or "self"

TERABOX_DOWNLOAD_TOKEN_TTL_SECONDS = int(
    os.getenv("TERABOX_DOWNLOAD_TOKEN_TTL_SECONDS", "3600")
)
TERABOX_DOWNLOAD_LINK_BATCH_SIZE = int(
    os.getenv("TERABOX_DOWNLOAD_LINK_BATCH_SIZE", "5")
)
TERABOX_SCAN_TIMEOUT_SECONDS = int(
    os.getenv("TERABOX_SCAN_TIMEOUT_SECONDS", "45")
)
