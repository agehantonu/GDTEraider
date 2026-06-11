import asyncio
from utils import log_success, log_error, get_modern_headers, generate_random_string
from modules.messenger import get_channel_members

async def reply_message_worker(session, token, channel_id, message_id, base_text, use_rand_str, rand_str_len, use_mention, member_ids, delay, count):
    masked_token = f"{token[:10]}***"
    headers = get_modern_headers(token)
    url = f"https://discord.com/api/v9/channels/{channel_id}/messages"
    for _ in range(count):
        full_text = base_text
        if use_rand_str:
            full_text += generate_random_string(rand_str_len)
        if use_mention and member_ids:
            full_text += f" <@{__import__('random').choice(member_ids)}>"
        payload = {
            "content": full_text,
            "message_reference": {"channel_id": channel_id, "message_id": message_id},
            "allowed_mentions": {"replied_user": True}
        }
        try:
            async with session.post(url, headers=headers, json=payload) as res:
                if res.status in [200, 201]:
                    log_success(f"リプライ成功 {masked_token} → Msg: {message_id}")
                elif res.status == 429:
                    retry_after = (await res.json()).get("retry_after", 1)
                    log_error(f"リプライ速度制限: {retry_after}秒待機 {masked_token}")
                    await asyncio.sleep(retry_after)
                else:
                    log_error(f"リプライ失敗 {masked_token} (Status: {res.status})")
        except Exception as e:
            log_error(f"リプライ失敗 {masked_token} (エラー: {e})")
        if delay > 0:
            await asyncio.sleep(delay)

async def replyer_menu(session, tokens):
    from utils import log_info, log_success, log_error
    print(f"\n{'='*50}")
    print("Discord Replyer")
    print(f"{'='*50}")
    channel_id = input("送信先チャンネルIDを入れてください: ")
    message_id = input("リプライ先のメッセージIDを入れてください: ")
    base_text = input("送信内容を入れてください: ")
    if not message_id:
        log_error("メッセージIDが入力されていません。")
        return
    use_rand_str = input("ランダム文字列を付け足しますか？ (y/n): ").lower() == 'y'
    rand_str_len = int(input("ランダム文字列の長さを入力してください: ")) if use_rand_str else 0
    use_mention = input("ランダムメンションをつけますか？ (y/n): ").lower() == 'y'
    member_ids = []
    if use_mention:
        log_success("チャンネルからユーザーIDを取得中...")
        for t in tokens:
            member_ids = await get_channel_members(session, t, channel_id)
            if member_ids:
                log_success(f"{len(member_ids)}人のユーザーIDを取得しました。")
                break
        if not member_ids:
            log_error("ユーザーIDを取得できませんでした。メンションなしで続行します。")
            use_mention = False
    send_count = int(input("各トークンからの送信数を入力してください: "))
    send_delay = float(input("送信間隔（秒）を入力してください (最速は 0): "))
    log_success(f"リプライ送信を開始します... (Reply to: {message_id})")
    print()
    tasks = []
    for token in tokens:
        tasks.append(reply_message_worker(session, token, channel_id, message_id, base_text, use_rand_str, rand_str_len, use_mention, member_ids, send_delay, send_count))
    await asyncio.gather(*tasks)
