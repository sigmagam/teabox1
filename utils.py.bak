"""
utils.py — Shared utility functions for the standalone TeraBox API.
"""
import json
import time
from flask import make_response

from config import API_AUTHOR, API_CONTACT, CORS_HEADERS


def sleep_ms(ms: int) -> None:
    time.sleep(ms / 1000.0)


def json_response(data, status: int = 200):
    payload = data

    if isinstance(payload, dict):
        if 'author' not in payload:
            payload['author'] = API_AUTHOR
        if 'contact' not in payload:
            payload['contact'] = API_CONTACT
    elif isinstance(payload, list):
        payload = {'author': API_AUTHOR, 'contact': API_CONTACT, 'data': payload}

    response = make_response(json.dumps(payload, ensure_ascii=False, indent=2), status)
    response.headers['Content-Type'] = 'application/json; charset=utf-8'
    for key, value in CORS_HEADERS.items():
        response.headers[key] = value
    return response


def error_response(status: int, message: str):
    return json_response({
        'author': API_AUTHOR,
        'message': 'error',
        'error': message,
    }, status)
