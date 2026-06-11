import asyncio
import random
from utils import log_success, log_error, log_warning, log_info, get_modern_headers, create_ja3_connector
import aiohttp

async def get_invite_info(session, invite_code):
    url = f"https://discord.com/api/v9/invites/{invite_code}?with_counts=true&with_expiration=true"
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as res:
            if res.status == 200:
                return await res.json()
    except Exception as e:
        log_error(f"招待情報取得エラー: {e}")
    return None

async def join_server_worker(session, token, invite_code, guild_id=None, ja3_profile=None):
    masked_token = f"{token[:10]}***"
    headers = get_modern_headers(token, ja3_profile)
    url = f"https://discord.com/api/v9/invites/{invite_code}"
    payload = {"session_id": __import__('utils').generate_random_string(32)}
    try:
        async with session.post(url, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=15)) as res:
            if res.status in [200, 201]:
                data = await res.json()
                guild_name = data.get("guild", {}).get("name", "Unknown")
                log_success(f"参加成功 {masked_token} → {guild_name}")
                return True
            elif res.status == 429:
                retry_after = (await res.json()).get("retry_after", 60)
                log_warning(f"レート制限: {retry_after}秒待機 {masked_token}")
                await asyncio.sleep(retry_after)
                return False
            elif res.status == 401:
                log_error(f"無効なトークン {masked_token}")
                return "invalid_token"
            elif res.status == 403:
                log_error(f"参加禁止（BAN/制限） {masked_token}")
                return "banned"
            elif res.status == 400:
                data = await res.json()
                if data.get("captcha_key"):
                    log_warning(f"CAPTCHA検出 {masked_token}")
                    return "captcha"
                log_error(f"参加失敗 (400) {masked_token}")
                return False
            else:
                log_error(f"参加失敗 {masked_token} (Status: {res.status})")
                return False
    except Exception as e:
        log_error(f"エラー {masked_token}: {e}")
        return False

async def accept_terms_of_service(session, token, guild_id):
    headers = get_modern_headers(token)
    url = f"https://discord.com/api/v9/guilds/{guild_id}/requests/@me"
    try:
        async with session.put(url, headers=headers, json={"version": "2023-11-01"}) as res:
            return res.status in [200, 201, 204]
    except Exception:
        return False

async def joiner_menu(session, tokens):
    print(f"\n{'='*50}")
    print("Discord Server Joiner")
    print(f"{'='*50}")
    invite_input = input("招待リンクまたはコードを入力 (複数はカンマ区切り): ").strip()
    invites = [i.strip().replace("https://discord.gg/", "").replace("https://discord.com/invite/", "") for i in invite_input.split(",") if i.strip()]
    if not invites:
        log_error("有効な招待コードがありません。")
        return
    from utils import select_ja3_profile, load_proxies
    selected_profiles = select_ja3_profile()
    use_proxy = input("プロキシを使用しますか？ (y/n): ").lower() == 'y'
    proxies = load_proxies() if use_proxy else []
    if proxies:
        log_success(f"{len(proxies)}個のプロキシを読み込みました。")
    max_retries = int(input("最大リトライ回数 (デフォルト 3): ") or "3")
    log_info("参加間隔は自動で2.0000〜4.0000秒のランダムに設定されます。")
    bypass_verification = input("メンバーバーフィケーションをバイパスしますか？ (y/n): ").lower() == 'y'
    log_success("サーバー参加を開始します...")
    print()
    success_count, fail_count, invalid_tokens = 0, 0, []
    for invite_code in invites:
        log_info(f"招待コード: {invite_code} を処理中...")
        invite_info = await get_invite_info(session, invite_code)
        if invite_info:
            guild_name = invite_info.get("guild", {}).get("name", "Unknown")
            guild_id = invite_info.get("guild", {}).get("id")
            log_info(f"サーバー名: {guild_name} | 現在のメンバー: {invite_info.get('approximate_member_count', '?')}")
        else:
            guild_id = None
            log_warning("招待情報の取得に失敗しました。続行します...")
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
                        result = await join_server_worker(ja3_session, token, invite_code, guild_id, ja3_profile)
                        if result == True:
                            success_count += 1
                            if bypass_verification and guild_id:
                                await accept_terms_of_service(ja3_session, token, guild_id)
                            break
                        elif result == "invalid_token":
                            invalid_tokens.append(token); fail_count += 1; break
                        elif result == "banned":
                            fail_count += 1; break
                        elif result == "captcha":
                            await asyncio.sleep(5); continue
                        elif attempt < max_retries - 1:
                            await asyncio.sleep(2 ** attempt)
                        else:
                            fail_count += 1
            else:
                for attempt in range(max_retries):
                    result = await join_server_worker(session, token, invite_code, guild_id, None)
                    if result == True:
                        success_count += 1
                        if bypass_verification and guild_id:
                            await accept_terms_of_service(session, token, guild_id)
                        break
                    elif result == "invalid_token":
                        invalid_tokens.append(token); fail_count += 1; break
                    elif result == "banned":
                        fail_count += 1; break
                    elif result == "captcha":
                        await asyncio.sleep(5); continue
                    elif attempt < max_retries - 1:
                        await asyncio.sleep(2 ** attempt)
                    else:
                        fail_count += 1
            if i < len(tokens) - 1:
                delay = random.uniform(2.0000, 4.0000)
                log_info(f"次の参加まで {delay:.4f}秒待機...")
                await asyncio.sleep(delay)
    print(f"\n{'='*50}")
    print("参加結果サマリー")
    print(f"{'='*50}")
    log_success(f"成功: {success_count}")
    log_error(f"失敗: {fail_count}")
    if invalid_tokens:
        log_error(f"無効トークン: {len(invalid_tokens)}個")
        with open("invalid_tokens.txt", "w", encoding="utf-8") as f:
            for t in invalid_tokens:
                f.write(t + "\n")
        log_warning("無効トークンを invalid_tokens.txt に保存しました。")
