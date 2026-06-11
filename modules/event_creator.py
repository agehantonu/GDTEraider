import asyncio
import random
from datetime import datetime, timedelta
from utils import log_success, log_error, log_warning, log_info, get_modern_headers, create_ja3_connector
import aiohttp

async def create_event_worker(session, token, guild_id, event_data, ja3_profile=None):
    masked_token = f"{token[:10]}***"
    headers = get_modern_headers(token, ja3_profile)
    url = f"https://discord.com/api/v9/guilds/{guild_id}/scheduled-events"
    try:
        async with session.post(url, headers=headers, json=event_data, timeout=aiohttp.ClientTimeout(total=15)) as res:
            if res.status in [200, 201]:
                data = await res.json()
                log_success(f"イベント作成成功 {masked_token} → {data.get('name', 'Unknown')}")
                return True
            elif res.status == 429:
                retry_after = (await res.json()).get("retry_after", 60)
                log_warning(f"イベントレート制限: {retry_after}秒待機 {masked_token}")
                await asyncio.sleep(retry_after)
                return False
            elif res.status == 401:
                log_error(f"イベント無効なトークン {masked_token}")
                return "invalid_token"
            elif res.status == 403:
                log_error(f"イベント作成禁止（権限不足） {masked_token}")
                return "forbidden"
            else:
                log_error(f"イベント作成失敗 {masked_token} (Status: {res.status})")
                return False
    except Exception as e:
        log_error(f"イベントエラー {masked_token}: {e}")
        return False

async def event_creator_menu(session, tokens):
    print(f"\n{'='*50}")
    print("Discord Event Creator")
    print(f"{'='*50}")
    guild_id = input("サーバーIDを入力: ").strip()
    if not guild_id:
        log_error("サーバーIDが入力されていません。")
        return
    event_name = input("イベント名を入力: ")
    event_description = input("イベント説明を入力: ")
    channel_id = input("ボイスチャンネルIDを入力（外部イベントの場合は空欄）: ").strip() or None
    event_count = int(input("作成するイベント数: ") or "1")
    from utils import select_ja3_profile, load_proxies
    selected_profiles = select_ja3_profile()
    use_proxy = input("プロキシを使用しますか？ (y/n): ").lower() == 'y'
    proxies = load_proxies() if use_proxy else []
    if proxies:
        log_success(f"{len(proxies)}個のプロキシを読み込みました。")
    log_success(f"イベント作成を開始します... (Guild: {guild_id})")
    print()
    success_count, fail_count, invalid_tokens = 0, 0, []
    for i in range(event_count):
        start_time = (datetime.utcnow() + timedelta(hours=i+1)).isoformat() + "Z"
        end_time = (datetime.utcnow() + timedelta(hours=i+2)).isoformat() + "Z"
        event_data = {
            "name": f"{event_name} #{i+1}" if event_count > 1 else event_name,
            "description": event_description,
            "privacy_level": 2,
            "entity_type": 2 if channel_id else 3,
            "channel_id": channel_id,
            "scheduled_start_time": start_time,
            "scheduled_end_time": end_time
        }
        for token in tokens:
            ja3_profile = random.choice(selected_profiles) if selected_profiles and len(selected_profiles) > 1 else (selected_profiles[0] if selected_profiles else None)
            proxy_url = None
            if proxies:
                proxy = random.choice(proxies)
                proxy_url = f"http://{proxy}" if not proxy.startswith("http") else proxy
            if ja3_profile or proxy_url:
                connector = create_ja3_connector(ja3_profile, proxy_url)
                async with aiohttp.ClientSession(connector=connector) as ja3_session:
                    result = await create_event_worker(ja3_session, token, guild_id, event_data, ja3_profile)
                    if result == True:
                        success_count += 1
                    elif result == "invalid_token":
                        invalid_tokens.append(token); fail_count += 1
                    elif result == "forbidden":
                        fail_count += 1
                    else:
                        fail_count += 1
            else:
                result = await create_event_worker(session, token, guild_id, event_data, None)
                if result == True:
                    success_count += 1
                elif result == "invalid_token":
                    invalid_tokens.append(token); fail_count += 1
                elif result == "forbidden":
                    fail_count += 1
                else:
                    fail_count += 1
    print(f"\n{'='*50}")
    print("イベント作成結果サマリー")
    print(f"{'='*50}")
    log_success(f"成功: {success_count}")
    log_error(f"失敗: {fail_count}")
    if invalid_tokens:
        log_error(f"無効トークン: {len(invalid_tokens)}個")
