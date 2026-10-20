# Public template: configure Discord IDs, account details, preferences, and schedules before use.
import discum
import json
import time
import random
import requests
import os

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from urllib.parse import quote


# ============================================================
# SHARED CONFIGURATION
# ============================================================

# Discord / Mudae
CHANNEL_ID = "YOUR_DISCORD_CHANNEL_ID"
SERVER_ID = "YOUR_DISCORD_SERVER_ID"

MUDAE_BOT_ID = "432610292342587392"


# ------------------------------------------------------------
# UTC SCHEDULING
# ------------------------------------------------------------

ROLL_TIMEZONE = ZoneInfo("UTC")

# Each hourly cycle starts at a random minute in this range.
ROLL_WINDOW_START = 1
ROLL_WINDOW_END = 4

# Delay between accounts that actually roll.
MIN_ACCOUNT_DELAY_SECONDS = 120     # 2 minutes
MAX_ACCOUNT_DELAY_SECONDS = 300     # 5 minutes


# ------------------------------------------------------------
# CLAIM RESET
# ------------------------------------------------------------

CLAIM_INTERVAL_HOURS = 3

# Configure the Mudae claim reset anchor for your server:
# Example: 00:00, 03:00, 06:00, 09:00, etc.
CLAIM_RESET_HOUR = 0
CLAIM_RESET_MINUTE = 0


# ------------------------------------------------------------
# ROLLS
# ------------------------------------------------------------

ROLLS_PER_ACCOUNT = 12

ROLL_DELAY_SECONDS = 1.8


# ------------------------------------------------------------
# SHARED DESIRED CHARACTERS
# ------------------------------------------------------------

desiredCharacters = [
    # Add character names here.
]


desiredSeries = [
    # Add series names here.
]


# ------------------------------------------------------------
# KAKERA SETTINGS
# ------------------------------------------------------------

soulmateKakeras = [
    "kakeraP",
    "kakeraR",
    "kakeraW",
    "kakeraL",
]

anycardKakeras = [
    "kakeraP",
    "kakeraW",
    "kakeraL",
]


# ============================================================
# ACCOUNT CONFIGURATION
# ============================================================
#
# startHour and endHour are in UTC.
#
# IMPORTANT:
# endHour is EXCLUSIVE.
#
# Example:
#
#     startHour = 6
#     endHour = 21
#
# means:
#
#     ON:  6:00 AM - 8:59 PM
#     OFF: 9:00 PM - 5:59 AM
#
# If you want the account to roll during the 9 PM hour:
#
#     endHour = 22
#
# Different accounts can have completely different schedules.
# ============================================================


ACCOUNTS = [
    # Replace these placeholders before running. Add accounts as needed.
    {
        "name": "Account 1",
        "username": "YOUR_DISCORD_USERNAME",
        "token": "YOUR_DISCORD_TOKEN",
        "rollCommand": "wa",
        "startHour": 0,
        "endHour": 24,
    },
]


# ============================================================
# CLAIM STATE STORAGE
# ============================================================

STATE_FILE = "public_claim_state.json"


def load_claim_state():

    if not os.path.exists(STATE_FILE):
        return {}

    try:

        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

    except Exception as e:

        print(f"Could not load claim state: {e}")

        return {}


def save_claim_state():

    data = {}

    for account in ACCOUNTS:

        last_claim = account.get("lastClaimTime")

        if last_claim is not None:

            data[account["name"]] = last_claim.isoformat()

        else:

            data[account["name"]] = None

    try:

        with open(STATE_FILE, "w", encoding="utf-8") as f:

            json.dump(
                data,
                f,
                indent=4
            )

    except Exception as e:

        print(f"Could not save claim state: {e}")


def initialize_claim_state():

    saved_state = load_claim_state()

    for account in ACCOUNTS:

        stored = saved_state.get(account["name"])

        if stored:

            try:

                account["lastClaimTime"] = datetime.fromisoformat(stored)

            except Exception:

                account["lastClaimTime"] = None

        else:

            account["lastClaimTime"] = None


# ============================================================
# CREATE ACCOUNT CLIENTS
# ============================================================

def initialize_accounts():

    for account in ACCOUNTS:

        account["auth"] = {
            "authorization": account["token"]
        }

        account["bot"] = discum.Client(
            token=account["token"],
            log=False
        )

        account["url"] = (
            f"https://discord.com/api/v8/channels/"
            f"{CHANNEL_ID}/messages"
        )


# ============================================================
# UTC / ACCOUNT SCHEDULE
# ============================================================

def hour_is_allowed(account, hour):

    start = account["startHour"]
    end = account["endHour"]

    # Normal schedule:
    # Example: 6 AM -> 9 PM
    if start < end:

        return start <= hour < end

    # Schedule crosses midnight:
    # Example: 6 PM -> 2 AM
    else:

        return hour >= start or hour < end


def account_is_on_shift(account):

    now = datetime.now(ROLL_TIMEZONE)

    return hour_is_allowed(
        account,
        now.hour
    )


# ============================================================
# CLAIM RESET LOGIC
# ============================================================

def get_next_claim_reset(after_time):

    reset = after_time.replace(
        hour=CLAIM_RESET_HOUR,
        minute=CLAIM_RESET_MINUTE,
        second=0,
        microsecond=0
    )

    interval = timedelta(
        hours=CLAIM_INTERVAL_HOURS
    )

    while reset - interval > after_time:

        reset -= interval

    while reset <= after_time:

        reset += interval

    return reset


def claim_available(account):

    last_claim = account.get("lastClaimTime")

    if last_claim is None:

        return True

    now = datetime.now()

    next_reset = get_next_claim_reset(
        last_claim
    )

    if now >= next_reset:

        return True

    remaining = next_reset - now

    print(
        f"[{account['name']}] "
        f"No claim available. "
        f"Next reset at "
        f"{next_reset.strftime('%I:%M:%S %p')} "
        f"({remaining} remaining)"
    )

    return False


# ============================================================
# DISCORD MESSAGE HELPERS
# ============================================================

def get_messages(account):

    try:

        response = requests.get(
            account["url"],
            headers=account["auth"],
            timeout=10
        )

        return response.json()

    except Exception as e:

        print(
            f"[{account['name']}] "
            f"Error retrieving messages: {e}"
        )

        return []


# ============================================================
# REAL ROLL VALIDATION
# ============================================================

def has_claim_button(msg):
    """
    Returns True if the Mudae message contains
    a heart-style claim button.
    """

    claim_hearts = (
        "❤️",
        "♥️",
        "💓",
        "💖",
        "💘",
        "💝",
        "🩷",
        "💗",
        "❣️",
        "❤️‍🔥",
        "💞",
        "💕",
        "💟",
        "❤️‍🩹",
    )

    for row in msg.get("components", []):

        for component in row.get("components", []):

            if component.get("type") != 2:
                continue

            emoji_data = component.get("emoji") or {}
            emoji_name = emoji_data.get("name")

            if emoji_name in claim_hearts:
                return True

    return False

def is_real_roll(msg):
    """
    Determine whether a Mudae message is an actual
    character roll rather than something like $im.
    """

    # Must come from Mudae
    if msg.get("author", {}).get("id") != MUDAE_BOT_ID:
        return False

    embeds = msg.get("embeds")

    if not embeds:
        return False

    embed = embeds[0]

    description = embed.get("description", "")
    character_name = embed.get("author", {}).get("name")
    image = embed.get("image")

    # A character roll should have a character name.
    if not character_name:
        return False

    # A character roll should have a character image.
    if not image:
        return False

    # ------------------------------------------------
    # Reject obvious informational / $im responses
    # ------------------------------------------------

    lookup_markers = (
        "Claim Rank",
        "Like Rank",
    )

    for marker in lookup_markers:
        if marker.lower() in description.lower():
            return False

    # ------------------------------------------------
    # Valid roll type 1:
    # Reaction-style Mudae roll
    # ------------------------------------------------

    if "react with any emoji to claim!" in description.lower():
        return True

    # ------------------------------------------------
    # Valid roll type 2:
    # Button-style Mudae roll
    # ------------------------------------------------

    if has_claim_button(msg):
        return True

    return False


# ============================================================
# WAIT FOR THE ROLL WE JUST REQUESTED
# ============================================================

def wait_for_roll_response(
    account,
    command_message_id,
    timeout=5
):

    """
    Wait for a genuine Mudae roll that appeared AFTER
    our roll command.

    This is safer than blindly using jsonCard[0].
    """

    start = time.time()

    while time.time() - start < timeout:

        messages = get_messages(account)

        valid_rolls = []

        for msg in messages:

            try:

                msg_id = int(msg["id"])

            except Exception:

                continue

            # Ignore anything older than our command
            if msg_id <= int(command_message_id):

                continue

            if not is_real_roll(msg):

                continue

            valid_rolls.append(msg)

        if valid_rolls:

            # Discord IDs increase over time.
            # Pick the earliest valid roll after our command.
            valid_rolls.sort(
                key=lambda x: int(x["id"])
            )

            return valid_rolls[0]

        time.sleep(0.25)

    return None


# ============================================================
# SEND ROLL COMMAND
# ============================================================

def send_roll(account):

    try:

        response = requests.post(
            url=account["url"],
            headers=account["auth"],
            data={
                "content":
                f"${account['rollCommand']}"
            },
            timeout=10
        )

        data = response.json()

        return data.get("id")

    except Exception as e:

        print(
            f"[{account['name']}] "
            f"Error sending roll: {e}"
        )

        return None


# ============================================================
# CLAIM BUTTON
# ============================================================

def click_claim_button(account, msg):

    components = msg.get("components")

    if not components:

        return False

    claim_hearts = (
        "❤️",
        "♥️",
        "💓",
        "💖",
        "💘",
        "💝",
        "🩷",
        "💗",
        "❣️",
        "❤️‍🔥",
        "💞",
        "💕",
        "💟",
        "❤️‍🩹",
    )

    try:

        for row in components:

            for component in row.get(
                "components",
                []
            ):

                if component.get("type") != 2:

                    continue

                emoji_data = (
                    component.get("emoji")
                    or {}
                )

                emoji_name = emoji_data.get(
                    "name"
                )

                if emoji_name in claim_hearts:

                    account["bot"].click(

                        msg["author"]["id"],

                        channelID=msg["channel_id"],

                        guildID=SERVER_ID,

                        messageID=msg["id"],

                        messageFlags=msg.get(
                            "flags",
                            0
                        ),

                        data={
                            "component_type": 2,
                            "custom_id":
                            component["custom_id"]
                        }
                    )

                    print(
                        f"[{account['name']}] "
                        f"Claim button clicked"
                    )

                    return True

    except Exception as e:

        print(
            f"[{account['name']}] "
            f"Error clicking claim button: {e}"
        )

    return False


# ============================================================
# CLAIM CONFIRMATION
# ============================================================

def wait_for_claim_confirmation(
    account,
    roll_message_id,
    timeout=4
):

    start = time.time()

    username = account["username"].lower()

    while time.time() - start < timeout:

        messages = get_messages(account)

        for msg in messages:

            try:

                if int(msg["id"]) <= int(
                    roll_message_id
                ):

                    continue

            except Exception:

                continue

            if (
                msg.get("author", {}).get("id")
                != MUDAE_BOT_ID
            ):

                continue

            content = msg.get(
                "content",
                ""
            ).lower()

            if (
                username in content
                and "now married" in content
            ):

                print(
                    f"[{account['name']}] "
                    f"Marriage confirmation received"
                )

                return True

        time.sleep(0.5)

    print(
        f"[{account['name']}] "
        f"No claim confirmation detected"
    )

    return False


# ============================================================
# REACTION CLAIM FALLBACK
# ============================================================

def reaction_claim(account, message_id):

    """
    If there is no clickable claim button,
    attempt several claim reactions.

    Stops as soon as Mudae confirms the claim.
    """

    claim_emojis = [
        "❤️",
        "💖",
        "💗",
    ]

    for claim_emoji in claim_emojis:

        print(
            f"[{account['name']}] "
            f"Trying reaction {claim_emoji}"
        )

        encoded_emoji = quote(
            claim_emoji,
            safe=""
        )

        try:

            requests.put(

                (
                    f"https://discord.com/api/v8/"
                    f"channels/{CHANNEL_ID}/"
                    f"messages/{message_id}/"
                    f"reactions/{encoded_emoji}/@me"
                ),

                headers=account["auth"],

                timeout=10
            )

        except Exception as e:

            print(
                f"[{account['name']}] "
                f"Reaction error: {e}"
            )

        if wait_for_claim_confirmation(
            account,
            message_id,
            timeout=2
        ):

            return True

    return False


# ============================================================
# PROCESS CHARACTER
# ============================================================

def process_roll(account, msg):

    embed = msg["embeds"][0]

    try:

        card_name = (
            embed["author"]["name"]
        )

        description = embed.get(
            "description",
            ""
        )

        # Series is first line
        card_series = (
            description
            .split("\n")[0]
            .strip()
        )

    except Exception:

        return False

    content = msg.get(
        "content",
        ""
    ).lower()

    # Wished status is ONLY evaluated after
    # the message has already passed is_real_roll().
    is_wished = (
        "wished by" in content
    )

    print(
        f"[{account['name']}] "
        f"🤍 ---- "
        f"{card_name} - {card_series}"
    )

    should_claim = False

    if is_wished:

        should_claim = True

        print(
            f"[{account['name']}] "
            f"WISHED character found: "
            f"{card_name}"
        )

    elif card_name in desiredCharacters:

        should_claim = True

        print(
            f"[{account['name']}] "
            f"Desired character found: "
            f"{card_name}"
        )

    elif card_series in desiredSeries:

        should_claim = True

        print(
            f"[{account['name']}] "
            f"Desired series found: "
            f"{card_series}"
        )

    # --------------------------------------------------------
    # CLAIM
    # --------------------------------------------------------

    if should_claim:

        print(
            f"[{account['name']}] "
            f"Trying to claim {card_name}"
        )

        clicked = click_claim_button(
            account,
            msg
        )

        confirmed = False

        if clicked:

            confirmed = (
                wait_for_claim_confirmation(
                    account,
                    msg["id"]
                )
            )

        else:

            print(
                f"[{account['name']}] "
                f"No claim button found. "
                f"Trying reaction claims."
            )

            confirmed = reaction_claim(
                account,
                msg["id"]
            )

        if confirmed:

            account["lastClaimTime"] = (
                datetime.now()
            )

            save_claim_state()

            print(
                f"[{account['name']}] "
                f"CLAIM SUCCESSFUL."
            )

            return True

    # --------------------------------------------------------
    # KAKERA
    # --------------------------------------------------------

    handle_kakera(
        account,
        msg,
        embed
    )

    return False


# ============================================================
# KAKERA
# ============================================================

def handle_kakera(
    account,
    msg,
    embed
):

    if not msg.get("components"):

        return

    is_soulmate = (
        "chaoskey"
        in embed.get("description", "")
    )

    for row in msg["components"]:

        for component in row.get(
            "components",
            []
        ):

            try:

                kakera_name = (
                    component["emoji"]["name"]
                )

                soulmate_match = (
                    kakera_name
                    in soulmateKakeras
                    and is_soulmate
                )

                normal_match = (
                    kakera_name
                    in anycardKakeras
                )

                if (
                    soulmate_match
                    or normal_match
                ):

                    print(
                        f"[{account['name']}] "
                        f"💎 reacting to "
                        f"{kakera_name}"
                    )

                    account["bot"].click(

                        msg["author"]["id"],

                        channelID=msg[
                            "channel_id"
                        ],

                        guildID=SERVER_ID,

                        messageID=msg["id"],

                        messageFlags=msg.get(
                            "flags",
                            0
                        ),

                        data={
                            "component_type": 2,
                            "custom_id":
                            component[
                                "custom_id"
                            ]
                        }
                    )

                    time.sleep(0.5)

            except KeyError:

                pass


# ============================================================
# ROLL ONE ACCOUNT
# ============================================================

def roll_account(account):

    print()
    print("=" * 60)

    print(
        f"Starting rolls for "
        f"{account['name']}"
    )

    print(
        datetime.now(
            ROLL_TIMEZONE
        ).strftime(
            "UTC time: "
            "%I:%M:%S %p"
        )
    )

    print("=" * 60)

    for roll_number in range(
        1,
        ROLLS_PER_ACCOUNT + 1
    ):

        # Account may have claimed during
        # this rolling session.
        if not claim_available(account):

            print(
                f"[{account['name']}] "
                f"Claim unavailable. "
                f"Stopping this account."
            )

            break

        command_id = send_roll(
            account
        )

        if command_id is None:

            print(
                f"[{account['name']}] "
                f"Could not send roll."
            )

            continue

        msg = wait_for_roll_response(
            account,
            command_id
        )

        if msg is None:

            print(
                f"[{account['name']}] "
                f"Roll {roll_number}: "
                f"No valid Mudae roll detected."
            )

            continue

        print(
            f"[{account['name']}] "
            f"Roll "
            f"{roll_number}/"
            f"{ROLLS_PER_ACCOUNT}"
        )

        claimed = process_roll(
            account,
            msg
        )

        if claimed:

            print(
                f"[{account['name']}] "
                f"Stopping rolls after "
                f"successful claim."
            )

            break

        time.sleep(
            ROLL_DELAY_SECONDS
        )

    print(
        f"[{account['name']}] "
        f"Rolling session ended."
    )


# ============================================================
# DETERMINE ACCOUNT ELIGIBILITY
# ============================================================

def account_can_roll(account):

    if not account_is_on_shift(
        account
    ):

        print(
            f"[{account['name']}] "
            f"Outside account shift."
        )

        return False

    if not claim_available(
        account
    ):

        return False

    return True


# ============================================================
# RUN ONE HOURLY CYCLE
# ============================================================

def run_hourly_cycle():

    print()
    print("#" * 70)

    now = datetime.now(
        ROLL_TIMEZONE
    )

    print(
        "Starting hourly cycle at "
        + now.strftime(
            "%Y-%m-%d %I:%M:%S %p %Z"
        )
    )

    print("#" * 70)

    shuffled_accounts = (
        ACCOUNTS.copy()
    )

    random.shuffle(
        shuffled_accounts
    )

    print(
        "Random account order:"
    )

    for index, account in enumerate(
        shuffled_accounts,
        start=1
    ):

        print(
            f"  {index}. "
            f"{account['name']}"
        )

    accounts_that_rolled = 0

    for account in shuffled_accounts:

        if not account_can_roll(
            account
        ):

            continue

        # Delay only BETWEEN accounts
        # that actually roll.
        if accounts_that_rolled > 0:

            delay = random.randint(
                MIN_ACCOUNT_DELAY_SECONDS,
                MAX_ACCOUNT_DELAY_SECONDS
            )

            print()
            print(
                f"Waiting "
                f"{delay // 60}m "
                f"{delay % 60}s "
                f"before next account..."
            )

            time.sleep(delay)

            # Re-check because account state /
            # shift may have changed while waiting.
            if not account_can_roll(
                account
            ):

                continue

        roll_account(
            account
        )

        accounts_that_rolled += 1

    print()
    print(
        "Hourly cycle complete."
    )


# ============================================================
# NEXT HOURLY CYCLE
# ============================================================

def pick_next_cycle_time(now):

    next_hour = (
        now.replace(
            minute=0,
            second=0,
            microsecond=0
        )
        + timedelta(hours=1)
    )

    chosen_minute = random.randint(
        ROLL_WINDOW_START,
        ROLL_WINDOW_END
    )

    chosen_second = random.randint(
        2,
        25
    )

    return next_hour.replace(
        minute=chosen_minute,
        second=chosen_second
    )


# ============================================================
# MAIN LOOP
# ============================================================

def run_forever():

    initialize_claim_state()

    initialize_accounts()

    now = datetime.now(
        ROLL_TIMEZONE
    )

    next_cycle = pick_next_cycle_time(
        now
    )

    print()
    print(
        "Combined Mudae roller started."
    )

    print(
        f"Managing "
        f"{len(ACCOUNTS)} accounts."
    )

    print(
        "Scheduler timezone: "
        "UTC"
    )

    print(
        "Next cycle: "
        + next_cycle.strftime(
            "%Y-%m-%d "
            "%I:%M:%S %p %Z"
        )
    )

    while True:

        now = datetime.now(
            ROLL_TIMEZONE
        )

        if now >= next_cycle:

            try:

                run_hourly_cycle()

            except Exception as e:

                print(
                    f"ERROR DURING "
                    f"HOURLY CYCLE: {e}"
                )

            # IMPORTANT:
            # Calculate from CURRENT TIME after
            # the entire cycle finishes.
            #
            # This prevents overlapping cycles.
            next_cycle = (
                pick_next_cycle_time(
                    datetime.now(
                        ROLL_TIMEZONE
                    )
                )
            )

            print()
            print(
                "Next cycle: "
                + next_cycle.strftime(
                    "%Y-%m-%d "
                    "%I:%M:%S %p %Z"
                )
            )

        time.sleep(1)


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    run_forever()