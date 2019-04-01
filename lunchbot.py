#!/usr/bin/env python3

import os, sys

import discord

import logging
#logging.basicConfig(level = logging.DEBUG)
_logger = logging.getLogger(__name__)
print(_logger.handlers)
_logger.setLevel(logging.DEBUG)

DEFAULT_STATE = {
    "participants": [
        "Ross",
        "Steve"
    ],
    "next_time": "2019-04-05 12:00:00",
    "who_pays": "Ross"
}


class Lunchbot:
    def __init__(self, statefilename, token):
        self.statefilename = statefilename
        self.token = token

        # Default state, to seed persistent state if not found
        self.state = DEFAULT_STATE

    def load_state(self):
        try:
            f = open(self.statefilename, "r")
            self.state = json.read(f)
            close(f)
            _logger.info(f"State restored from file ({self.statefilename}).")
        except:
            _logger.warn(f"Could not load state file ({self.statefilename}).")

    def save_state(self):
        try:
            f = open(self.statefilename, "w")
            json.dump(self.state, f)
            close(f)
            _logger.info(f"State saved to file ({self.statefile}).")
        except:
            _logger.warn(f"Could not save state file ({self.statefilename}).")

    def setup_discord_client(self):
        client = discord.Client()

        @client.event
        async def on_ready():
            _logger.info(f"Logged into Discord as {client.user}")

        @client.event
        async def on_message(message):
            _logger.debug(f"{message.author}: {message.content}")
            if(message.content[0:6].lower() == "/lunch"):
                reply = f"Next lunch is on {self.state.next_time}. It's {self.state.who_pays}'s turn to pay."
                await client.send_message(message.channel, reply)

        _logger.info(f"Starting Discord client...")
        client.run(token)

    def main(self):
        self.load_state()

        self.setup_discord_client()

        # [TODO] Background maintenance thread...
        #self.start_background_thread()


if __name__ == '__main__':
    token = os.getenv("DISCORD_TOKEN")

    try:
        statefile = sys.argv[1]
    except:
        statefile = "/persistence.json"

    lunchbot = Lunchbot(statefile, token)
    lunchbot.main()
