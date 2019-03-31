#!/usr/bin/env python3.7
import logging
import asyncio
from PIL import Image
import colorsys

from pokemonlib import PokemonGo
p = PokemonGo()

async def hue_affinity(hue1, hue2):
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
    im = await p.screencap()
    im = im.crop([240, 1958, 290, 1985])
    # im = im.quantize()
    im = im.quantize()
    im.show()
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


    logging.info('Detected H:%s (%i%% of H1: %s | %i%% of H2: %s)', hue, a1, hue1, a2, hue2)

    if a1 < a2:
        return True
        # return ((((a1 + hue) / hue) - 1) * 100, (((a2 + hue) / hue) - 1) * 100)
    if a2 < a1:
        return False
        # return ((((a1 + hue) / hue) - 1) * 100, (((a2 + hue) / hue) - 1) * 100)
        raise Exception("Well you got unlucky boy, it's right on the middle")

asyncio.run(hue_affinity(130, 200))
