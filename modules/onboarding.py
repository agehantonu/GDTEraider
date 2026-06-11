import asyncio
import random
import json
from utils import log_success, log_error, log_warning, log_info, get_modern_headers, create_ja3_connector, generate_random_string
import aiohttp

async def get_onboarding_questions(session, token, guild_id, ja3_profile=None):
    """サーバーのOnBoarding質問を取得"""
    masked_token = f"{token[:10]}***"
    headers = get_modern_headers(token, ja3_profile)
    url = f"https://discord.com/api/v9/guilds/{guild_id}/onboarding"
    try:
        async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as res:
            if res.status == 200:
                data = await res.json()
                return data
            elif res.status == 401:
                log_error(f"OnBoarding無効トークン {masked_token}")
                return "invalid_token"
            elif res.status == 403:
                log_error(f"OnBoarding取得禁止 {masked_token}")
                return "forbidden"
            else:
                log_error(f"OnBoarding取得失敗 {masked_token} (Status: {res.status})")
                return None
    except Exception as e:
        log_error(f"OnBoarding取得エラー {masked_token}: {e}")
        return None

async def submit_onboarding_answer(session, token, guild_id, answers, ja3_profile=None):
    """OnBoarding回答を送信"""
    masked_token = f"{token[:10]}***"
    headers = get_modern_headers(token, ja3_profile)
    url = f"https://discord.com/api/v9/guilds/{guild_id}/onboarding-responses"

    payload = {
        "answers": answers,
        "version": "1"
    }

    try:
        async with session.put(url, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=15)) as res:
            if res.status in [200, 201, 204]:
                log_success(f"突破成功 {masked_token}")
                return True
            elif res.status == 429:
                retry_after = (await res.json()).get("retry_after", 60)
                log_warning(f"OnBoardingレート制限: {retry_after}秒 {masked_token}")
                await asyncio.sleep(retry_after)
                return False
            elif res.status == 401:
                log_error(f"突破無効トークン {masked_token}")
                return "invalid_token"
            elif res.status == 403:
                log_error(f"突破禁止 {masked_token}")
                return "forbidden"
            elif res.status == 400:
                log_error(f"突破失敗（回答不正） {masked_token}")
                return "bad_answer"
            else:
                log_error(f"突破失敗 {masked_token} (Status: {res.status})")
                return False
    except Exception as e:
        log_error(f"突破エラー {masked_token}: {e}")
        return False

def display_questions(questions_data):
    """質問を表示して回答を取得"""
    prompts = questions_data.get("prompts", [])
    if not prompts:
        log_error("OnBoarding質問が見つかりません。")
        return None

    answers = []
    for prompt in prompts:
        question = prompt.get("title", "質問")
        options = prompt.get("options", [])
        prompt_id = prompt.get("id")

        print(f"\n{question}")
        for i, option in enumerate(options, 1):
            print(f"  {i}: {option.get('title', '選択肢')}")

        while True:
            choice = input("> ").strip()
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(options):
                    selected_option = options[idx]
                    answers.append({
                        "prompt_id": prompt_id,
                        "options": [selected_option.get("id")]
                    })
                    break
                else:
                    print("無効な選択です。もう一度入力してください。")
            except ValueError:
                print("数字を入力してください。")

    return answers

async def onboarding_menu(session, tokens):
    """OnBoardingメニュー"""
    from utils import select_ja3_profile, load_proxies
    print(f"\n{'='*50}")
    print("Discord OnBoarding Breaker")
    print(f"{'='*50}")

    invite_code = input("招待コードを入力 (discord.gg/xxx): ").strip()
    if not invite_code:
        log_error("招待コードが入力されていません。")
        return

    invite_url = f"https://discord.com/api/v9/invites/{invite_code.replace('https://discord.gg/', '').replace('discord.gg/', '')}"
    guild_id = None

    try:
        async with session.get(invite_url) as res:
            if res.status == 200:
                invite_data = await res.json()
                guild_id = invite_data.get("guild", {}).get("id")
                guild_name = invite_data.get("guild", {}).get("name", "Unknown")
                log_success(f"サーバー情報取得: {guild_name} (ID: {guild_id})")
            else:
                log_error("招待コードが無効です。")
                return
    except Exception as e:
        log_error(f"招待情報取得エラー: {e}")
        return

    if not guild_id:
        log_error("サーバーIDを取得できませんでした。")
        return

    log_info("サーバーに参加します...")
    join_url = f"https://discord.com/api/v9/invites/{invite_code.replace('https://discord.gg/', '').replace('discord.gg/', '')}"

    for token in tokens:
        headers = get_modern_headers(token)
        try:
            async with session.post(join_url, headers=headers, json={"session_id": generate_random_string(32)}) as res:
                if res.status in [200, 201]:
                    log_success(f"サーバー参加成功")
                elif res.status == 429:
                    retry_after = (await res.json()).get("retry_after", 60)
                    await asyncio.sleep(retry_after)
                elif res.status == 400:
                    data = await res.json()
                    if data.get("captcha_key"):
                        log_warning(f"CAPTCHA検出 - ソルバー設定を確認してください")
                else:
                    log_error(f"サーバー参加失敗 (Status: {res.status})")
        except Exception as e:
            log_error(f"サーバー参加エラー: {e}")

    log_info("OnBoarding質問を取得中...")
    questions_data = None
    for token in tokens:
        result = await get_onboarding_questions(session, token, guild_id)
        if result and result not in ["invalid_token", "forbidden"]:
            questions_data = result
            break
        elif result == "invalid_token":
            continue

    if not questions_data:
        log_error("OnBoarding質問を取得できませんでした。")
        return

    answers = display_questions(questions_data)
    if not answers:
        log_error("回答が取得できませんでした。")
        return

    print(f"\n{Fore.GREEN}回答を送信して突破します...{Style.RESET_ALL}")

    selected_profiles = select_ja3_profile()
    use_proxy = input("プロキシを使用しますか？ (y/n): ").lower() == 'y'
    proxies = load_proxies() if use_proxy else []
    if proxies:
        log_success(f"{len(proxies)}個のプロキシを読み込みました。")

    log_success(f"OnBoarding突破を開始します... (Guild: {guild_id})")
    print()

    success_count, fail_count, invalid_tokens = 0, 0, []

    for token in tokens:
        ja3_profile = random.choice(selected_profiles) if selected_profiles and len(selected_profiles) > 1 else (selected_profiles[0] if selected_profiles else None)
        proxy_url = None
        if proxies:
            proxy = random.choice(proxies)
            proxy_url = f"http://{proxy}" if not proxy.startswith("http") else proxy

        if ja3_profile or proxy_url:
            connector = create_ja3_connector(ja3_profile, proxy_url)
            async with aiohttp.ClientSession(connector=connector) as ja3_session:
                result = await submit_onboarding_answer(ja3_session, token, guild_id, answers, ja3_profile)
                if result == True:
                    success_count += 1
                elif result == "invalid_token":
                    invalid_tokens.append(token); fail_count += 1
                elif result == "forbidden":
                    fail_count += 1
                elif result == "bad_answer":
                    fail_count += 1
                else:
                    fail_count += 1
        else:
            result = await submit_onboarding_answer(session, token, guild_id, answers, None)
            if result == True:
                success_count += 1
            elif result == "invalid_token":
                invalid_tokens.append(token); fail_count += 1
            elif result == "forbidden":
                fail_count += 1
            elif result == "bad_answer":
                fail_count += 1
            else:
                fail_count += 1

    print(f"\n{'='*50}")
    print("OnBoarding突破結果サマリー")
    print(f"{'='*50}")
    log_success(f"突破成功: {success_count}")
    log_error(f"突破失敗: {fail_count}")
    if invalid_tokens:
        log_error(f"無効トークン: {len(invalid_tokens)}個")
