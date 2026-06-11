import asyncio
import random
from urllib.parse import quote
from utils import log_success, log_error, log_warning, log_info, get_modern_headers, create_ja3_connector
import aiohttp

async def add_reaction_worker(session, token, channel_id, message_id, emoji, ja3_profile=None):
    masked_token = f"{token[:10]}***"
    headers = get_modern_headers(token, ja3_profile)
    if ":" in emoji:
        emoji_parts = emoji.strip(":").split(":")
        if len(emoji_parts) == 2:
            emoji_str = f"{emoji_parts[0]}:{emoji_parts[1]}"
        else:
            emoji_str = emoji
    else:
        emoji_str = quote(emoji)
    url = f"https://discord.com/api/v9/channels/{channel_id}/messages/{message_id}/reactions/{emoji_str}/@me"
    try:
        async with session.put(url, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as res:
            if res.status in [200, 201, 204]:
                log_success(f"リアクション追加成功 {masked_token} → {emoji}")
                return True
            elif res.status == 429:
                retry_after = (await res.json()).get("retry_after", 60)
                log_warning(f"リアクションレート制限: {retry_after}秒待機 {masked_token}")
                await asyncio.sleep(retry_after)
                return False
            elif res.status == 401:
                log_error(f"リアクション無効なトークン {masked_token}")
                return "invalid_token"
            elif res.status == 403:
                log_error(f"リアクション追加禁止（権限不足） {masked_token}")
                return "forbidden"
            elif res.status == 404:
                log_error(f"メッセージまたは絵文字不存在 {masked_token}")
                return "not_found"
            else:
                log_error(f"リアクション追加失敗 {masked_token} (Status: {res.status})")
                return False
    except Exception as e:
        log_error(f"リアクションエラー {masked_token}: {e}")
        return False

async def reaction_tool_menu(session, tokens):
    print(f"\n{'='*50}")
    print("Discord Reaction Tool")
    print(f"{'='*50}")
    channel_id = input("チャンネルIDを入力: ").strip()
    message_id = input("メッセージIDを入力: ").strip()
    if not channel_id or not message_id:
        log_error("チャンネルIDまたはメッセージIDが入力されていません。")
        return
    emoji_input = input("絵文字を入力（カスタム: :name:id / ユニコード: 😀）: ").strip()
    if not emoji_input:
        log_error("絵文字が入力されていません。")
        return
    reaction_count = int(input("各トークンからのリアクション数: ") or "1")
    from utils import select_ja3_profile, load_proxies
    selected_profiles = select_ja3_profile()
    use_proxy = input("プロキシを使用しますか？ (y/n): ").lower() == 'y'
    proxies = load_proxies() if use_proxy else []
    if proxies:
        log_success(f"{len(proxies)}個のプロキシを読み込みました。")
    log_success(f"リアクション追加を開始します... (Msg: {message_id})")
    print()
    success_count, fail_count, invalid_tokens = 0, 0, []
    for token in tokens:
        ja3_profile = random.choice(selected_profiles) if selected_profiles and len(selected_profiles) > 1 else (selected_profiles[0] if selected_profiles else None)
        proxy_url = None
        if proxies:
            proxy = random.choice(proxies)
            proxy_url = f"http://{proxy}" if not proxy.startswith("http") else proxy
        for _ in range(reaction_count):
            if ja3_profile or proxy_url:
                connector = create_ja3_connector(ja3_profile, proxy_url)
                async with aiohttp.ClientSession(connector=connector) as ja3_session:
                    result = await add_reaction_worker(ja3_session, token, channel_id, message_id, emoji_input, ja3_profile)
                    if result == True:
                        success_count += 1
                    elif result == "invalid_token":
                        invalid_tokens.append(token); fail_count += 1; break
                    elif result == "forbidden":
                        fail_count += 1; break
                    elif result == "not_found":
                        fail_count += 1; break
                    else:
                        fail_count += 1
            else:
                result = await add_reaction_worker(session, token, channel_id, message_id, emoji_input, None)
                if result == True:
                    success_count += 1
                elif result == "invalid_token":
                    invalid_tokens.append(token); fail_count += 1; break
                elif result == "forbidden":
                    fail_count += 1; break
                elif result == "not_found":
                    fail_count += 1; break
                else:
                    fail_count += 1
    print(f"\n{'='*50}")
    print("リアクション追加結果サマリー")
    print(f"{'='*50}")
    log_success(f"成功: {success_count}")
    log_error(f"失敗: {fail_count}")
    if invalid_tokens:
        log_error(f"無効トークン: {len(invalid_tokens)}個")
