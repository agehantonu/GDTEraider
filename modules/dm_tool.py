import asyncio
from utils import log_success, log_error, log_warning, get_modern_headers, generate_random_string

async def create_dm_channel(session, token, user_id, ja3_profile=None):
    masked_token = f"{token[:10]}***"
    headers = get_modern_headers(token, ja3_profile)
    url = "https://discord.com/api/v9/users/@me/channels"
    payload = {"recipient_id": user_id}
    try:
        async with session.post(url, headers=headers, json=payload, timeout=__import__('aiohttp').ClientTimeout(total=15)) as res:
            if res.status in [200, 201]:
                data = await res.json()
                log_success(f"DMチャンネル作成成功 {masked_token} → User: {user_id}")
                return data.get("id")
            elif res.status == 429:
                retry_after = (await res.json()).get("retry_after", 60)
                log_warning(f"DMレート制限: {retry_after}秒待機 {masked_token}")
                await asyncio.sleep(retry_after)
                return None
            elif res.status == 401:
                log_error(f"DM無効なトークン {masked_token}")
                return "invalid_token"
            elif res.status == 403:
                log_error(f"DM作成禁止（ブロック等） {masked_token}")
                return "forbidden"
            else:
                log_error(f"DMチャンネル作成失敗 {masked_token} (Status: {res.status})")
                return None
    except Exception as e:
        log_error(f"DMエラー {masked_token}: {e}")
        return None

async def dm_send_worker(session, token, dm_channel_id, base_text, use_rand_str, rand_str_len, delay, count, ja3_profile=None):
    masked_token = f"{token[:10]}***"
    headers = get_modern_headers(token, ja3_profile)
    url = f"https://discord.com/api/v9/channels/{dm_channel_id}/messages"
    for _ in range(count):
        full_text = base_text
        if use_rand_str:
            full_text += generate_random_string(rand_str_len)
        payload = {"content": full_text}
        try:
            async with session.post(url, headers=headers, json=payload) as res:
                if res.status in [200, 201]:
                    log_success(f"DM送信成功 {masked_token} → DM: {dm_channel_id}")
                elif res.status == 429:
                    retry_after = (await res.json()).get("retry_after", 1)
                    log_error(f"DM速度制限: {retry_after}秒待機 {masked_token}")
                    await asyncio.sleep(retry_after)
                elif res.status == 401:
                    log_error(f"DM無効なトークン {masked_token}")
                    break
                elif res.status == 403:
                    log_error(f"DM送信禁止（ブロック等） {masked_token}")
                    break
                else:
                    log_error(f"DM送信失敗 {masked_token} (Status: {res.status})")
        except Exception as e:
            log_error(f"DM送信失敗 {masked_token} (エラー: {e})")
        if delay > 0:
            await asyncio.sleep(delay)

async def dm_tool_menu(session, tokens):
    from utils import log_info, log_success, log_error
    print(f"\n{'='*50}")
    print("Discord DM Tool")
    print(f"{'='*50}")
    user_id = input("送信先ユーザーIDを入力: ").strip()
    base_text = input("送信内容を入れてください: ")
    if not user_id:
        log_error("ユーザーIDが入力されていません。")
        return
    use_rand_str = input("ランダム文字列を付け足しますか？ (y/n): ").lower() == 'y'
    rand_str_len = int(input("ランダム文字列の長さを入力してください: ")) if use_rand_str else 0
    send_count = int(input("各トークンからの送信数を入力してください: "))
    send_delay = float(input("送信間隔（秒）を入力してください (最速は 0): "))
    log_success(f"DM送信を開始します... (User: {user_id})")
    print()
    for token in tokens:
        dm_channel_id = await create_dm_channel(session, token, user_id)
        if dm_channel_id == "invalid_token" or dm_channel_id == "forbidden" or dm_channel_id is None:
            if dm_channel_id is None:
                log_error(f"DMチャンネル作成失敗のためスキップ {token[:10]}***")
            continue
        await dm_send_worker(session, token, dm_channel_id, base_text, use_rand_str, rand_str_len, send_delay, send_count)
