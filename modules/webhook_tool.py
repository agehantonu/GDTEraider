import asyncio
import random
from utils import log_success, log_error, log_warning, log_info, get_modern_headers, create_ja3_connector, generate_random_string
import aiohttp

async def create_webhook_worker(session, token, channel_id, webhook_name, ja3_profile=None):
    masked_token = f"{token[:10]}***"
    headers = get_modern_headers(token, ja3_profile)
    url = f"https://discord.com/api/v9/channels/{channel_id}/webhooks"
    payload = {"name": webhook_name}
    try:
        async with session.post(url, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=15)) as res:
            if res.status in [200, 201]:
                data = await res.json()
                log_success(f"Webhook作成成功 {masked_token} → {data.get('name')}")
                return data.get("url")
            elif res.status == 429:
                retry_after = (await res.json()).get("retry_after", 60)
                log_warning(f"Webhookレート制限: {retry_after}秒待機 {masked_token}")
                await asyncio.sleep(retry_after)
                return None
            elif res.status == 401:
                log_error(f"Webhook無効なトークン {masked_token}")
                return "invalid_token"
            elif res.status == 403:
                log_error(f"Webhook作成禁止（権限不足） {masked_token}")
                return "forbidden"
            elif res.status == 400:
                log_error(f"Webhook作成失敗（上限等） {masked_token}")
                return "limit"
            else:
                log_error(f"Webhook作成失敗 {masked_token} (Status: {res.status})")
                return None
    except Exception as e:
        log_error(f"Webhookエラー {masked_token}: {e}")
        return None

async def send_webhook_message(webhook_url, content, username=None, avatar_url=None):
    payload = {"content": content}
    if username:
        payload["username"] = username
    if avatar_url:
        payload["avatar_url"] = avatar_url
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(webhook_url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as res:
                if res.status in [200, 201, 204]:
                    return True
                elif res.status == 429:
                    retry_after = (await res.json()).get("retry_after", 1)
                    await asyncio.sleep(retry_after)
                    return False
                else:
                    return False
    except Exception:
        return False

async def webhook_tool_menu(session, tokens):
    print(f"\n{'='*50}")
    print("Discord Webhook Tool")
    print(f"{'='*50}")
    guild_id = input("サーバーIDを入力: ").strip()
    channel_id = input("チャンネルIDを入力: ").strip()
    if not guild_id or not channel_id:
        log_error("サーバーIDまたはチャンネルIDが入力されていません。")
        return
    webhook_count = int(input("作成するWebhook数: ") or "10")
    webhook_name = input("Webhook名を入力: ") or "Webhook"
    send_messages = input("Webhookでメッセージを送信しますか？ (y/n): ").lower() == 'y'
    message_content = ""
    send_count = 0
    if send_messages:
        message_content = input("送信内容を入力: ")
        send_count = int(input("各Webhookからの送信数: ") or "1")
    from utils import select_ja3_profile, load_proxies
    selected_profiles = select_ja3_profile()
    use_proxy = input("プロキシを使用しますか？ (y/n): ").lower() == 'y'
    proxies = load_proxies() if use_proxy else []
    if proxies:
        log_success(f"{len(proxies)}個のプロキシを読み込みました。")
    log_success(f"Webhook作成を開始します... (Channel: {channel_id})")
    print()
    created_webhooks = []
    success_count, fail_count, invalid_tokens = 0, 0, []
    for i in range(webhook_count):
        name = f"{webhook_name}-{i+1}" if webhook_count > 1 else webhook_name
        for token in tokens:
            ja3_profile = random.choice(selected_profiles) if selected_profiles and len(selected_profiles) > 1 else (selected_profiles[0] if selected_profiles else None)
            proxy_url = None
            if proxies:
                proxy = random.choice(proxies)
                proxy_url = f"http://{proxy}" if not proxy.startswith("http") else proxy
            webhook_url = None
            if ja3_profile or proxy_url:
                connector = create_ja3_connector(ja3_profile, proxy_url)
                async with aiohttp.ClientSession(connector=connector) as ja3_session:
                    result = await create_webhook_worker(ja3_session, token, channel_id, name, ja3_profile)
                    if result and result not in ["invalid_token", "forbidden", "limit"]:
                        webhook_url = result
                        success_count += 1
                        break
                    elif result == "invalid_token":
                        invalid_tokens.append(token)
                    elif result in ["forbidden", "limit"]:
                        fail_count += 1
            else:
                result = await create_webhook_worker(session, token, channel_id, name, None)
                if result and result not in ["invalid_token", "forbidden", "limit"]:
                    webhook_url = result
                    success_count += 1
                    break
                elif result == "invalid_token":
                    invalid_tokens.append(token)
                elif result in ["forbidden", "limit"]:
                    fail_count += 1
        if webhook_url:
            created_webhooks.append(webhook_url)
    print(f"\n{'='*50}")
    print("Webhook作成結果")
    print(f"{'='*50}")
    log_success(f"成功: {success_count} / 作成済みWebhook: {len(created_webhooks)}")
    log_error(f"失敗: {fail_count}")
    if invalid_tokens:
        log_error(f"無効トークン: {len(invalid_tokens)}個")
    if send_messages and created_webhooks and message_content:
        log_success(f"Webhookメッセージ送信を開始します...")
        print()
        msg_success = 0
        for webhook_url in created_webhooks:
            for _ in range(send_count):
                result = await send_webhook_message(webhook_url, message_content)
                if result:
                    msg_success += 1
                    log_success(f"Webhook送信成功")
                else:
                    log_error(f"Webhook送信失敗")
        print(f"\n{'='*50}")
        print("Webhook送信結果")
        print(f"{'='*50}")
        log_success(f"送信成功: {msg_success}")
