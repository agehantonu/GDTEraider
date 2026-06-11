import os
import random
import string
import json
import ssl
import base64
from datetime import datetime
import aiohttp
from aiohttp import TCPConnector
from colorama import init, Fore, Style

init(autoreset=True)

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config", "config.json")

def load_config():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_config(config):
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4, ensure_ascii=False)

CONFIG = load_config()

JA3_CHROME_120 = "771,4865-4866-4867-49195-49199-49196-49200-52393-52392-49171-49172-156-157-47-53,0-23-65281-10-11-35-16-5-13-18-51-45-43-27-17513-21,29-23-24,0"
JA3_CHROME_120_HASH = "cd08e65939142c526675d794c71a664b"
JA3_FIREFOX_120 = "771,4865-4867-4866-49195-49199-52393-52392-49196-49200-49162-49161-49171-49172-51-57-47-53-10,0-23-65281-10-11-35-16-5-51-43-13-45-28-65037,29-23-24-25-256-257,0"
JA3_FIREFOX_120_HASH = "a69708a8b232d3fbae7047a2f8d4c621"
JA3_EDGE_120 = "771,4865-4866-4867-49195-49199-49196-49200-52393-52392-49171-49172-156-157-47-53,0-23-65281-10-11-35-16-5-13-18-51-45-43-27-17513,29-23-24,0"
JA3_EDGE_120_HASH = "b32309a26951912be7dba376398abc3b"
JA3_SAFARI_17 = "771,4865-4866-4867-49196-49195-52393-49200-49199-52392-49162-49161-49172-49171-157-156-53-47-10,65281-0-23-35-13-5-18-16-30032-11-10,29-23-24-25,0"
JA3_SAFARI_17_HASH = "b1e5db7c6d6e5d6b8e8c5d6e7f8a9b0c1"

JA3_PROFILES = [
    ("chrome_120", JA3_CHROME_120, JA3_CHROME_120_HASH),
    ("firefox_120", JA3_FIREFOX_120, JA3_FIREFOX_120_HASH),
    ("edge_120", JA3_EDGE_120, JA3_EDGE_120_HASH),
]

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def get_time_str():
    return datetime.now().strftime("[%H:%M:%S]")

def generate_random_string(length):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

def generate_random_ua():
    versions = [
        ("Chrome", "120.0.0.0", "537.36"),
        ("Chrome", "121.0.0.0", "537.36"),
        ("Chrome", "119.0.0.0", "537.36"),
        ("Edg", "120.0.0.0", "537.36"),
        ("Firefox", "120.0", "Gecko/20100101"),
    ]
    browser, ver, engine = random.choice(versions)
    if browser == "Firefox":
        return f"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/{ver}"
    return f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/{engine} (KHTML, like Gecko) {browser}/{ver} Safari/{engine}"

def get_super_properties(ua):
    props = {
        "os": "Windows",
        "browser": "Chrome" if "Chrome" in ua else "Firefox" if "Firefox" in ua else "Edge",
        "device": "",
        "system_locale": "ja",
        "has_client_mods": False,
        "browser_user_agent": ua,
        "browser_version": "120.0.0.0" if "Chrome" in ua or "Edg" in ua else "120.0",
        "os_version": "10",
        "referrer": "https://www.google.com/",
        "referring_domain": "www.google.com",
        "referrer_current": "",
        "referring_domain_current": "",
        "release_channel": "stable",
        "client_build_number": 250836,
        "client_event_source": None,
        "client_launch_id": generate_random_string(32) + "-" + generate_random_string(4) + "-" + generate_random_string(4) + "-" + generate_random_string(4) + "-" + generate_random_string(12),
        "launch_signature": generate_random_string(8) + "-" + generate_random_string(4) + "-" + generate_random_string(4) + "-" + generate_random_string(4) + "-" + generate_random_string(12),
        "client_heartbeat_session_id": generate_random_string(32) + "-" + generate_random_string(4) + "-" + generate_random_string(4) + "-" + generate_random_string(4) + "-" + generate_random_string(12),
        "client_app_state": "focused"
    }
    return base64.b64encode(json.dumps(props).encode()).decode()

def get_modern_headers(token, ja3_profile=None):
    ua = generate_random_ua()
    super_props = get_super_properties(ua)
    ja3_headers = {}
    if ja3_profile:
        ja3_headers["X-JA3-Fingerprint"] = ja3_profile[2]
        ja3_headers["X-TLS-Version"] = "TLSv1.3"
    return {
        "Authorization": token,
        "Content-Type": "application/json",
        "User-Agent": ua,
        "Accept": "*/*",
        "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "X-Super-Properties": super_props,
        "X-Discord-Locale": "ja",
        "X-Discord-Timezone": "Asia/Tokyo",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "Origin": "https://discord.com",
        "Referer": "https://discord.com/channels/@me",
        "Connection": "keep-alive",
        "Cache-Control": "no-cache",
        **ja3_headers
    }

def log_success(message):
    print(f"{get_time_str()}{Fore.GREEN}[+]{Style.RESET_ALL} {message}")

def log_error(message):
    print(f"{get_time_str()}{Fore.RED}[-]{Style.RESET_ALL} {message}")

def log_warning(message):
    print(f"{get_time_str()}{Fore.YELLOW}[!]{Style.RESET_ALL} {message}")

def log_info(message):
    print(f"{get_time_str()}{Fore.CYAN}[*]{Style.RESET_ALL} {message}")

class JA3SSLContext(ssl.SSLContext):
    def __init__(self, ja3_string=None, ja3_hash=None):
        super().__init__(ssl.PROTOCOL_TLS_CLIENT)
        self.ja3_string = ja3_string
        self.ja3_hash = ja3_hash
        self.minimum_version = ssl.TLSVersion.TLSv1_2
        self.maximum_version = ssl.TLSVersion.MAXIMUM_SUPPORTED
        if ja3_string:
            self._configure_ciphers(ja3_string)
        self.check_hostname = False
        self.verify_mode = ssl.CERT_NONE

    def _configure_ciphers(self, ja3_string):
        parts = ja3_string.split(",")
        if len(parts) >= 2:
            ciphers = parts[1].split("-")
            cipher_map = {
                "4865": "TLS_AES_128_GCM_SHA256", "4866": "TLS_AES_256_GCM_SHA384",
                "4867": "TLS_CHACHA20_POLY1305_SHA256", "49195": "TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256",
                "49199": "TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256", "49196": "TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384",
                "49200": "TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384", "52393": "TLS_ECDHE_ECDSA_WITH_CHACHA20_POLY1305_SHA256",
                "52392": "TLS_ECDHE_RSA_WITH_CHACHA20_POLY1305_SHA256", "49171": "TLS_ECDHE_RSA_WITH_AES_128_CBC_SHA",
                "49172": "TLS_ECDHE_RSA_WITH_AES_256_CBC_SHA", "156": "TLS_RSA_WITH_AES_128_GCM_SHA256",
                "157": "TLS_RSA_WITH_AES_256_GCM_SHA384", "47": "TLS_RSA_WITH_AES_128_CBC_SHA",
                "53": "TLS_RSA_WITH_AES_256_CBC_SHA",
            }
            cipher_names = [cipher_map.get(c, "") for c in ciphers if c in cipher_map]
            if cipher_names:
                try:
                    self.set_ciphers(":".join(cipher_names))
                except ssl.SSLError:
                    pass

def create_ja3_connector(ja3_profile=None, proxy=None):
    if ja3_profile:
        ja3_string, ja3_hash = ja3_profile[1], ja3_profile[2]
        ssl_context = JA3SSLContext(ja3_string, ja3_hash)
    else:
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
    return TCPConnector(
        ssl=ssl_context, limit=100, limit_per_host=30,
        enable_cleanup_closed=True, force_close=True, ttl_dns_cache=300,
    )

def select_ja3_profile():
    print(f"\n{Fore.CYAN}JA3/JA4 プロファイル選択:{Style.RESET_ALL}")
    print("1: Chrome 120 (推奨)")
    print("2: Firefox 120")
    print("3: Edge 120")
    print("4: Safari 17")
    print("5: ランダムローテーション")
    print("6: JA3不使用")
    ja3_choice = input("選択 > ").strip()
    ja3_profiles = {
        "1": [JA3_PROFILES[0]], "2": [JA3_PROFILES[1]], "3": [JA3_PROFILES[2]],
        "4": [("safari_17", JA3_SAFARI_17, JA3_SAFARI_17_HASH)],
        "5": JA3_PROFILES, "6": None
    }
    return ja3_profiles.get(ja3_choice, [JA3_PROFILES[0]])

def load_proxies():
    proxies = []
    if os.path.exists("proxies.txt"):
        with open("proxies.txt", "r", encoding="utf-8") as f:
            proxies = [line.strip() for line in f if line.strip()]
    return proxies

async def gemini_chat(prompt, language="ja", topic=""):
    """Gemini APIでAIチャットを生成"""
    api_key = CONFIG.get("ai_chater", {}).get("gemini_api_key", "")
    if not api_key:
        return None

    model = CONFIG.get("ai_chater", {}).get("model", "gemini-2.0-flash")
    max_tokens = CONFIG.get("ai_chater", {}).get("max_tokens", 500)
    temperature = CONFIG.get("ai_chater", {}).get("temperature", 0.9)

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

    system_prompt = f"You are a chat participant. Speak in {language}. Topic: {topic}. Keep it natural, casual, and under 100 characters. No hashtags, no emojis unless asked."

    payload = {
        "contents": [
            {"role": "user", "parts": [{"text": system_prompt + "\n\nUser: " + prompt}]}
        ],
        "generationConfig": {
            "maxOutputTokens": max_tokens,
            "temperature": temperature,
        }
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=30)) as res:
                if res.status == 200:
                    data = await res.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "").strip()
                        return text[:500]
                return None
    except Exception as e:
        log_error(f"Gemini APIエラー: {e}")
        return None
