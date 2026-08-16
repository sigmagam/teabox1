"""
routes/pages.py — Frontend page routes.

This blueprint only renders templates. It does not touch TeraBox
resolving/scraping/download logic at all — that lives entirely in
routes/terabox.py and is untouched. The frontend (static/js/downloader.js)
talks to the existing API endpoints directly:

    GET /terabox?url=<share_url>&pwd=<optional>
    GET /dl?url=<b64 dlink>&cookie=<b64 cookie>&filename=<name>
"""
from flask import Blueprint, render_template

pages_bp = Blueprint('pages', __name__)


@pages_bp.route('/', methods=['GET'])
def home():
    return render_template('index.html', active='home')


@pages_bp.route('/help', methods=['GET'])
def help_page():
    return render_template('help.html', active='help')


@pages_bp.route('/faq', methods=['GET'])
def faq_page():
    return render_template('faq.html', active='faq')
