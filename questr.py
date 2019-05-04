#!/usr/bin/env python3.7
import argparse
import asyncio
import logging
import re
import sys
import time
from sys import platform
import os

import yaml
from PIL import Image
from pyocr import builders, pyocr

from COOLmeDOWN import calculate, calculateCD, splitCoords
from pokemonlib import PokemonGo

import logging

try:
    import colorlog
    HAVE_COLORLOG = True
except ImportError:
    HAVE_COLORLOG = False

def create_logger():
    '''Setup the logging environment'''
    log = logging.getLogger()  # root logger
    log.setLevel(logging.INFO)
    format_str = '[%(asctime)s] (%(name)8.8s) %(levelname)8s | %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    if HAVE_COLORLOG:
        cformat = '%(log_color)s' + format_str
        formatter = colorlog.ColoredFormatter(cformat, date_format)
    else:
        formatter = logging.Formatter(format_str, date_format)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    log.addHandler(stream_handler)
    return logging.getLogger(__name__)

logger = create_logger()

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

    async def hue_affinity(self, im, hue1, hue2):
        '''Checks the affinity, in percentual terms,
        of the average median im hue against hue1 and
        hue2.

        Input values are in range 0-255, instead of
        the common 0-360° used for HSL and HSV images.

        Arguments:
            image {Image}   -- PIL.Image
            hue1  {int}     -- 0-255
            hue2  {int}     -- 0-255

        Returns:
            {tuple}   -- A tuple containing the relative
                         percentages lenghts of the arcs
                         between im's median hue against
                         hue1 and hue2, respectively.
        '''
        ## Image filtering mumbojumbo
        im = im.quantize()
        im = im.resize((1, 1))
        im = im.convert('HSV')
        pixel = im.getpixel((0, 0))

        ## Gets us one only int, the average hue of the image
        hue = pixel[0]

        ## The Angles
        # The modulus makes it a polar function, i.e.:
        # everything that overflows or underflows 255
        # becomes the difference, so we don't need to
        # translate values nor calculate distances :)
        a1 = abs(hue-hue1) % 255
        a2 = abs(hue-hue2) % 255

        # This is just for giggles
        confidence = (1 - (min(a1, a2) / max(a1, a2))) * 100

        logger.info('Detected H: %s (%i%% of H1: %s | %i%% of H2: %s) with a confidence of %i%%', hue, a1, hue1, a2, hue2, confidence)

        if a1 < a2:
            return True
            # return ((((a1 + hue) / hue) - 1) * 100, (((a2 + hue) / hue) - 1) * 100)
        if a2 < a1:
            return False
            # return ((((a1 + hue) / hue) - 1) * 100, (((a2 + hue) / hue) - 1) * 100)
        raise Exception("Well you got unlucky boy, it's right on the middle")

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
            logger.error('Something is not right.')('KEYCODE_BACK')
                                # await self.tap('x_button')
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
            logger.info('Waiting %s seconds after %s...', self.config['waits'][location], self.config['locations'][location])
            await asyncio.sleep(self.config['waits'][location])

    async def key(self, keycode):
        await self.p.key(keycode)
        if str(keycode).lower in self.config['waits']:
            logger.info('Waiting %s seconds after %s...', self.config['waits'][keycode], self.config['locations'][keycode])
            await asyncio.sleep(self.config['waits'][str(keycode).lower])

    async def check_where_the_hell_are_we(self):
        screencap = await self.p.screencap()

        text_gps = screencap.crop(self.config['locations']['im_a_passenger_button_box'])
        text_gps = self.tool.image_to_string(text_gps).replace("\n", " ")
        if 'PASSENGER' in text_gps:
            logger.error("I'M NOT A PASSENGER, I'M A SPOOFER, WHEN ARE YOU GOING TO UNDERSTAND?!")
            await self.tap('im_a_passenger_button_box')
            return 'on_passenger'

        text_oh = screencap.crop(self.config['locations']['oh_hatching_box'])
        text_oh = self.tool.image_to_string(text_oh).replace("\n", " ")
        if 'Oh' in text_oh or '?' in text_oh:
            logger.error('Oh, look at that, we just hatched an egg, lol.')
            # click anywhere, twice (we click on i'm a passenger button)
            await self.tap('im_a_passenger_button_box')
            await self.tap('im_a_passenger_button_box')
            # wait animation
            await asyncio.sleep(20)
            # close pokemon screen
            await self.tap('x_button')
            return 'on_egg'

        text_shop = screencap.crop(self.config['locations']['shop_button_text_box'])
        text_shop = self.tool.image_to_string(text_shop).replace("\n", " ")
        if 'SHOP' in text_shop:
            logger.error('Looks like somehow we went onto the menu... lolz')
            await self.tap('x_button')
            return 'on_menu'

        return 'on_world'

    async def cap_and_crop(self, location):
        screencap = await self.p.screencap()
        crop = screencap.crop(self.config['locations'][location])
        text = self.tool.image_to_string(crop).replace("\n", " ")
        logger.info('[OCR] Found text: %s', text)
        return text

    async def spin_pokestop(self, time_when_cooldown_ends):
        '''Spins pokestop

        Returns:
            {bool} -- True means you can move on to next pokestop, false means not.
        '''

        logger.info('Clicking PokeStop')
        await self.tap('pokestop')

        while True:
            screencap = await self.p.screencap()
            crop = screencap.crop(self.config['locations']['bottom_pokestop_bar'])
            is_color_blue = await self.hue_affinity(crop, 130, 200)
            if is_color_blue:
                logger.info("We're certainly on a non spun pokestop yet! :D We shall wait for the cooldown.")
                while time.time() < time_when_cooldown_ends:
                    # sys.stdout.write("\r")
                    # sys.stdout.write("{:2f} seconds remaining.".format(time_when_cooldown_ends - time.time()))
                    # sys.stdout.flush()
                    half_life = (time_when_cooldown_ends - time.time()) / 2
                    logger.info('%f seconds to go...', half_life)
                    half_life = half_life if half_life >= 2 else 2
                    await asyncio.sleep(half_life)
                logger.warning("Cooldown is OVER! Let's go.")
            elif not is_color_blue:
                logger.info("We already spun this pokestop! I'm leaving and moving on!")
                await self.tap('x_button')
                return 'skip'
            else:
                logger.error("We don't seem to be on the correct place...")
                return 'repeat'

            logger.info('Spinning...')
            await self.swipe('spin_swipe', 300)
            screencap = await self.p.screencap()
            crop = screencap.crop(self.config['locations']['bottom_pokestop_bar'])
            is_color_blue = await self.hue_affinity(crop, 130, 200)
            if not is_color_blue:
                logger.info('All good! Leaving PokeStop')
                await self.tap('x_button')
                return 'ok'
            else:
                logger.info('Nah, doesnt look like it worked.')
                await self.tap('x_button')
                return 'repeat'


        # TODO: figure out the bag thing
        # await asyncio.sleep(0.35)
        # screencap = await self.p.screencap()

        # crop = screencap.crop(self.config['locations']['your_bag_is_full_text_box'])
        # text = self.tool.image_to_string(crop).replace("\n", " ")
        # if 'Bag' in text:
        #     logger.error('Shit, we need to clear our bag and try again.')
        #     await self.tap('x_button')
        #     return 'bag'
        # crop = screencap.crop(self.config['locations']['your_bag_is_full_text_box'])
        # text = self.tool.image_to_string(crop).replace("\n", " ")
        # crop.show()
        # logger.critical(text)
        # if any(word in text for word in ['try', 'again', 'later']):
        #     logger.error("Oh, we're being too precoce. Lets give it a few secs and try again...")
        #     return 'wait'

    async def switch_app(self):
        logger.info('Switching apps...')
        await self.key('APP_SWITCH')
        await self.tap('second_app_position')


    async def start(self):
        await self.p.set_device(self.args.device_id)

        with open('quest_list.txt', 'r') as file:
            quest_list = file.read().splitlines()

        actions_so_far = 0
        time_start = time_when_cooldown_ends = 0
        for num, quest in enumerate(quest_list, start=1):
            time_start = time.time()

            quest_coords = splitCoords(quest)
            logger.warning('Teleporting to quest number %s, coords: %s', num, quest_coords)
            await self.p.run(["adb", "-s", await self.p.get_device(), "shell", 'am start-foreground-service -a theappninjas.gpsjoystick.TELEPORT --ef lat {} --ef lng {}'.format(*quest_coords)])
            await asyncio.sleep(10)

            while await self.check_where_the_hell_are_we() is not 'on_world':
                # TODO: put something that checks that the pokestop is actually on top of the character
                logger.info("We still seem to be loading")
                continue

            while True:
                # TODO: needs to be separated into: open_pokestop and functions for each action.
                result = await self.spin_pokestop(time_when_cooldown_ends)
                if result == 'repeat':
                    await asyncio.sleep(5)
                    await self.swipe('spin_swipe', 800)
                    continue
                elif result == 'skip':
                    if args.action == 'trade':
                        actions_so_far += 1
                    else:
                        actions_so_far -= 1
                    break
                elif result == 'ok':
                    actions_so_far += 1
                    if actions_so_far >= args.num:
                        if args.action == 'trade':
                            await self.tap('character_menu_button')
                            await self.tap('friends_tab')
                            await self.tap('friend_position')
                            os.system('cd ../PGoTrader/ && ./trade.py --device-id=10.42.0.128 --stop-after 1 && cd ../PGoQuestr')
                            await asyncio.sleep(8)
                            await self.key('KEYCODE_BACK')
                            await self.key('KEYCODE_BACK')
                            await self.key('KEYCODE_BACK')
                            # await self.tap('x_button')
                            # await self.tap('x_button')

                        await asyncio.sleep(5)
                        # Finished, can claim quests
                        passed = False
                        while True:
                            await self.tap('quest_button')

                            if not passed:
                                storage_text = await self.cap_and_crop('claim_reward_box')
                                if any(word not in storage_text for word in ['CLAIM', 'REWARD']):
                                    logger.error('Does not look like we\'re in the right place...')
                                    await self.key('KEYCODE_BACK')
                                    continue
                                else:
                                    passed = True

                            claim_text = await self.cap_and_crop('claim_reward_box')
                            if any(word not in claim_text for word in ['CLAIM', 'REWARD']):
                                logger.error("Seems we finished!")
                                await self.key('KEYCODE_BACK')
                                break

                            logger.warning("Cool, we got another one! :D ")
                            await self.tap('claim_reward_box')
                            await self.tap('exit_encounter')

                        actions_so_far = 0

                    try:
                        next_quest = quest_list[num + 1]
                    except:
                        logger.critical("We ran out of coords! Bye!")
                        exit()
                    next_quest_coords = splitCoords(next_quest)
                    cooldown_until_next_stop = calculateCD(calculate(*quest_coords, *next_quest_coords)) * 60  # in seconds

                    # time_taken = time.time() - time_start
                    total_time_to_wait = max(5, cooldown_until_next_stop) * 1.10  # adds extra 10% and fixed 5 sec.
                    time_when_cooldown_ends = time.time() + total_time_to_wait
                    break




if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Pokemon go renamer')
    parser.add_argument('--device-id', type=str, default=None,
                        help="Optional, if not specified the phone is automatically detected. Useful only if you have multiple phones connected. Use adb devices to get a list of ids.")
    parser.add_argument('--config', type=str, default='config.yaml',
                        help="Config file location.")
    parser.add_argument('--action', type=str, default='spin',
                        help="Action to perform required by the particular quest type. Available options: Spin N PokeStops"),  #Trade X
    parser.add_argument('-n', '--num', type=int, default='1',
                        help="Number of times that the action must be performed to complete the quest (i.e.: the N on the options below)."
                        + "After the action is performed N times, the completed quest will be claimed, and the process starts again."),
    args = parser.parse_args()

    asyncio.run(Main(args).start())
