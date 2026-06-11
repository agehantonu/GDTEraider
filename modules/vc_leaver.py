import asyncio
import random
from utils import log_success, log_error, log_warning, get_modern_headers, create_ja3_connector
import aiohttp

async def vc_leave_worker(session, token, guild_id, ja3_profile=None):
    masked_token = f"{token[:10]}***"
    headers = get_modern_headers(token, ja3_profile)
    url = f"https://discord.com/api/v9/guilds/{guild_id}/voice-states/@me"
    payload = {
        "channel_id": None,
        "self_mute": False,
        "self_deaf": False,
        "self_video": False
    }
    try:
        async with session.patch(url, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=15)) as res:
            if res.status in [200, 201, 204]:
                log_success(f"VC退出成功 {masked_token} → Guild: {guild_id}")
                return True
            elif res.status == 429:
                retry_after = (await res.json()).get("retry_after", 60)
                log_warning(f"VCレート制限: {retry_after}秒待機 {masked_token}")
                await asyncio.sleep(retry_after)
                return False
            elif res.status == 401:
                log_error(f"VC無効なトークン {masked_token}")
                return "invalid_token"
            elif res.status == 403:
                log_error(f"VC退出禁止（権限不足） {masked_token}")
                return "forbidden"
            else:
                log_error(f"VC退出失敗 {masked_token} (Status: {res.status})")
                return False
    except Exception as e:
        log_error(f"VCエラー {masked_token}: {e}")
        return False

async def vc_leaver_menu(session, tokens):
    print(f"\n{'='*50}")
    print("Discord VC Leaver")
    print(f"{'='*50}")
    guild_id = input("サーバーIDを入力: ").strip()
    if not guild_id:
        log_error("サーバーIDが入力されていません。")
        return
    from utils import select_ja3_profile, load_proxies
    selected_profiles = select_ja3_profile()
    use_proxy = input("プロキシを使用しますか？ (y/n): ").lower() == 'y'
    proxies = load_proxies() if use_proxy else []
    if proxies:
        log_success(f"{len(proxies)}個のプロキシを読み込みました。")
    max_retries = int(input("最大リトライ回数 (デフォルト 3): ") or "3")
    log_success(f"VC退出を開始します... (Guild: {guild_id})")
    print()
    success_count, fail_count, invalid_tokens = 0, 0, []
    for i, token in enumerate(tokens):
        ja3_profile = random.choice(selected_profiles) if selected_profiles and len(selected_profiles) > 1 else (selected_profiles[0] if selected_profiles else None)
        proxy_url = None
        if proxies:
            proxy = random.choice(proxies)
            proxy_url = f"http://{proxy}" if not proxy.startswith("http") else proxy
        if ja3_profile or proxy_url:
            connector = create_ja3_connector(ja3_profile, proxy_url)
            async with aiohttp.ClientSession(connector=connector) as ja3_session:
                for attempt in range(max_retries):
                    result = await vc_leave_worker(ja3_session, token, guild_id, ja3_profile)
                    if result == True:
                        success_count += 1; break
                    elif result == "invalid_token":
                        invalid_tokens.append(token); fail_count += 1; break
                    elif result == "forbidden":
                        fail_count += 1; break
                    elif attempt < max_retries - 1:
                        await asyncio.sleep(2 ** attempt)
                    else:
                        fail_count += 1
        else:
            for attempt in range(max_retries):
                result = await vc_leave_worker(session, token, guild_id, None)
                if result == True:
                    success_count += 1; break
                elif result == "invalid_token":
                    invalid_tokens.append(token); fail_count += 1; break
                elif result == "forbidden":
                    fail_count += 1; break
                elif attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                else:
                    fail_count += 1
    print(f"\n{'='*50}")
    print("VC退出結果サマリー")
    print(f"{'='*50}")
    log_success(f"成功: {success_count}")
    log_error(f"失敗: {fail_count}")
    if invalid_tokens:
        log_error(f"無効トークン: {len(invalid_tokens)}個")
        with open("invalid_tokens.txt", "w", encoding="utf-8") as f:
            for t in invalid_tokens:
                f.write(t + "\n")
        log_warning("無効トークンを invalid_tokens.txt に保存しました。")
