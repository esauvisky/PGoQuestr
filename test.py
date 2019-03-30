#!/usr/bin/env python3.7
import logging
import asyncio
from PIL import Image
import colorsys

from pokemonlib import PokemonGo
p = PokemonGo()

async def hue_affinity(hue1, hue2):
    '''Checks if the image's hue (i.e.: "main color")
    is closer to hue1 than to hue2. All values are in
    range 0-255, instead of the common 0-360 used for
    HSL and HSV images.

    Important: This takes in account that hue is a
               polar function, without the need for
               translating the values.

    Arguments:
        image {Image}   -- PIL.Image
        hue1  {int}     -- 0-255
        hue2  {int}     -- 0-255

    Returns:
        True if hue is closer to hue1
        False if closer to hue2
    '''
    image = await p.screencap()

    crop = image.crop([0, 2000, 1080, 2160])
    crop = crop.quantize(colors=1, kmeans=5)
    crop = crop.resize((1, 1))
    crop = crop.convert('HSV')
    pixel = crop.getpixel((0, 0))


    hue = pixel[0]
    print('Detected hue was: {}'.format(hue))

    ## Angles
    # The modulus simulates a polar function, everything
    # that would overflow 255 becomes the difference.
    a1 = abs(hue-hue1) % 255
    a2 = abs(hue-hue2) % 255


    if a1 < a2:
        # return True
        print( ((((a1 + hue) / hue) - 1) * 100, (((a2 + hue) / hue) - 1) * 100))
    if a2 < a1:
        print( ((((a1 + hue) / hue) - 1) * 100, (((a2 + hue) / hue) - 1) * 100))
    raise Exception("Well you got unlucky boy, it's right on the middle")

asyncio.run(hue_affinity(140, 200))
