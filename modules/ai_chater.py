import asyncio
import random
import time
from utils import log_success, log_error, log_warning, log_info, get_modern_headers, create_ja3_connector, gemini_chat
import aiohttp

async def ai_send_message(session, token, channel_id, content, ja3_profile=None):
    """AI生成メッセージを送信"""
    masked_token = f"{token[:10]}***"
    headers = get_modern_headers(token, ja3_profile)
    url = f"https://discord.com/api/v9/channels/{channel_id}/messages"
    payload = {"content": content}
    try:
        async with session.post(url, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=15)) as res:
            if res.status in [200, 201]:
                log_success(f"AI送信成功 {masked_token}: {content[:50]}...")
                return True
            elif res.status == 429:
                retry_after = (await res.json()).get("retry_after", 1)
                log_warning(f"AIレート制限: {retry_after}秒 {masked_token}")
                await asyncio.sleep(retry_after)
                return False
            elif res.status == 401:
                log_error(f"AI無効トークン {masked_token}")
                return "invalid"
            else:
                log_error(f"AI送信失敗 {masked_token} (Status: {res.status})")
                return False
    except Exception as e:
        log_error(f"AI送信エラー {masked_token}: {e}")
        return False

async def ai_chater_worker(session, token, channel_id, language, topic, ja3_profile=None, stop_event=None):
    """AI Chaterワーカー - 高速でAI生成メッセージを送信し続ける"""
    masked_token = f"{token[:10]}***"
    log_success(f"AI Chater開始 {masked_token} → Channel: {channel_id} | Lang: {language} | Topic: {topic}")

    prompts = [
        f"Tell me about {topic}",
        f"What do you think about {topic}?",
        f"I love {topic}!",
        f"Anyone here likes {topic}?",
        f"{topic} is amazing",
        f"What's your favorite thing about {topic}?",
        f"I just learned about {topic}",
        f"{topic} changed my life",
        f"Can't stop thinking about {topic}",
        f"Who else is into {topic}?",
    ]

    while True:
        if stop_event and stop_event.is_set():
            log_info(f"AI Chater停止 {masked_token}")
            break

        prompt = random.choice(prompts)
        ai_response = await gemini_chat(prompt, language, topic)

        if ai_response:
            result = await ai_send_message(session, token, channel_id, ai_response, ja3_profile)
            if result == "invalid":
                break
            await asyncio.sleep(random.uniform(0.5, 1.5))
        else:
            log_warning(f"AI応答生成失敗 {masked_token}")
            await asyncio.sleep(2)

async def ai_chater_menu(session, tokens):
    """AI Chaterメニュー"""
    from utils import select_ja3_profile, load_proxies
    print(f"\n{'='*50}")
    print("Discord AI Chater")
    print(f"{'='*50}")

    channel_id = input("チャンネルIDを入力: ").strip()
    if not channel_id:
        log_error("チャンネルIDが入力されていません。")
        return

    language = input("話す言語を入力 (ja/en/ko/zh/etc): ").strip() or "ja"
    topic = input("話すトピックを入力: ").strip() or "日常"

    print(f"\n{Fore.CYAN}設定確認:{Style.RESET_ALL}")
    print(f"  チャンネル: {channel_id}")
    print(f"  言語: {language}")
    print(f"  トピック: {topic}")
    print(f"  送信間隔: 0.5〜1.5秒（高速）")
    print(f"\n{Fore.YELLOW}Enterを押すと開始します。Ctrl+Cで停止。{Style.RESET_ALL}")
    input()

    selected_profiles = select_ja3_profile()
    use_proxy = input("プロキシを使用しますか？ (y/n): ").lower() == 'y'
    proxies = load_proxies() if use_proxy else []
    if proxies:
        log_success(f"{len(proxies)}個のプロキシを読み込みました。")

    log_success(f"AI Chaterを開始します...")
    print()

    stop_event = asyncio.Event()

    tasks = []
    sessions = []

    for token in tokens:
        ja3_profile = random.choice(selected_profiles) if selected_profiles and len(selected_profiles) > 1 else (selected_profiles[0] if selected_profiles else None)
        proxy_url = None
        if proxies:
            proxy = random.choice(proxies)
            proxy_url = f"http://{proxy}" if not proxy.startswith("http") else proxy

        connector = create_ja3_connector(ja3_profile, proxy_url)
        worker_session = aiohttp.ClientSession(connector=connector)
        sessions.append(worker_session)

        task = asyncio.create_task(
            ai_chater_worker(worker_session, token, channel_id, language, topic, ja3_profile, stop_event)
        )
        tasks.append(task)

    try:
        await asyncio.gather(*tasks)
    except KeyboardInterrupt:
        log_info("AI Chater停止中...")
        stop_event.set()
    finally:
        for s in sessions:
            await s.close()

    log_success("AI Chaterを終了しました。")
