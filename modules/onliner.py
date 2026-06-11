import asyncio
import random
from utils import log_success, log_error, log_warning, get_modern_headers, create_ja3_connector
import aiohttp

async def online_worker(session, token, ja3_profile=None):
    masked_token = f"{token[:10]}***"
    headers = get_modern_headers(token, ja3_profile)
    gateway_url = "https://discord.com/api/v9/gateway"
    try:
        async with session.get(gateway_url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as res:
            if res.status == 200:
                gateway_data = await res.json()
                ws_url = gateway_data.get("url", "wss://gateway.discord.gg/?v=9&encoding=json")
            else:
                ws_url = "wss://gateway.discord.gg/?v=9&encoding=json"
    except Exception:
        ws_url = "wss://gateway.discord.gg/?v=9&encoding=json"
    log_success(f"オンライン開始 {masked_token}")
    while True:
        try:
            settings_url = "https://discord.com/api/v9/users/@me/settings"
            activities = [
                {"name": "Spotify", "type": 2},
                {"name": "YouTube", "type": 3},
                {"name": "Visual Studio Code", "type": 0},
                {"name": "Discord", "type": 0},
            ]
            activity = random.choice(activities)
            payload = {
                "status": random.choice(["online", "idle", "dnd"]),
                "custom_status": {"text": None, "emoji_id": None, "emoji_name": None, "expires_at": None},
                "activities": [activity]
            }
            async with session.patch(settings_url, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as res:
                if res.status in [200, 204]:
                    await asyncio.sleep(random.uniform(30.0, 60.0))
                elif res.status == 429:
                    retry_after = (await res.json()).get("retry_after", 60)
                    log_warning(f"オンラインレート制限: {retry_after}秒待機 {masked_token}")
                    await asyncio.sleep(retry_after)
                elif res.status == 401:
                    log_error(f"オンライン無効トークン {masked_token}")
                    break
                else:
                    log_error(f"オンライン失敗 {masked_token} (Status: {res.status})")
                    await asyncio.sleep(10)
        except asyncio.TimeoutError:
            log_error(f"オンラインタイムアウト {masked_token}")
            await asyncio.sleep(10)
        except Exception as e:
            log_error(f"オンラインエラー {masked_token}: {e}")
            await asyncio.sleep(10)

async def onliner_menu(tokens):
    from utils import log_info, log_success, select_ja3_profile, load_proxies
    print(f"\n{'='*50}")
    print("Discord Onliner")
    print(f"{'='*50}")
    selected_profiles = select_ja3_profile()
    use_proxy = input("プロキシを使用しますか？ (y/n): ").lower() == 'y'
    proxies = load_proxies() if use_proxy else []
    if proxies:
        log_success(f"{len(proxies)}個のプロキシを読み込みました。")
    log_success("オンライン維持を開始します...")
    log_info("Ctrl+C で停止")
    print()
    tasks = []
    for token in tokens:
        ja3_profile = random.choice(selected_profiles) if selected_profiles and len(selected_profiles) > 1 else (selected_profiles[0] if selected_profiles else None)
        proxy_url = None
        if proxies:
            proxy = random.choice(proxies)
            proxy_url = f"http://{proxy}" if not proxy.startswith("http") else proxy
        connector = create_ja3_connector(ja3_profile, proxy_url)
        session = aiohttp.ClientSession(connector=connector)
        task = asyncio.create_task(online_worker(session, token, ja3_profile))
        tasks.append((task, session))
    try:
        await asyncio.gather(*[t[0] for t in tasks])
    except KeyboardInterrupt:
        log_info("Onliner停止中...")
    finally:
        for _, session in tasks:
            await session.close()
