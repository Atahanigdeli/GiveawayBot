# Discord Giveaway Bot

A simple Discord bot for hosting giveaways with customizable duration and number of winners.

## Features

- Start giveaways with custom duration (hours, days, or weeks)
- Set number of winners
- Automatic winner selection
- Reroll functionality
- Clean embed messages

## Setup

1. **Install Python 3.8 or higher**
   - Download from [python.org](https://www.python.org/downloads/)

2. **Install required packages**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up your bot**
   - Go to [Discord Developer Portal](https://discord.com/developers/applications)
   - Create a new application
   - Go to the "Bot" tab and click "Add Bot"
   - Copy the bot token
   - Enable "Message Content Intent" in the bot settings
   - Invite the bot to your server with the following permissions:
     - Send Messages
     - Embed Links
     - Add Reactions
     - Read Message History

4. **Configure the bot**
   - Open the `.env` file
   - Replace `your_bot_token_here` with your bot's token
   - Save the file

## Usage

- **Start a giveaway:**
  ```
  !giveaway <duration><unit> <winners> <prize>
  ```
  Example: `!giveaway 1d 1 Discord Nitro`
  
  Duration units:
  - `h` for hours (e.g., 12h)
  - `d` for days (e.g., 7d)
  - `w` for weeks (e.g., 2w)

- **Reroll winners:**
  ```
  !reroll <message_id> [winners]
  ```
  Example: `!reroll 123456789012345678 2`

## Running the Bot

```bash
python bot.py
```

## Notes

- The bot must have permissions to read messages and reactions in the channel where the giveaway is hosted.
- The bot needs to be online for the giveaway to end automatically.
- For 24/7 hosting, consider using a cloud service like Replit, Heroku, or a VPS.
