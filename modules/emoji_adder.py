import asyncio
import random
import base64
from utils import log_success, log_error, log_warning, log_info, get_modern_headers, create_ja3_connector, generate_random_string
import aiohttp

async def add_emoji_worker(session, token, guild_id, emoji_name, emoji_data, ja3_profile=None):
    masked_token = f"{token[:10]}***"
    headers = get_modern_headers(token, ja3_profile)
    url = f"https://discord.com/api/v9/guilds/{guild_id}/emojis"
    payload = {
        "name": emoji_name,
        "image": emoji_data,
        "roles": []
    }
    try:
        async with session.post(url, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=15)) as res:
            if res.status in [200, 201]:
                log_success(f"絵文字追加成功 {masked_token} → :{emoji_name}:")
                return True
            elif res.status == 429:
                retry_after = (await res.json()).get("retry_after", 60)
                log_warning(f"絵文字レート制限: {retry_after}秒待機 {masked_token}")
                await asyncio.sleep(retry_after)
                return False
            elif res.status == 401:
                log_error(f"絵文字無効なトークン {masked_token}")
                return "invalid_token"
            elif res.status == 403:
                log_error(f"絵文字追加禁止（権限不足） {masked_token}")
                return "forbidden"
            elif res.status == 400:
                log_error(f"絵文字追加失敗（上限等） {masked_token}")
                return "limit"
            else:
                log_error(f"絵文字追加失敗 {masked_token} (Status: {res.status})")
                return False
    except Exception as e:
        log_error(f"絵文字エラー {masked_token}: {e}")
        return False

async def emoji_adder_menu(session, tokens):
    print(f"\n{'='*50}")
    print("Discord Emoji Adder")
    print(f"{'='*50}")
    guild_id = input("サーバーIDを入力: ").strip()
    if not guild_id:
        log_error("サーバーIDが入力されていません。")
        return
    emoji_name = input("絵文字名を入力（英数字のみ）: ")
    emoji_source = input("絵文字画像のパスまたはURLを入力: ").strip()
    if not emoji_source:
        log_error("絵文字ソースが入力されていません。")
        return
    emoji_data = None
    if emoji_source.startswith("http"):
        try:
            async with session.get(emoji_source) as res:
                if res.status == 200:
                    image_bytes = await res.read()
                    ext = emoji_source.split(".")[-1].split("?")[0] if "." in emoji_source else "png"
                    emoji_data = f"data:image/{ext};base64," + base64.b64encode(image_bytes).decode()
        except Exception as e:
            log_error(f"絵文字ダウンロード失敗: {e}")
            return
    else:
        try:
            with open(emoji_source, "rb") as f:
                image_bytes = f.read()
            ext = emoji_source.split(".")[-1] if "." in emoji_source else "png"
            emoji_data = f"data:image/{ext};base64," + base64.b64encode(image_bytes).decode()
        except Exception as e:
            log_error(f"絵文字ファイル読み込み失敗: {e}")
            return
    if not emoji_data:
        log_error("絵文字データの準備に失敗しました。")
        return
    from utils import select_ja3_profile, load_proxies
    selected_profiles = select_ja3_profile()
    use_proxy = input("プロキシを使用しますか？ (y/n): ").lower() == 'y'
    proxies = load_proxies() if use_proxy else []
    if proxies:
        log_success(f"{len(proxies)}個のプロキシを読み込みました。")
    log_success(f"絵文字追加を開始します... (Guild: {guild_id})")
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
                result = await add_emoji_worker(ja3_session, token, guild_id, emoji_name, emoji_data, ja3_profile)
                if result == True:
                    success_count += 1
                elif result == "invalid_token":
                    invalid_tokens.append(token); fail_count += 1
                elif result == "forbidden":
                    fail_count += 1
                elif result == "limit":
                    fail_count += 1
                else:
                    fail_count += 1
        else:
            result = await add_emoji_worker(session, token, guild_id, emoji_name, emoji_data, None)
            if result == True:
                success_count += 1
            elif result == "invalid_token":
                invalid_tokens.append(token); fail_count += 1
            elif result == "forbidden":
                fail_count += 1
            elif result == "limit":
                fail_count += 1
            else:
                fail_count += 1
    print(f"\n{'='*50}")
    print("絵文字追加結果サマリー")
    print(f"{'='*50}")
    log_success(f"成功: {success_count}")
    log_error(f"失敗: {fail_count}")
    if invalid_tokens:
        log_error(f"無効トークン: {len(invalid_tokens)}個")
