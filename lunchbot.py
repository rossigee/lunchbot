#!/usr/bin/env python3

import os, sys
import asyncio
import datetime
import functools
import json
import random
import signal
import threading
import time

import logging
_logfmt = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
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
`/lunch change place` - Change to a different restaurant.
`/lunch skip` - Skip due to other commitments.
"""

DEFAULT_STATE = {
    "next_time": "2019-04-19T12:00:00.000Z",
    "next_place": {
        "name": "Ruam Pon",
        "url": "https://www.google.com/maps/place/%E0%B8%A3%E0%B9%89%E0%B8%B2%E0%B8%99%E0%B8%AD%E0%B8%B2%E0%B8%AB%E0%B8%B2%E0%B8%A3%E0%B8%A3%E0%B8%A7%E0%B8%A1%E0%B8%9E%E0%B8%A5/@11.3556358,99.5704748,19.75z/data=!4m5!3m4!1s0x30fee7c318329155:0x4f329ce2301e25a7!8m2!3d11.3558359!4d99.5707702"
    },
    "who_pays": "Steve",
    "participants": [
        "Ross",
        "Steve"
    ],
    "places": [
        # Closed for off season...
        #{
        #    "name": "Cafe Del Mar",
        #    "url": "https://www.google.com/maps/place/%E0%B8%84%E0%B8%B8%E0%B8%93%E0%B8%99%E0%B8%B2%E0%B8%A2%E0%B8%81%E0%B8%B3%E0%B8%99%E0%B8%B1%E0%B8%99+%E2%80%93+Cafe+del+Mar/@11.3530552,99.5602715,16.42z/data=!4m5!3m4!1s0x0:0x67d9d1fa6a389fa6!8m2!3d11.3559418!4d99.5708553"
        #},
        {
            "name": "Nam Neua 2",
            "url": "https://www.google.com/maps/place/Baan+Num+Neua+Bar/@11.3530552,99.5602715,16.42z/data=!4m5!3m4!1s0x0:0x32ab146768732323!8m2!3d11.354197!4d99.5680846"
        },
        {
            "name": "Pla Too Seafood",
            "url": "https://www.google.com/maps/place/Platoo+Seafood/@11.3486113,99.5641838,17.92z/data=!4m5!3m4!1s0x0:0xc33be567c6ad189f!8m2!3d11.3472663!4d99.5652066"
        },
        {
            "name": "Ban Sewan",
            "url": "https://www.google.com/maps/place/%E0%B8%84%E0%B8%A3%E0%B8%B1%E0%B8%A7%E0%B8%9A%E0%B9%89%E0%B8%B2%E0%B8%99%E0%B8%AA%E0%B8%A7%E0%B8%99+%E0%B8%9A%E0%B9%89%E0%B8%B2%E0%B8%99%E0%B8%81%E0%B8%A3%E0%B8%B9%E0%B8%94/@11.3608861,99.5578898,15.17z/data=!4m5!3m4!1s0x0:0x390b893e04b593a0!8m2!3d11.3623069!4d99.5588645"
        },
        {
            "name": "Ruam Pon",
            "url": "https://www.google.com/maps/place/%E0%B8%A3%E0%B9%89%E0%B8%B2%E0%B8%99%E0%B8%AD%E0%B8%B2%E0%B8%AB%E0%B8%B2%E0%B8%A3%E0%B8%A3%E0%B8%A7%E0%B8%A1%E0%B8%9E%E0%B8%A5/@11.3556358,99.5704748,19.75z/data=!4m5!3m4!1s0x30fee7c318329155:0x4f329ce2301e25a7!8m2!3d11.3558359!4d99.5707702"
        }
    ]
}

schedstop = threading.Event()

def _next_friday():
    today = datetime.datetime.now()
    friday = today + datetime.timedelta((4 - today.weekday()) % 7)
    friday = friday.replace(hour=12, minute=0, second=0)
    return friday


class ScheduleThread(threading.Thread):
    @classmethod
    def run(cls):
        _logger.info("Running scheduler thread...")
        while not schedstop.is_set():
            _logger.debug("Running pending tasks in scheduler thread...")
            schedule.run_pending()
            time.sleep(5)
        _logger.info("Exiting scheduler thread...")


class Lunchbot:
    def __init__(self, statefilename, token, channel_id):
        self.statefilename = statefilename
        self.token = token
        self.channel_id = channel_id

        # Default state, to seed persistent state if not found
        self.state = DEFAULT_STATE
        self.load_state()

    def load_state(self):
        try:
            f = open(self.statefilename, "r")
            self.state = json.load(f)
            f.close()
            _logger.info(f"State restored from file ({self.statefilename}).")
        except FileNotFoundError:
            _logger.info(f"Missing state file ({self.statefilename}). Will create a new one.")
            self.save_state()
        except:
            e = sys.exc_info()[0]
            _logger.exception(f"Could not load state file ({self.statefilename}).", e)

    def save_state(self):
        try:
            f = open(self.statefilename, "w")
            f.write(json.dumps(self.state, indent=4))
            f.close()
            _logger.debug(f"State saved to file ({self.statefilename}).")
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
            _logger.info(f"Logged into Discord as {self.client.user}.")

            self.channel = self.client.get_channel(int(self.channel_id))
            if self.channel is None:
                _logger.error(f"Unable to connect to notification channel ({self.channel_id}).")
            else:
                _logger.info(f"Connected to channel {self.channel}.")

            #text = "(on ready)"
            #await self.channel.send(text)

        @self.client.event
        async def on_message(message):
            if message.content[0:6].lower() != "/lunch":
                return

            _logger.info(f"{message.channel.id}:{message.author}: {message.content}")
            if message.content.lower() == "/lunch status":
                await self.status(message)
            elif message.content.lower() == "/lunch change place":
                await self.change_place(message)
            elif message.content.lower() == "/lunch skip":
                await self.skip(message)
            else:
                await self.usage(message)

    def usage(self, message):
        return message.channel.send(USAGE)

    def _set_next_payee(self):
        participants = self.state['participants']
        who_paid_last = self.state['who_pays']
        next_participant_id = (participants.index(who_paid_last) + 1) % len(participants)
        _logger.info("Setting next payee to {}.".format(participants[next_participant_id]))
        self._set_state('who_pays', participants[next_participant_id])

    def _set_next_place(self):
        places = self.state['places']
        last_place = self.state['next_place']
        next_place = last_place
        places = self.state['places']
        while last_place['name'] == next_place['name']:
            idx = random.randint(0, len(places) - 1)
            next_place = self.state['places'][idx]
        _logger.info("Setting next place to {}.".format(next_place['name']))
        self._set_state('next_place', next_place)

    def _move_to_next_friday(self):
        friday = _next_friday()
        friday_json = friday.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        _logger.info("Moving to next {}.".format(friday.strftime("%A, %b %d %Y %H:%M")))
        self._set_state('next_time', friday_json)

    def _move_to_following_friday(self):
        friday = _next_friday() + datetime.timedelta(7)
        friday_json = friday.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        _logger.info("Moving to following {}.".format(friday.strftime("%A, %b %d %Y %H:%M")))
        self._set_state('next_time', friday_json)

    def _get_next_time_str(self):
        next_time = datetime.datetime.strptime(self.state['next_time'], '%Y-%m-%dT%H:%M:%S.%fZ')
        return next_time.strftime("%A, %b %d %Y %H:%M")

    def _get_mins_until_lunch(self):
        t_then = datetime.datetime.strptime(self.state['next_time'], '%Y-%m-%dT%H:%M:%S.%fZ')
        t_now = datetime.datetime.now()
        return int((t_now - t_then).total_seconds() / 60)

    def _get_next_place_embed(self):
        return discord.Embed(
            title=self.state['next_place']['name'],
            description="",
            color=0x00ff00,
            url=self.state['next_place']['url']
        )

    def skip(self, message):
        self._move_to_following_friday()
        return self.status(message)

    def change_place(self, message):
        self._move_to_next_friday()
        self._set_next_place()
        return self.status(message)

    def status(self, message):
        next_time_str = self._get_next_time_str()
        reply = f"Lunch will be {next_time_str} at {self.state['next_place']['name']}. It'll be {self.state['who_pays']}'s turn to pay."
        return message.channel.send(reply, embed=self._get_next_place_embed())

    def remind_participants(self):
        _logger.info("Reminding participants")
        async def _coro_remind_participants(self):
            mins = self._get_mins_until_lunch()
            text = f"Lunch in {mins} mins at {self.state['next_place']['name']}. It's {self.state['who_pays']}'s turn to pay."
            _logger.info(text)
            await self.channel.send(text, embed=self._get_next_place_embed())
        asyncio.run_coroutine_threadsafe(_coro_remind_participants(self), self.client.loop)

    def next_time(self):
        _logger.info("Setting next lunch time")
        async def _coro_next_time(self):
            self._set_next_payee()
            self._set_next_place()
            self._move_to_next_friday()
            next_time_str = self._get_next_time_str()
            text = f"Hope you enjoyed your meal. Next lunch will be {next_time_str} at {self.state['next_place']['name']}. It'll be {self.state['who_pays']}'s turn to pay."
            _logger.info(text)
            _logger.debug(await self.channel.send(text, embed=self._get_next_place_embed()))
        asyncio.run_coroutine_threadsafe(_coro_next_time(self), self.client.loop)

    def prepare_scheduler(self):
        schedule.every().friday.at("11:30").do(self.remind_participants)
        schedule.every().friday.at("14:00").do(self.next_time)
        schedule.every().minute.do(self.save_state)

        self.scheduler_thread = ScheduleThread()
        self.scheduler_thread.start()

    def main(self):
        self.setup_discord_client()

        self.prepare_scheduler()

        self.client.run(token)

        # Stop scheduler thread
        schedstop.set()


if __name__ == '__main__':
    try:
        statefile = sys.argv[1]
    except:
        statefile = "/persistence.json"

    token = os.getenv("DISCORD_TOKEN")
    channel_id = os.getenv("DISCORD_CHANNEL")

    lunchbot = Lunchbot(statefile, token, channel_id)
    lunchbot.main()
