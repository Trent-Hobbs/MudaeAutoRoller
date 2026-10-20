# Combined Mudae Autoroller

A configurable Python script for scheduled Mudae rolls, character claims, and kakera collection on Discord. Supports multiple accounts, individual activity schedules, shared character and series preferences, and persistent claim tracking.

## Features

- Runs hourly cycles with randomized start times and account order.
- Supports separate account schedules, including overnight shifts.
- Attempts to claim characters matching shared character or series lists, or rolls containing a `wished by` message.
- Uses heart claim buttons when available, with reaction attempts as a fallback when no button is found.
- Checks for a marriage confirmation before recording a successful claim.
- Attempts to collect configured kakera types from rolled cards.
- Saves confirmed claim times between restarts.
- Prints roll progress, claim results, and scheduling information to the terminal.

## Files

| File | Purpose |
| --- | --- |
| `Public_CombinedBot.py` | Public script template with placeholder account details and Discord IDs. |
| `README.md` | Setup, configuration, and behavior reference. |
| `public_claim_state.json` | Runtime state file created when claim state is saved; keep this local. |

## Requirements

- Python 3.9 or newer for the built-in `zoneinfo` module. Dependency compatibility with your Python version must be checked separately.
- Python packages: `discum`, `requests`, and `tzdata`.
- Access to the configured Discord channel and a running Mudae instance.

Install dependencies using your Python interpreter:

```sh
python -m pip install discum requests tzdata
```

`tzdata` supplies timezone information on systems without an IANA timezone database, including many Windows installations. See the [Python zoneinfo documentation](https://docs.python.org/3/library/zoneinfo.html#data-sources).

## Configuration

Edit the settings near the top of `Public_CombinedBot.py` before running it. The public defaults are examples and need to match your environment.

### Discord IDs

Replace `CHANNEL_ID` and `SERVER_ID` with your channel and server IDs, keeping the values as strings. `MUDAE_BOT_ID` identifies Mudae and is already populated.

### Accounts

Each entry in `ACCOUNTS` uses these fields:

| Field | Purpose |
| --- | --- |
| `name` | Unique local label used in logs and as the saved claim-state key. |
| `username` | Text expected in Mudae's marriage confirmation message. Matching is case insensitive. |
| `token` | Authentication token used by the script. Keep configured copies private. |
| `rollCommand` | Roll command without the leading `$`, such as `wa`. |
| `startHour` | First active hour in `ROLL_TIMEZONE`. |
| `endHour` | End of the active period, exclusive. |

Duplicate the example dictionary to configure additional accounts. Keep each `name` unique and stable so its saved claim time can be restored.

The example schedule, `startHour = 0` and `endHour = 24`, allows all hours. A schedule from `22` to `6` allows 10 PM through 5:59 AM. Equal start and end hours also allow all hours under the current scheduling logic.

### Character and series preferences

Populate the shared lists with the names displayed in Mudae embeds:

```python
desiredCharacters = [
    "Example Character",
]

desiredSeries = [
    "Example Series",
]
```

Character and series matching uses exact, case-sensitive strings. The script treats the first line of the embed description as the series name.

Both lists are empty in the public template. A roll containing `wished by` can still trigger a claim attempt; this checks for the phrase, rather than identifying which account wished for it.

### Timing and claim resets

| Setting | Public default | Purpose |
| --- | --- | --- |
| `ROLL_TIMEZONE` | `ZoneInfo("UTC")` | Timezone used for hourly cycles and account activity schedules. |
| `ROLL_WINDOW_START` / `ROLL_WINDOW_END` | `1` / `4` | Inclusive range of minutes used to start a cycle in the next hour. |
| `MIN_ACCOUNT_DELAY_SECONDS` / `MAX_ACCOUNT_DELAY_SECONDS` | `120` / `300` | Random wait between accounts that roll. |
| `ROLLS_PER_ACCOUNT` | `12` | Maximum roll attempts for an account in one cycle. |
| `ROLL_DELAY_SECONDS` | `1.8` | Pause after a processed roll when the session continues. |
| `CLAIM_INTERVAL_HOURS` | `3` | Interval between configured claim resets. |
| `CLAIM_RESET_HOUR` / `CLAIM_RESET_MINUTE` | `0` / `0` | Anchor time used to calculate the next reset. |

Claim timestamps and reset calculations currently use the computer's local time through `datetime.now()`, while cycle scheduling uses `ROLL_TIMEZONE`. Configure the claim reset anchor in the computer's local time, even if `ROLL_TIMEZONE` is different.

Claim availability is estimated from locally recorded successful claims. Claims made outside the script are not automatically synchronized. An account without saved claim history is initially treated as available.

### Kakera collection

`anycardKakeras` lists kakera emoji names to collect from any processed card. `soulmateKakeras` lists additional types to collect when the embed description contains `chaoskey`. These checks depend on Mudae's message format.

## Running

From the directory containing the configured script:

```sh
python Public_CombinedBot.py
```

On Windows, use `py` instead of `python` if that is your installed launcher.

The script schedules its first cycle for the next hour; it does not roll immediately on startup. With the defaults, cycles begin at a randomly selected minute from 1 through 4 and a second from 2 through 25. Accounts are processed sequentially. The next cycle is scheduled after the current cycle finishes.

An account is skipped outside its activity schedule or when its local claim tracker indicates a claim is unavailable. Its rolling session stops after a confirmed claim. Kakera handling happens while processing rolls; there is no independent background kakera monitor.

Keep the terminal running. Press `Ctrl+C` to stop.

## Saved state and publishing

`public_claim_state.json` stores account labels and last confirmed claim timestamps. Its path is relative to the working directory, so start the script from the same directory to reuse the same state file.

Publish the unconfigured public template and this README. Keep tokens, configured personal copies, and claim-state files out of your repository. Suggested `.gitignore` entries:

```gitignore
CombinedBot.py
*claim_state.json
.env
.venv/
__pycache__/
*.pyc
```

These rules do not protect credentials entered directly into a tracked `Public_CombinedBot.py`. Keep your configured version separate from the public template.

## Limitations

The script relies on Discord API v8 endpoints, Discum, Mudae message text, embed layouts, and button formats. Changes to any of these may require code updates. Randomized scheduling does not provide comprehensive rate-limit handling, and claim attempts are not guaranteed to succeed.

The public template has been reviewed for configuration and documentation consistency. Live Discord behavior and dependency compatibility have not been validated as part of this release preparation.
