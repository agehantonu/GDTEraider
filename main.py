import os
import asyncio
from colorama import init, Fore, Style
from utils import clear_screen, log_success, log_error
from modules.joiner import joiner_menu
from modules.leaver import leaver_menu
from modules.vc_joiner import vc_joiner_menu
from modules.vc_leaver import vc_leaver_menu
from modules.messenger import messenger_menu
from modules.replyer import replyer_menu
from modules.dm_tool import dm_tool_menu
from modules.typer import typer_menu
from modules.onliner import onliner_menu
from modules.event_creator import event_creator_menu
from modules.emoji_adder import emoji_adder_menu
from modules.webhook_tool import webhook_tool_menu
from modules.reaction_tool import reaction_tool_menu
from modules.ai_chater import ai_chater_menu
from modules.button_clicker import button_clicker_menu
from modules.onboarding import onboarding_menu

init(autoreset=True)

ASCII_ART = f"""
{Fore.RED}  ________ ________ __________ _________
 /  _____/ \______ \\\\__   ___/ \_   ___ \\
/   \  ___  |    |  \\ |   |    /    \  \/
\    \_\  \ |    `   \|   |    \     \____
 \______  //_______  /|___|     \______  /
        \/         \/                  \/ {Style.RESET_ALL}
{Fore.GREEN}[+] dev discord - mse4{Style.RESET_ALL}
{Fore.GREEN}[+] discord server https://discord.gg/TbkZR5fhUs{Style.RESET_ALL}
"""

def print_red_box_menu():
  
    menu_items = [
        "[1] Message Spammer",
        "[2] Reply Spammer",
        "[3] DM Spammer",
        "[4] Server Joiner",
        "[5] Server Leaver",
        "[6] VC Joiner",
        "[7] VC Leaver",
        "[8] Typing Indicator",
        "[9] Online Status Keeper",
        "[10] Event Creator",
        "[11] Emoji Adder",
        "[12] Webhook Mass Creator + Spammer",
        "[13] Reaction Adder",
        "[14] Button Clicker",
        "[15] AI Chater (Gemini)",
        "[16] OnBoarding Bypass",
        "[17] Exit",
    ]

    max_len = max(len(item) for item in menu_items)
    box_width = max_len + 4

    red = Fore.RED
    reset = Style.RESET_ALL

    top_border = f"{red}╔{'═' * box_width}╗{reset}"
    bottom_border = f"{red}╚{'═' * box_width}╝{reset}"

    print(f"\n{red}{' ' * 15}SELECT MODULE{' ' * 15}{reset}")
    print(top_border)

    for item in menu_items:
        padding = box_width - len(item) - 2
        line = f"{red}║{reset} {item}{' ' * padding} {red}║{reset}"
        print(line)

    print(bottom_border)
    print()

async def main():
    clear_screen()
    print(ASCII_ART)
    print_red_box_menu()

    choice = input(f"{Fore.RED}[>]{Style.RESET_ALL} Select > ")

    if choice == "17":
        log_error("Exiting...")
        return

    if not os.path.exists("tokens.txt"):
        log_error("tokens.txt not found.")
        return

    with open("tokens.txt", "r", encoding="utf-8") as f:
        tokens = [line.strip() for line in f if line.strip()]

    if not tokens:
        log_error("No tokens found in tokens.txt.")
        return

    if choice in ["8", "9"]:
        if choice == "8":
            await typer_menu(tokens)
        else:
            await onliner_menu(tokens)
    else:
        from utils import create_ja3_connector
        import aiohttp
        connector = create_ja3_connector()
        async with aiohttp.ClientSession(connector=connector) as session:
            if choice == "1":
                await messenger_menu(session, tokens)
            elif choice == "2":
                await replyer_menu(session, tokens)
            elif choice == "3":
                await dm_tool_menu(session, tokens)
            elif choice == "4":
                await joiner_menu(session, tokens)
            elif choice == "5":
                await leaver_menu(session, tokens)
            elif choice == "6":
                await vc_joiner_menu(session, tokens)
            elif choice == "7":
                await vc_leaver_menu(session, tokens)
            elif choice == "10":
                await event_creator_menu(session, tokens)
            elif choice == "11":
                await emoji_adder_menu(session, tokens)
            elif choice == "12":
                await webhook_tool_menu(session, tokens)
            elif choice == "13":
                await reaction_tool_menu(session, tokens)
            elif choice == "14":
                await button_clicker_menu(session, tokens)
            elif choice == "15":
                await ai_chater_menu(session, tokens)
            elif choice == "16":
                await onboarding_menu(session, tokens)
            else:
                log_error("Invalid selection.")

    log_success("All operations completed.")

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
