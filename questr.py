#!/usr/bin/env python3.7
import argparse
import asyncio
import re
from sys import platform
import time

from PIL import Image
import sys
from pyocr import pyocr
from pyocr import builders
import yaml

from pokemonlib import PokemonGo
from COOLmeDOWN import splitCoords, calculate, calculateCD

import logging
from colorlog import ColoredFormatter
logger = logging.getLogger('ivcheck')
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
formatter = ColoredFormatter("  %(log_color)s%(levelname)-8s%(reset)s | %(log_color)s%(message)s%(reset)s")
ch.setFormatter(formatter)
logger.addHandler(ch)

def get_median_location(box_location):
    '''
    Given a list of 4 coordinates, returns the central point of diagonal intersections
    '''
    x1, y1, x2, y2 = box_location
    return [int((x1 + x2) / 2), int((y1 + y2) / 2)]

class Main:
    def __init__(self, args):
        with open(args.config, "r") as f:
            self.config = yaml.load(f)
        self.args = args
        tools = pyocr.get_available_tools()
        self.tool = tools[0]
        self.p = PokemonGo()

    async def tap(self, location):
        coordinates = self.config['locations'][location]
        if len(coordinates) == 2:
            await self.p.tap(*coordinates)
            if location in self.config['waits']:
                await asyncio.sleep(self.config['waits'][location])
        elif len(coordinates) == 4:
            median_location = get_median_location(coordinates)
            await self.p.tap(*median_location)
            if location in self.config['waits']:
                await asyncio.sleep(self.config['waits'][location])
        else:
            logger.error('Something is not right.')
            raise Exception

    async def swipe(self, location, duration):
        await self.p.swipe(
            self.config['locations'][location][0],
            self.config['locations'][location][1],
            self.config['locations'][location][2],
            self.config['locations'][location][3],
            duration
        )
        if location in self.config['waits']:
            logger.info('Waiting ' + str(self.config['waits'][location]) + ' seconds after ' + str(self.config['locations'][location]) + '...')
            await asyncio.sleep(self.config['waits'][location])

    async def key(self, keycode):
        await self.p.key(keycode)
        if str(keycode).lower in self.config['waits']:
            await asyncio.sleep(self.config['waits'][str(keycode).lower])

    async def deal_with_blocking_dialogs(self):
        screencap = await self.p.screencap()
        text_oh = screencap.crop(self.config['locations']['oh_hatching_box'])
        text_oh = self.tool.image_to_string(text_oh).replace("\n", " ")
        text_gps = screencap.crop(self.config['locations']['im_a_passenger_button_box'])
        text_gps = self.tool.image_to_string(text_gps).replace("\n", " ")

        if 'PASSENGER' in text_gps:
            logger.error("I'M NOT A PASSENGER, I'M A SPOOFER, WHEN ARE YOU GOING TO UNDERSTAND?!")
            await self.tap('im_a_passenger_button_box')
            return True
        elif 'Oh' in text_oh or '?' in text_oh:
            logger.error('Oh, look at that, we just hatched an egg, lol.')
            # click anywhere, twice (we click on i'm a passenger button)
            await self.tap('im_a_passenger_button_box')
            await self.tap('im_a_passenger_button_box')
            # wait animation
            await asyncio.sleep(20)
            # close pokemon screen
            await self.tap('x_button')
            return True

        return False

    async def cap_and_crop(self, location):
        screencap = await self.p.screencap()
        crop = screencap.crop(self.config['locations'][location])
        text = self.tool.image_to_string(crop).replace("\n", " ")
        logger.info('[OCR] Found text: %s', text)
        return text

    async def start(self):
        await self.p.set_device(self.args.device_id)

        with open('quest_list.txt', 'r') as file:
            quest_list = file.read().splitlines()

        actions_so_far = 0
        for num, quest in enumerate(quest_list, start=1):
            quest_coords = splitCoords(quest)
            time_start = time.time()

            logger.info('Teleporting to quest number %s, coords: %s', num, quest_coords)
            await self.p.run(["adb", "-s", await self.p.get_device(), "shell", 'am start-foreground-service -a theappninjas.gpsjoystick.TELEPORT --ef lat {} --ef lng {}'.format(*quest_coords)])
            await asyncio.sleep(20)

            await self.deal_with_blocking_dialogs

            await self.tap('pokestop')
            logger.info('Clicking PokeStop')

            logger.info('Spinning...')
            await self.swipe('spin_swipe', 300)

            logger.info('Leaving PokeStop')
            await self.tap('x_button')

            # Validate/Check/DO action (for other actions rather than spinning)
            if args.action == 'spin':
                actions_so_far += 1

            # Finished, can claim quest
            if actions_so_far == args.num:
                actions_so_far = 0
                await self.tap('quest_button')
                text = await self.cap_and_crop('claim_reward_box')
                if 'CLAIM REWARD' in text:
                    await self.tap('claim_reward_box')
                else:
                    logger.error("Seems we didn't complete any quest! Lets try again...")
                    num = num - 1
                    continue

            next_quest = quest_list[num + 1]
            next_quest_coords = splitCoords(next_quest)

            cooldown_until_next_stop = calculateCD(calculate(*quest_coords, *next_quest_coords)) * 60  # in seconds
            time_so_far = time.time() - time_start
            total_time_to_wait = max(0, cooldown_until_next_stop - time_so_far) + 5  # extra 30 seconds

            logger.info('Cooldown until next PokeStop is {} seconds.'.format(total_time_to_wait))
            await asyncio.sleep(cooldown_until_next_stop - time_so_far)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Pokemon go renamer')
    parser.add_argument('--device-id', type=str, default=None,
                        help="Optional, if not specified the phone is automatically detected. Useful only if you have multiple phones connected. Use adb devices to get a list of ids.")
    parser.add_argument('--config', type=str, default='config.yaml',
                        help="Config file location.")
    parser.add_argument('--action', type=str, default='spin',
                        help="Action to perform required by the particular quest type. Available options: Spin N PokeStops"),  #Trade X
    parser.add_argument('-n', '--num', type=int, default='2',
                        help="Number of times that the action must be performed to complete the quest (i.e.: the N on the options below)."
                        + "After the action is performed N times, the completed quest will be claimed, and the process starts again."),
    args = parser.parse_args()

    asyncio.run(Main(args).start())
