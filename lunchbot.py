#!/usr/bin/env python3

import os, sys
import asyncio
import datetime
import functools
import json
import signal
import threading
import time

import logging
_logfmt = logging.Formatter('%(asctime)s,%(msecs)d %(levelname)s %(message)s')
_loghandler = logging.StreamHandler()
_loghandler.setFormatter(_logfmt)
_logger = logging.getLogger(__name__)
if 'LOGGING' in os.environ:
    if os.environ['LOGGING'] == 'INFO':
        _logger.setLevel(logging.INFO)
    if os.environ['LOGGING'] == 'DEBUG':
        _logger.setLevel(logging.DEBUG)
_logger.addHandler(_loghandler)

import discord
import schedule

USAGE = """
Usage:
`/lunch status` - Show next lunch details.
`/lunch skip` - Skip due to other commitments.
"""

DEFAULT_STATE = {
    "participants": [
        "Ross",
        "Steve"
    ],
    "next_time": "2019-04-05 12:00:00",
    "who_pays": "Ross"
}

DISCORD_CHANNEL = "562844655407071262"


class Lunchbot:
    def __init__(self, statefilename, token):
        self.statefilename = statefilename
        self.token = token

        self.channel_id = DISCORD_CHANNEL

        # Default state, to seed persistent state if not found
        self.state = DEFAULT_STATE
        self.load_state()

    def load_state(self):
        try:
            f = open(self.statefilename, "r")
            self.state = json.read(f)
            close()
            _logger.info(f"State restored from file ({self.statefilename}).")
        except:
            e = sys.exc_info()[0]
            _logger.exception(f"Could not load state file ({self.statefilename}).", e)

    def save_state(self):
        try:
            f = open(self.statefilename, "w")
            f.write(json.dumps(self.state, indent=4))
            close(f)
            _logger.info(f"State saved to file ({self.statefile}).")
        except:
            e = sys.exc_info()[0]
            _logger.exception(f"Could not save state file ({self.statefilename}).", e)

    def _set_state(self, key, value):
        self.state[key] = value
        self.save_state()

    def setup_discord_client(self):
        self.client = discord.Client()

        @self.client.event
        async def on_ready():
            _logger.info(f"Logged into Discord as {self.client.user}")

        @self.client.event
        async def on_message(message):
            _logger.debug(f"{message.channel.id}:{message.author}: {message.content}")
            if message.content[0:6].lower() != "/lunch":
                return
            elif message.content.lower() == "/lunch status":
                await self.status(message)
            elif message.content.lower() == "/lunch skip":
                await self.skip(message)
            else:
                await self.usage(message)

    def usage(self, message):
        return self.client.send_message(message.channel, USAGE)

    def _set_next_payee(self):
        participants = self.state['participants']
        who_paid_last = self.state['who_pays']
        next_participant_id = (participants.indexOf(who_pays) + 1) % len(participants)
        self._set_state('who_pays', partipants[next_participant_id])

    def _move_to_next_friday(self):
        today = datetime.date.today()
        friday = today + datetime.timedelta((4 - today.weekday()) % 7)
        friday_json = friday.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        self._set_state('next_time', friday_json)

    def _move_to_following_friday(self):
        today = datetime.date.today() + datetime.timedelta(7)
        friday = today + datetime.timedelta((4 - today.weekday()) % 7)
        friday_json = friday.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        self._set_state('next_time', friday_json)

    def skip(self, message):
        self._move_to_following_friday()
        reply = f"OK. So, next lunch will be on {self.state['next_time']}. It'll be {self.state['who_pays']}'s turn to pay."
        return self.client.send_message(message.channel, reply)

    def status(self, message):
        reply = f"Lunch will be on {self.state['next_time']}. It'll be {self.state['who_pays']}'s turn to pay."
        return self.client.send_message(message.channel, reply)

    def remind_participants(self):
        text = f"Lunch in 30 mins. It'll be {self.state['who_pays']}'s turn to pay today."
        return self.client.send_message(self.channel_id, text)

    def next_time(self):
        self._set_next_payee()
        self._move_to_next_friday()
        text = f"Hope you enjoyed your meal. Reminder set for next week."
        return self.client.send_message(self.channel_id, text)

    def prepare_scheduler(self):
        class ScheduleThread(threading.Thread):
            @classmethod
            def run(cls):
                _logger.debug("Running scheduler thread...")
                while self.client.loop.is_running():
                    _logger.debug("Running pending tasks in scheduler thread...")
                    schedule.run_pending()
                    time.sleep(5)
                _logger.debug("Exiting scheduler thread...")

        schedule.every().friday.at("11:30").do(self.remind_participants)
        schedule.every().friday.at("14:00").do(self.next_time)

        _logger.debug("Starting scheduler thread...")
        self.scheduler_thread = ScheduleThread()
        self.scheduler_thread.start()
        _logger.debug("Started scheduler thread...")

    def main(self):
        def sig_handler(sig_name):
            _logger.info("Received %s" % signame)
            self.scheduler_thread.stop()

        self.setup_discord_client()
        self.prepare_scheduler()

        _logger.info(f"Starting Discord client...")
        self.client.run(token)

        sys.exit(0)

if __name__ == '__main__':
    token = os.getenv("DISCORD_TOKEN")

    try:
        statefile = sys.argv[1]
    except:
        statefile = "/persistence.json"

    lunchbot = Lunchbot(statefile, token)
    lunchbot.main()
