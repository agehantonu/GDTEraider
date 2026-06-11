import asyncio
import random
from utils import log_success, log_error, log_warning, get_modern_headers, create_ja3_connector
import aiohttp

async def typing_worker(session, token, channel_id, ja3_profile=None):
    masked_token = f"{token[:10]}***"
    headers = get_modern_headers(token, ja3_profile)
    url = f"https://discord.com/api/v9/channels/{channel_id}/typing"
    log_success(f"タイピング開始 {masked_token} → Channel: {channel_id}")
    while True:
        try:
            async with session.post(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as res:
                if res.status in [200, 204]:
                    await asyncio.sleep(random.uniform(8.0, 10.0))
                elif res.status == 429:
                    retry_after = (await res.json()).get("retry_after", 5)
                    log_warning(f"タイピングレート制限: {retry_after}秒待機 {masked_token}")
                    await asyncio.sleep(retry_after)
                elif res.status == 401:
                    log_error(f"タイピング無効トークン {masked_token}")
                    break
                elif res.status == 403:
                    log_error(f"タイピング権限不足 {masked_token}")
                    break
                elif res.status == 404:
                    log_error(f"タイピングチャンネル不存在 {masked_token}")
                    break
                else:
                    log_error(f"タイピング失敗 {masked_token} (Status: {res.status})")
                    await asyncio.sleep(5)
        except asyncio.TimeoutError:
            log_error(f"タイピングタイムアウト {masked_token}")
            await asyncio.sleep(5)
        except Exception as e:
            log_error(f"タイピングエラー {masked_token}: {e}")
            await asyncio.sleep(5)

async def typer_menu(tokens):
    from utils import log_info, log_success, select_ja3_profile, load_proxies
    print(f"\n{'='*50}")
    print("Discord Typer")
    print(f"{'='*50}")
    channel_id = input("タイピング表示するチャンネルIDを入力: ").strip()
    if not channel_id:
        log_error("チャンネルIDが入力されていません。")
        return
    selected_profiles = select_ja3_profile()
    use_proxy = input("プロキシを使用しますか？ (y/n): ").lower() == 'y'
    proxies = load_proxies() if use_proxy else []
    if proxies:
        log_success(f"{len(proxies)}個のプロキシを読み込みました。")
    log_success(f"タイピング表示を開始します... (Channel: {channel_id})")
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
        task = asyncio.create_task(typing_worker(session, token, channel_id, ja3_profile))
        tasks.append((task, session))
    try:
        await asyncio.gather(*[t[0] for t in tasks])
    except KeyboardInterrupt:
        log_info("Typer停止中...")
    finally:
        for _, session in tasks:
            await session.close()
