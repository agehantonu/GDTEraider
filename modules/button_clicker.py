import asyncio
import random
from utils import log_success, log_error, log_warning, log_info, get_modern_headers, create_ja3_connector
import aiohttp

async def click_button_worker(session, token, channel_id, message_id, custom_id, guild_id=None, ja3_profile=None):
    """ボタンを押すワーカー"""
    masked_token = f"{token[:10]}***"
    headers = get_modern_headers(token, ja3_profile)

    url = "https://discord.com/api/v9/interactions"

    payload = {
        "type": 3,
        "nonce": random.randint(1000000000000000000, 9999999999999999999),
        "guild_id": guild_id,
        "channel_id": channel_id,
        "message_flags": 0,
        "message_id": message_id,
        "data": {
            "component_type": 2,
            "custom_id": custom_id
        }
    }

    try:
        async with session.post(url, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=15)) as res:
            if res.status in [200, 201, 204]:
                log_success(f"ボタン押下成功 {masked_token} → {custom_id}")
                return True
            elif res.status == 429:
                retry_after = (await res.json()).get("retry_after", 1)
                log_warning(f"ボタンレート制限: {retry_after}秒 {masked_token}")
                await asyncio.sleep(retry_after)
                return False
            elif res.status == 401:
                log_error(f"ボタン無効トークン {masked_token}")
                return "invalid_token"
            elif res.status == 403:
                log_error(f"ボタン押下禁止 {masked_token}")
                return "forbidden"
            else:
                log_error(f"ボタン押下失敗 {masked_token} (Status: {res.status})")
                return False
    except Exception as e:
        log_error(f"ボタンエラー {masked_token}: {e}")
        return False

async def button_clicker_menu(session, tokens):
    """ボタンクリッカーメニュー"""
    from utils import select_ja3_profile, load_proxies
    print(f"\n{'='*50}")
    print("Discord Button Clicker")
    print(f"{'='*50}")

    channel_id = input("チャンネルIDを入力: ").strip()
    message_id = input("メッセージIDを入力: ").strip()
    custom_id = input("ボタンのcustom_idを入力: ").strip()
    guild_id = input("サーバーIDを入力（DMの場合は空欄）: ").strip() or None

    if not channel_id or not message_id or not custom_id:
        log_error("必要な情報が入力されていません。")
        return

    click_count = int(input("各トークンからの押下回数: ") or "1")
    click_delay = float(input("押下間隔（秒）(最速は 0): ") or "0")

    selected_profiles = select_ja3_profile()
    use_proxy = input("プロキシを使用しますか？ (y/n): ").lower() == 'y'
    proxies = load_proxies() if use_proxy else []
    if proxies:
        log_success(f"{len(proxies)}個のプロキシを読み込みました。")

    log_success(f"ボタン押下を開始します... (Msg: {message_id} | Button: {custom_id})")
    print()

    success_count, fail_count, invalid_tokens = 0, 0, []

    for token in tokens:
        ja3_profile = random.choice(selected_profiles) if selected_profiles and len(selected_profiles) > 1 else (selected_profiles[0] if selected_profiles else None)
        proxy_url = None
        if proxies:
            proxy = random.choice(proxies)
            proxy_url = f"http://{proxy}" if not proxy.startswith("http") else proxy

        for _ in range(click_count):
            if ja3_profile or proxy_url:
                connector = create_ja3_connector(ja3_profile, proxy_url)
                async with aiohttp.ClientSession(connector=connector) as ja3_session:
                    result = await click_button_worker(ja3_session, token, channel_id, message_id, custom_id, guild_id, ja3_profile)
            else:
                result = await click_button_worker(session, token, channel_id, message_id, custom_id, guild_id, None)

            if result == True:
                success_count += 1
            elif result == "invalid_token":
                invalid_tokens.append(token)
                fail_count += 1
                break
            elif result == "forbidden":
                fail_count += 1
                break
            else:
                fail_count += 1

            if click_delay > 0:
                await asyncio.sleep(click_delay)

    print(f"\n{'='*50}")
    print("ボタン押下結果サマリー")
    print(f"{'='*50}")
    log_success(f"成功: {success_count}")
    log_error(f"失敗: {fail_count}")
    if invalid_tokens:
        log_error(f"無効トークン: {len(invalid_tokens)}個")
