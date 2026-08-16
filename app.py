"""
app.py — Standalone TeraBox API (Flask)
Single-purpose API for TeraBox URL scraping & download link extraction.
No api_key required.
"""
import os
from pathlib import Path
from flask import Flask, jsonify
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / '.env')

app = Flask(__name__)
app.url_map.strict_slashes = False
app.wsgi_app = ProxyFix(
    app.wsgi_app,
    x_for=1, x_proto=1, x_host=1, x_prefix=1,
)
CORS(app, resources={r"/*": {"origins": "*"}})

from routes.terabox import terabox_bp, terabox_download
from routes.pages import pages_bp

app.register_blueprint(terabox_bp)
app.register_blueprint(pages_bp)

# Also expose the streaming download proxy at the top-level /dl path
# (in addition to /terabox/download), since deployments may reverse-proxy
# or generate links expecting /dl directly.
app.add_url_rule('/dl', 'dl_download', terabox_download, methods=['GET'])


# NOTE: '/' used to return this JSON status payload directly. The website
# frontend now owns '/' (see routes/pages.py -> templates/index.html), so
# the same payload has moved here to keep it reachable for anyone/anything
# that was hitting '/' for API status. Nothing about the resolver or
# download logic changed.
@app.route('/api')
def api_status():
    from config import API_AUTHOR, API_CONTACT
    return jsonify({
        "author": API_AUTHOR,
        "contact": API_CONTACT,
        "service": "TeraBox Standalone API",
        "version": "1.0.0",
        "status": "online",
        "endpoints": {
            "terabox": "/terabox?url=TERABOX_URL",
            "terabox_with_pwd": "/terabox?url=TERABOX_URL&pwd=PASSWORD",
            "download_proxy": "/dl?url=BASE64_DLINK&cookie=BASE64_COOKIE&filename=NAME"
        },
        "examples": [
            "/terabox?url=https://1024terabox.com/s/1HcZ4bbKShOS8o69NX7MXFg",
            "/terabox?url=https://1024terabox.com/s/xxxxx&pwd=1234"
        ]
    })


def _wants_html():
    from flask import request
    best = request.accept_mimetypes.best_match(['application/json', 'text/html'])
    return best == 'text/html' and \
        request.accept_mimetypes[best] >= request.accept_mimetypes['application/json']


@app.errorhandler(404)
def not_found(e):
    from flask import render_template
    from utils import json_response
    if _wants_html():
        return render_template(
            'error.html',
            error_title="Page not found",
            error_message="The page you're looking for doesn't exist or may have moved.",
        ), 404
    return json_response({'error': 'Not Found'}, 404)


@app.errorhandler(500)
def server_error(e):
    from flask import render_template
    from utils import json_response
    if _wants_html():
        return render_template(
            'error.html',
            error_title="Something went wrong",
            error_message="An unexpected error occurred on our end. Please try again shortly.",
        ), 500
    return json_response({'error': 'Internal Server Error', 'message': str(e)}, 500)


if __name__ == '__main__':
    port = int(os.getenv('PORT', 30317))
    host = os.getenv('HOST', '0.0.0.0')
    debug = os.getenv('DEBUG', 'false').lower() == 'true'

    print(f"""
    +==========================================+
    |   TeraBox Standalone API - Flask         |
    |   Running on http://{host}:{port}        |
    +==========================================+
    """)

    app.run(host=host, port=port, debug=debug)
