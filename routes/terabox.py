"""
routes/terabox.py — TeraBox Downloader
Handles TeraBox scraping, session management (via local JSON), and download proxying.
Migrated from Supabase Edge Function (Deno) to Flask.
"""
import os
import json
import time
import random
import re
import string
import urllib.parse
import base64
from urllib.parse import urlparse, parse_qs, urlencode
import requests
from flask import Blueprint, request, Response, stream_with_context
from utils import json_response, error_response
from config import (
    API_AUTHOR,
    API_CONTACT,
    CORS_DOWNLOAD_BASE,
    TERABOX_DOWNLOAD_TOKEN_TTL_SECONDS,
    TERABOX_DOWNLOAD_LINK_BATCH_SIZE,
    TERABOX_SCAN_TIMEOUT_SECONDS,
)

terabox_bp = Blueprint('terabox', __name__, url_prefix='/terabox')


def _resolve_db_dir():
    """
    Serverless platforms (Vercel, AWS Lambda, Netlify) ship a read-only
    filesystem except for /tmp. Detect that environment and store the
    session cache there instead of next to the source code, otherwise
    os.makedirs()/open(..., 'w') blow up with a read-only fs error.
    Falls back to the normal project-local ./database folder for
    traditional hosts (VPS, Procfile-based platforms, local dev).
    """
    is_serverless = any([
        os.environ.get('VERCEL'),
        os.environ.get('NETLIFY'),
        os.environ.get('AWS_LAMBDA_FUNCTION_NAME'),
        os.environ.get('LAMBDA_TASK_ROOT'),
    ])
    if is_serverless:
        return '/tmp/terapi_database'
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), 'database')


DB_DIR = _resolve_db_dir()
os.makedirs(DB_DIR, exist_ok=True)
SESSION_DB_FILE = os.path.join(DB_DIR, 'terabox_session.json')


# ─── TeraBox Hardcoded Headers & Cookies ───────────────────────────────
TERABOX_CONFIG = {
    "HARDCODED_HEADERS": {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36",
        "Connection": "keep-alive",
        "Accept": "application/json, text/plain, */*",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "sec-ch-ua-platform": '"Windows"',
        "X-Requested-With": "XMLHttpRequest",
        "sec-ch-ua": '"Brave";v="147", "Not.A/Brand";v="8", "Chromium";v="147"',
        "Content-Type": "application/x-www-form-urlencoded",
        "sec-ch-ua-mobile": "?0",
        "Sec-GPC": "1",
        "Accept-Language": "en-US,en;q=0.8",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Dest": "empty",
        "Cookie": 'browserid=TtA7v5yR6Ww63FEgTr9PY1OZ6U5_NMhrolc_sNVMHqxBoheDrzWGMVVB0_A=; lang=en; TSID=57UEJEwAyKKRvoKek7ZUGes44RyCAyzr; shareUpdateRandom=12; ndus=Y2L-YenteHui7Sr1wyTFBOIQjLinLSkIZEgufot_; csrfToken=0DPF4idAcFw5nmkP2l5uSwHY; g_state={"i_l":0,"i_ll":1777196753712,"i_b":"n0sCe7X1O4lnsgBVxIBhGPgspZb8fW1Kb6r+Uttz7E4","i_e":{"enable_itp_optimization":0},"i_et":1777196753706}; ndut_fmt=050EF3F3799EDCD8E14DAA5D88D2EBB5FD8529E81F2975F9084000C8A63F886D; ndut_fmv=86007f3893c7cedda99c33d703c9c0e98ecd0580c01d1b5359cb70e7cd722b38ab5750dd338c3a7c51fa970fda43376ba8e19db3eed6c1c2648deb5f9ca6e054a66f1492f8877d8cd1c76783c07bc4cb3bdd0b0cb1571b0ceb63ba1c9487999f9ce21d4109bbfbaca0d256a30d68ff6c'
    },
    "FALLBACK_COOKIES": [
        'browserid=TtA7v5yR6Ww63FEgTr9PY1OZ6U5_NMhrolc_sNVMHqxBoheDrzWGMVVB0_A=; lang=en; TSID=57UEJEwAyKKRvoKek7ZUGes44RyCAyzr; shareUpdateRandom=12; ndus=Y2L-YenteHui7Sr1wyTFBOIQjLinLSkIZEgufot_; csrfToken=0DPF4idAcFw5nmkP2l5uSwHY; g_state={"i_l":0,"i_ll":1777196753712,"i_b":"n0sCe7X1O4lnsgBVxIBhGPgspZb8fW1Kb6r+Uttz7E4","i_e":{"enable_itp_optimization":0},"i_et":1777196753706}; ndut_fmt=050EF3F3799EDCD8E14DAA5D88D2EBB5FD8529E81F2975F9084000C8A63F886D; ndut_fmv=86007f3893c7cedda99c33d703c9c0e98ecd0580c01d1b5359cb70e7cd722b38ab5750dd338c3a7c51fa970fda43376ba8e19db3eed6c1c2648deb5f9ca6e054a66f1492f8877d8cd1c76783c07bc4cb3bdd0b0cb1571b0ceb63ba1c9487999f9ce21d4109bbfbaca0d256a30d68ff6c',
        'browserid=bHXwjpn0VMV3dL9stwTYVRDNwlmQ6kJnm-Gh0gNz6nO2T2-n1dbtewGsnMA=; lang=en; TSID=0nfQUYjScONbu0CXRFegH5B9It3WRY4E; shareUpdateRandom=72; ri=dm; ndus=YdueFBPpeHui_gP7bjKzQfnn8CzSyYhmbI8AgBWr; csrfToken=611BSR6w3EtIOxz3JB6X-njp; ndut_fmt=894A87436CEC92772A4F66C77E01C53CE1E392918CB10D2BF18749E3D5859E56; ndut_fmv=efbcf7bbf41b768952241c54fca14743ccaa7926c262b00f476946cf768141f0f9c08fcf58c55bc63e999f5311e60095776a99a4bcc725a09bfa521245f372db1f54231824258391ffbf2d00fc06f4a1fa3ebac4d6ed693c28e3e1ee86fc8655afc43001ac2027497fedf83a56f0bce9; g_state={"i_l":0,"i_ll":1774063601518,"i_b":"UUtRnBxLBsZPYNR8oBYTZYHf7YAC1y0nzZD8Z9htFOo","i_e":{"enable_itp_optimization":17}}',
        'browserid=yaAAEvCFra2xV9lGMIC4MUSTROZ0i4O1G4L1edQGv1Hp1oNEMzHiJOOt828C60VkpgyzrV9M9NAH8mAh; lang=en; TSID=YtaeBoctgPje67D1jeNpUP27AYguRWe0; shareUpdateRandom=72; ri=dm; ndus=Y4PdFBPpeHuimcpd3KRYlO6esqNmgZnZyTihEFc5; csrfToken=SbsT7Ag89l3II6fPa9DvHaal; ndut_fmt=D4230DA1049020FB282E457549CC41B3CF684B3D58C0B6EE3D0D69DFFAE46F2F; ndut_fmv=7219ead412f7c97da3718f5a1968c6c96361cf002fd2c4c522bb64ea064bcbba35883662fdb4278082c561a1d0f6d75f034759dcfe08ace918e03244f991c1183eff33bde7133e1d9f26d01348b739530524eeaa95e356995b50909186a7a3faa5b8a3fda5203edac41eea5d5add0b39; g_state={"i_l":0,"i_ll":1774063816513,"i_b":"/qhnJcIN42uRxMRJNMwFbbRwq5Ym3nZUs5JtBqPsrqo","i_e":{"enable_itp_optimization":13}}',
        'browserid=fN1EJwYBF70ZPOE6Ur8JnvYECPG2J8qcfAnkENPpGZJkNMsAUe1Vcs4hqOk=; lang=en; TSID=psb5aNbfRaXOxjpLRHosU2LBF0l0tKmj; shareUpdateRandom=35; ri=dm; ndus=Yu8VFBPpeHui_CXhiScW79bXt1Y3skWjsG4bC8BM; csrfToken=UWnOim9gs3OKglqunN9SyE2Y; ndut_fmt=42B0DA64E1AD2FEE666050F19410F03B407F07237DBCA5951CE6A350F8574189; ndut_fmv=3a2e9ec85528367d5ae60faaa609f93712770f2da98c37dd50be657ece033f494f351eba7e521c465eb704612416a6114911ab49780ac76a03aaf23937383db8e000d7732b9852e4093167b22630f1993560175f4a747f8b846cd8f5014b162c476ef74356625d97b979450ff0115ede; g_state={"i_l":0,"i_ll":1774064039400,"i_b":"PigfkMZ1MXL8kDY5NV3SC47kQTxEDInnqVI6RvGl2R8","i_e":{"enable_itp_optimization":0}}'
    ]
}

USER_AGENT_POOL = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36 Edg/129.0.0.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36 OPR/113.0.0.0',
    'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:132.0) Gecko/20100101 Firefox/132.0'
]

TERABOX_PRIMARY_ENDPOINTS = [
    {
        'origin': 'https://dm.1024tera.com',
        'list': 'https://dm.1024tera.com/share/list',
        'verify': 'https://dm.1024tera.com/share/verify',
        'siteReferer': 'https://www.1024tera.com/'
    },
    {
        'origin': 'https://dm.terabox.app',
        'list': 'https://dm.terabox.app/share/list',
        'verify': 'https://dm.terabox.app/share/verify',
        'siteReferer': 'https://www.terabox.app/'
    },
    {
        'origin': 'https://www.terabox.app',
        'list': 'https://www.terabox.app/share/list',
        'verify': 'https://www.terabox.app/share/verify',
        'siteReferer': 'https://www.terabox.app/'
    },
    {
        'origin': 'https://www.1024tera.com',
        'list': 'https://www.1024tera.com/share/list',
        'verify': 'https://www.1024tera.com/share/verify',
        'siteReferer': 'https://www.1024tera.com/'
    }
]

TERABOX_EXTRA_LIST_ENDPOINTS = [
    'https://terabox.com/share/list',
    'https://freeterabox.com/share/list',
    'https://teraboxapp.com/share/list'
]

RETRYABLE_TERABOX_ERRORS = {4000020, 4000018, -6, 400141, 400142}

# ─── Local Database ──────────────────────────────────────────────────────

def _db_read(filename):
    if not os.path.exists(filename):
        return {}
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}

def _db_write(filename, data):
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Failed to write to {filename}: {e}")

def _db_get(filename, key):
    data = _db_read(filename)
    return data.get(key)

def _db_put(filename, key, value):
    data = _db_read(filename)
    data[key] = value
    _db_write(filename, data)



# ─── Utility ─────────────────────────────────────────────────────────────

def _random_token(n=32):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=n))

def _random_ua():
    return random.choice(USER_AGENT_POOL)

def _random_ip():
    ranges = [
        lambda: f"{random.randint(36, 40)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}",
        lambda: f"{random.randint(101, 110)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}",
        lambda: f"{random.randint(175, 179)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}",
        lambda: f"{random.randint(180, 189)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}",
        lambda: f"{random.randint(85, 94)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}",
    ]
    return random.choice(ranges)()

def _get_cookies():
    return [c for c in [TERABOX_CONFIG["HARDCODED_HEADERS"]["Cookie"]] + TERABOX_CONFIG["FALLBACK_COOKIES"] if c]

def _is_folder(item):
    return str(item.get('isdir')) == '1'

def _is_likely_jstoken(token):
    return isinstance(token, str) and len(token) >= 32 and re.match(r'^[A-Za-z0-9_-]+$', token)

def _extract_jstoken(html):
    sources = [html]
    for match in re.finditer(r'decodeURIComponent\(`([^`]+)`\)', html):
        try: sources.append(urllib.parse.unquote(match.group(1)))
        except: pass
    for match in re.finditer(r'decodeURIComponent\("([^"]+)"\)', html):
        try: sources.append(urllib.parse.unquote(match.group(1)))
        except: pass
    for match in re.finditer(r"decodeURIComponent\('([^']+)'\)", html):
        try: sources.append(urllib.parse.unquote(match.group(1)))
        except: pass

    patterns = [
        r'window\.jsToken\s*=\s*["\']([^"\']+)["\']',
        r'jsToken\s*=\s*["\']([^"\']+)["\']',
        r'["\']?jsToken["\']?\s*[:]\s*["\']([^"\']+)["\']',
        r'fn%28%22([^%]+)%22%29',
        r'fn\(\s*["\']jsToken["\']\s*,\s*["\']([^"\']+)["\']\s*\)',
        r'fn\(\s*["\']([A-Za-z0-9_-]{32,})["\']\s*\)'
    ]

    for source in sources:
        for pattern in patterns:
            match = re.search(pattern, source)
            if match and _is_likely_jstoken(match.group(1)):
                return match.group(1)
    return None

def _get_endpoint_meta(list_url):
    for ep in TERABOX_PRIMARY_ENDPOINTS:
        if ep['list'] == list_url:
            return ep
    return None

def _build_terabox_session(input_data):
    matched_primary = None
    for ep in TERABOX_PRIMARY_ENDPOINTS:
        if ep['origin'] == input_data.get('originBase') or \
           ep['list'] == input_data.get('preferredListUrl') or \
           ep['verify'] == input_data.get('preferredVerifyUrl'):
            matched_primary = ep
            break
    if not matched_primary:
        matched_primary = TERABOX_PRIMARY_ENDPOINTS[0]

    cookie = input_data.get('cookie') or TERABOX_CONFIG["HARDCODED_HEADERS"]["Cookie"]
    pref_list = input_data.get('preferredListUrl') or matched_primary['list']
    pref_verify = input_data.get('preferredVerifyUrl') or matched_primary['verify']

    list_endpoints = []
    for x in [TERABOX_PRIMARY_ENDPOINTS[0]['list'], pref_list] + \
             [ep['list'] for ep in TERABOX_PRIMARY_ENDPOINTS] + \
             TERABOX_EXTRA_LIST_ENDPOINTS:
        if x not in list_endpoints:
            list_endpoints.append(x)
            
    verify_endpoints = []
    for x in [TERABOX_PRIMARY_ENDPOINTS[0]['verify'], pref_verify] + \
             [ep['verify'] for ep in TERABOX_PRIMARY_ENDPOINTS]:
        if x not in verify_endpoints:
            verify_endpoints.append(x)

    headers = dict(TERABOX_CONFIG["HARDCODED_HEADERS"])
    headers['Cookie'] = cookie

    return {
        'jsToken': input_data.get('jsToken'),
        'cookie': cookie,
        'originBase': input_data.get('originBase') or matched_primary['origin'],
        'siteReferer': input_data.get('siteReferer') or matched_primary['siteReferer'] or matched_primary['origin'],
        'preferredListUrl': pref_list,
        'preferredVerifyUrl': pref_verify,
        'headers': headers,
        'listEndpoints': list_endpoints,
        'verifyEndpoints': verify_endpoints,
        'source': input_data.get('source', 'Terabox')
    }

# ─── Scraping & Fetching ─────────────────────────────────────────────────

def _fetch_terabox_list(short_url, dir_path, config, endpoints, debug_log):
    last_error_msg = ''
    last_endpoint = None
    data = None
    text = ""

    for endpoint in endpoints:
        ep_meta = _get_endpoint_meta(endpoint)
        origin_base = ep_meta['origin'] if ep_meta else config.get('originBase') or urllib.parse.urlparse(endpoint).netloc
        site_referer = ep_meta['siteReferer'] if ep_meta else origin_base

        params = {
            'app_id': '250528',
            'web': '1',
            'channel': 'dubox',
            'clienttype': '0',
            'jsToken': config.get('jsToken', ''),
            'dp-logid': f"{int(time.time()*1000)}{random.randint(1000000, 9999999)}",
            'page': '1',
            'num': '50',
            'by': 'name',
            'order': 'asc',
            'site_referer': site_referer,
            'shorturl': short_url,
            'root': '1' if dir_path == '/' else '0'
        }
        if dir_path != '/':
            params['dir'] = dir_path

        headers = dict(config.get('headers', {}))
        headers.update({
            'Referer': f"{origin_base}/sharing/link?surl={short_url}&clearCache=1",
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Dest': 'empty',
            'X-Requested-With': 'XMLHttpRequest'
        })

        url = f"{endpoint}?{urllib.parse.urlencode(params)}"
        try:
            r = requests.get(url, headers=headers, timeout=15)
            if r.status_code != 200:
                last_error_msg = f"HTTP {r.status_code}"
                last_endpoint = endpoint
                continue
            
            text = r.text
            last_endpoint = endpoint
            parsed = r.json()

            if parsed.get('errno') != 0 and parsed.get('errno') in RETRYABLE_TERABOX_ERRORS:
                last_error_msg = f"API Error {parsed.get('errno')} on {endpoint}"
                data = parsed
                continue

            has_missing = False
            for item in parsed.get('list', []):
                if not _is_folder(item) and not item.get('dlink'):
                    has_missing = True
                    break
                    
            if parsed.get('errno') == 0 and has_missing:
                last_error_msg = f"API stripped dlink on {endpoint}"
                data = parsed
                continue

            if parsed.get('errno') == 0:
                debug_log.append(f"List OK via {endpoint}.")

            return {'success': True, 'data': parsed, 'endpoint': endpoint}
        except Exception as e:
            last_error_msg = f"Invalid JSON or Network Error: {e}"
            last_endpoint = endpoint
            continue

    if data and 'errno' in data:
        return {
            'success': False,
            'error': 'no_dlink' if data.get('errno') == 0 else data.get('errno'),
            'msg': data.get('errmsg') or last_error_msg,
            'raw': data,
            'endpoint': last_endpoint
        }

    preview = text[:50].replace('\n', ' ') if text else last_error_msg
    debug_log.append(f"All domains failed at {dir_path}. Last: {preview}")
    return {'success': False, 'error': 'html_response', 'msg': 'Received HTML/Invalid JSON', 'endpoint': last_endpoint}

def _probe_terabox_session(short_url, candidate, debug_log):
    session = _build_terabox_session(candidate)
    probe = _fetch_terabox_list(short_url, '/', session, session['listEndpoints'][:3], debug_log)
    if not probe['success']:
        debug_log.append(f"Scraped session rejected ({probe.get('error')} => {probe.get('msg') or 'unusable'}).")
        return None

    matched_primary = _get_endpoint_meta(probe['endpoint'])
    hydrated = _build_terabox_session({
        **candidate,
        'originBase': matched_primary['origin'] if matched_primary else candidate.get('originBase'),
        'siteReferer': matched_primary['siteReferer'] if matched_primary else candidate.get('siteReferer'),
        'preferredListUrl': probe['endpoint'] or candidate.get('preferredListUrl'),
        'preferredVerifyUrl': matched_primary['verify'] if matched_primary else candidate.get('preferredVerifyUrl')
    })
    debug_log.append(f"Validated scraped session via {hydrated['preferredListUrl']}.")
    return hydrated

def _scrape_terabox_config(short_url, debug_log):
    cookies = _get_cookies()
    for i, cookie in enumerate(cookies):
        debug_log.append(f"Attempting scrape with cookie index {i}/{len(cookies)-1}...")
        for endpoint in TERABOX_PRIMARY_ENDPOINTS:
            share_url = f"{endpoint['origin']}/sharing/link?surl={short_url}&clearCache=1"
            ip = _random_ip()
            headers = {
                'User-Agent': _random_ua(),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9,id;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Upgrade-Insecure-Requests': '1',
                'X-Forwarded-For': ip,
                'X-Real-IP': ip,
                'Cookie': cookie
            }
            try:
                r = requests.get(share_url, headers=headers, timeout=10, allow_redirects=True)
                if r.status_code != 200:
                    debug_log.append(f"Cookie {i} on {endpoint['origin']} failed. HTTP {r.status_code}")
                    continue
                html = r.text
                if len(html) < 200:
                    debug_log.append(f"Cookie {i} on {endpoint['origin']} failed (Too short: {len(html)}).")
                    continue
                js_token = _extract_jstoken(html)
                if js_token:
                    debug_log.append(f"Success: Token found with cookie {i} on {endpoint['origin']} (HTML len: {len(html)}).")
                    validated = _probe_terabox_session(short_url, {
                        'jsToken': js_token, 'cookie': cookie, 'originBase': endpoint['origin'],
                        'siteReferer': endpoint['siteReferer'], 'preferredListUrl': endpoint['list'],
                        'preferredVerifyUrl': endpoint['verify'], 'source': 'SCRAPED_NEW'
                    }, debug_log)
                    if validated: return validated
                    continue
                
                if any(x in html for x in ['security-check', 'captcha', 'Access Denied', 'Just a moment']) or len(html) < 500:
                    debug_log.append(f"Cookie {i} on {endpoint['origin']} failed (Blocked).")
                else:
                    debug_log.append(f"Cookie {i} on {endpoint['origin']} failed (No token).")
            except Exception as e:
                debug_log.append(f"Cookie {i} on {endpoint['origin']} exception: {e}")
    debug_log.append("Failed: All cookies exhausted for token scraping.")
    return None

def _verify_password(short_url, pwd, config):
    for endpoint in config.get('verifyEndpoints', []):
        try:
            ep_meta = _get_endpoint_meta(endpoint)
            origin_base = ep_meta['origin'] if ep_meta else config.get('originBase')
            params = {
                'app_id': '250528', 'web': '1', 'channel': 'dubox', 'clienttype': '0',
                'jsToken': config['jsToken'], 'surl': short_url,
                'site_referer': ep_meta['siteReferer'] if ep_meta else config.get('siteReferer')
            }
            headers = dict(config['headers'])
            headers.update({
                'Content-Type': 'application/x-www-form-urlencoded',
                'Referer': f"{origin_base}/sharing/link?surl={short_url}&clearCache=1"
            })
            r = requests.post(f"{endpoint}?{urllib.parse.urlencode(params)}", headers=headers, data=f"pwd={urllib.parse.quote(pwd)}", timeout=10)
            data = r.json()
            if data.get('errno') == 0 and data.get('randsk'):
                return {'randsk': data['randsk'], 'endpoint': endpoint}
        except:
            pass
    return None

def _scan_directory(short_url, dir_path, collection, debug_log, config):
    if config.get('deadline') and time.time() > config['deadline']:
        debug_log.append("Timeout exceeded. Returning partial results.")
        return {'success': True, 'timeout': True}
    
    res = _fetch_terabox_list(short_url, dir_path, config, config['listEndpoints'], debug_log)
    if not res.get('success'):
        return {'error': res.get('error'), 'msg': res.get('msg'), 'raw': res.get('raw')}
    
    data = res['data']
    if data.get('errno') != 0:
        return {'error': data.get('errno'), 'msg': data.get('errmsg'), 'raw': data}
    
    for item in data.get('list', []):
        if config.get('deadline') and time.time() > config['deadline']:
            debug_log.append("Timeout exceeded. Returning partial results.")
            return {'success': True, 'timeout': True}
        
        if _is_folder(item):
            sub = _scan_directory(short_url, item.get('path'), collection, debug_log, config)
            if sub.get('error') or sub.get('timeout'):
                return sub
        else:
            if not item.get('dlink'): continue
            collection.append({
                'filename': item.get('server_filename'),
                'size': item.get('size'),
                'path': item.get('path'),
                'base_link': item.get('dlink'),
                'thumbnail': item.get('thumbs', {}).get('url3'),
                '_short_url': short_url
            })
    return {'success': True}

# ─── Flask Routes ────────────────────────────────────────────────────────

def _b64_pad(s):
    return s + '=' * (-len(s) % 4)

@terabox_bp.route('/download', methods=['GET'])
def terabox_download():
    """
    Self-hosted streaming download proxy — replaces the external Cloudflare
    Worker so downloads don't depend on a third-party service being alive.
    Expects base64-encoded `url` (the raw TeraBox dlink) and `cookie`
    (the session Cookie header) query params, same encoding the /terabox
    endpoint produces.
    """
    encoded_url = request.args.get('url')
    encoded_cookie = request.args.get('cookie')
    filename = request.args.get('filename') or 'download'

    if not encoded_url:
        return error_response(400, "Missing 'url' parameter")

    try:
        dlink = base64.b64decode(_b64_pad(encoded_url)).decode('utf-8')
    except Exception:
        return error_response(400, "Invalid 'url' parameter (bad base64)")

    cookie = ''
    if encoded_cookie:
        try:
            cookie = base64.b64decode(_b64_pad(encoded_cookie)).decode('utf-8')
        except Exception:
            return error_response(400, "Invalid 'cookie' parameter (bad base64)")

    headers = {
        'User-Agent': TERABOX_CONFIG['HARDCODED_HEADERS']['User-Agent'],
        'Accept': '*/*',
        'Accept-Encoding': 'identity',
        'Referer': 'https://www.terabox.app/',
    }
    if cookie:
        headers['Cookie'] = cookie

    # Support Range requests so video players / resumable downloaders work.
    range_header = request.headers.get('Range')
    if range_header:
        headers['Range'] = range_header

    try:
        upstream = requests.get(dlink, headers=headers, stream=True, timeout=30)
    except requests.RequestException as e:
        return error_response(502, f"Upstream request failed: {e}")

    if upstream.status_code >= 400:
        return error_response(upstream.status_code, f"Upstream returned {upstream.status_code}")

    def generate():
        try:
            for chunk in upstream.iter_content(chunk_size=64 * 1024):
                if chunk:
                    yield chunk
        finally:
            upstream.close()

    resp_headers = {
        'Content-Disposition': f'attachment; filename="{filename}"',
    }
    for h in ('Content-Length', 'Content-Type', 'Content-Range', 'Accept-Ranges'):
        if h in upstream.headers:
            resp_headers[h] = upstream.headers[h]
    resp_headers.setdefault('Content-Type', 'application/octet-stream')
    resp_headers.setdefault('Accept-Ranges', 'bytes')

    status = 206 if (range_header and upstream.status_code == 206) else 200
    return Response(stream_with_context(generate()), status=status, headers=resp_headers)


@terabox_bp.route('/', methods=['GET'])
def terabox_index():
    url = request.args.get('url')
    if not url:
        return json_response({
            "author": API_AUTHOR,
            "contact": API_CONTACT,
            "status": "online",
            "service": "TeraBox API",
            "version": "1.0.0",
            "endpoints": {
                "terabox": "/terabox?url=TERABOX_URL",
                "terabox_with_pwd": "/terabox?url=TERABOX_URL&pwd=PASSWORD"
            }
        })
    
    pwd = request.args.get('pwd')
    debug_log = []
    
    short_url = None
    try:
        if 'surl=' in url:
            short_url = parse_qs(urlparse(url).query).get('surl', [None])[0]
        if not short_url:
            match = re.search(r's/1?([A-Za-z0-9_-]+)', url)
            if match: short_url = match.group(1)
    except: pass

    if not short_url:
        return error_response(400, "URL Invalid")

    session = _db_get(SESSION_DB_FILE, 'current')
    source = 'Terabox'
    
    if session and _is_likely_jstoken(session.get('jsToken')):
        debug_log.append(f"Loaded session from database: {session['jsToken'][:10]}...")
        session = _build_terabox_session({**session, 'source': 'Terabox'})
    else:
        session = None

    if not session:
        debug_log.append("Refreshing TeraBox session (missing session)...")
        session = _scrape_terabox_config(short_url, debug_log)
        if session:
            _db_put(SESSION_DB_FILE, 'current', session)
            source = 'SCRAPED_NEW'

    if not session:
        return json_response({
            "author": API_AUTHOR, "contact": API_CONTACT, "status": "error",
            "source": "SCRAPE_FAILED", "request_url": url, "extracted_shorturl": short_url,
            "is_private": bool(pwd), "total_files": 0, "files": [], "debug": debug_log
        })

    config = _build_terabox_session(session)
    config['deadline'] = time.time() + TERABOX_SCAN_TIMEOUT_SECONDS
    all_files = []
    
    if pwd:
        v_res = _verify_password(short_url, pwd, config)
        if v_res and v_res.get('randsk'):
            config['headers']['Cookie'] += f"; BOXCLND={v_res['randsk']}"
            debug_log.append(f"Password verified via {v_res['endpoint']}.")
        else:
            debug_log.append("Password verify failed.")

    res = _scan_directory(short_url, '/', all_files, debug_log, config)
    
    # Retry if needed
    if res.get('error') in ['no_dlink', 'html_response'] or res.get('error') in RETRYABLE_TERABOX_ERRORS:
        debug_log.append(f"Primary session failed ({res.get('error')}). Re-scraping...")
        session = _scrape_terabox_config(short_url, debug_log)
        if session:
            _db_put(SESSION_DB_FILE, 'current', session)
            source = 'SCRAPED_REFRESH'
            config = _build_terabox_session(session)
            config['deadline'] = time.time() + TERABOX_SCAN_TIMEOUT_SECONDS
            all_files = []
            if pwd:
                v_res = _verify_password(short_url, pwd, config)
                if v_res and v_res.get('randsk'):
                    config['headers']['Cookie'] += f"; BOXCLND={v_res['randsk']}"
            res = _scan_directory(short_url, '/', all_files, debug_log, config)

    # Build proxy download links
    # If TERABOX_CORS_DOWNLOAD_BASE is empty/unset (or "self"), route through this
    # Flask server's own /dl endpoint instead of an external worker.
    download_base = CORS_DOWNLOAD_BASE
    if not download_base or download_base.strip().lower() == 'self':
        download_base = f"{request.host_url.rstrip('/')}/dl"

    for f in all_files:
        encoded_dlink = base64.b64encode(f['base_link'].encode('utf-8')).decode('utf-8').rstrip('=')
        encoded_cookie = base64.b64encode(config['headers']['Cookie'].encode('utf-8')).decode('utf-8').rstrip('=')
        filename_q = urllib.parse.quote(f.get('filename') or 'download')
        f['download_link'] = f"{download_base}?url={encoded_dlink}&cookie={encoded_cookie}&filename={filename_q}"

        del f['_short_url']
        del f['base_link']

    return json_response({
        "author": API_AUTHOR, "contact": API_CONTACT,
        "status": "success" if all_files else "error",
        "source": source, "request_url": url, "extracted_shorturl": short_url,
        "is_private": bool(pwd), "total_files": len(all_files),
        "files": all_files, "debug": debug_log
    })


