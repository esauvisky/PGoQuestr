#!/usr/bin/env python3
# Author: Emi Bemol <esauvisky@gmail.com>

import re

# GPXpy Library
import gpxpy.geo

# GTK Stuff
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Notify', '0.7')
from gi.repository import Gtk, Gdk, Notify


# Colored STDOUT
CEND = '\033[0m'
CBOLD = '\033[1m'
CRED = '\033[91m'
CYELLOW = '\033[33m'
CGREEN = '\033[32m'
CBLUE = '\033[34m'


def prettifyCoord(coord, n=6):
    '''Prettifies a coordinate into a beautiful string.

    Arguments:
        coord {[float, float]} -- Pair of latitude and longitude.
    Keyword Arguments:
        n {int} -- Number of decimal places after the period (default: 6).
    Returns:
        string -- Formatted string of the lat-long pair.
    '''
    try:
        if isinstance(coord[0], float) and isinstance(coord[1], float):
            return str(format(coord[0], '.' + str(n) + 'f') + ',' + format(coord[1], '.' + str(n) + 'f'))
    except Exception as e:
        return False


def newClipboardDetected(*args):
    '''Fires everytime the Gnome clipboard changes.

    Function that handles clipboard changes and stores coordinates.
    When it finds a new coordinate, compares it with the previous one,
    then, notifies the user with the proper cooldown.
    '''
    global lastCoord
    cooldown = 0
    currentCoord = splitCoords(clip.wait_for_text())
    if currentCoord is not False:
        try:
            dist = calculate(lastCoord[0], lastCoord[1], currentCoord[0], currentCoord[1])
        except Exception as e:
            if 'lastCoord' not in globals():
                print('First coordinate detected.\n')
            else:
                print(CRED + 'Some unknown error happened!\nPlease copy below and report it to @esauvisky or open an issue on GitHub. Thanks!')
                print(e)
                exit()
        else:
            cooldown = calculateCD(dist)

            # If the same coord was copied twice in a row, the user wants a timer
            if dist == 0:
                # TODO: set timer
                return

            # Sets the colors in one beautiful single line
            color = CGREEN if cooldown < 10 else CYELLOW if cooldown < 30 else CRED

            # stdout
            print("Last coordinate was: " + CBLUE + prettifyCoord(lastCoord) + CEND)
            print("New coordinate is:   " + CBLUE + prettifyCoord(currentCoord) + CEND)
            print("Cooldown is " + CBOLD + color + str(cooldown) + ' minutes' + CEND + ' (' + str(dist) + 'km)')
            print('--------------------------------------------')

            # and libnotify
            notification = Notify.Notification.new(str(cooldown) + ' minutes ' + '(' + str(dist) + 'km)',
                                                   'From: ' + prettifyCoord(lastCoord, 3) +
                                                   '\nTo: ' + prettifyCoord(currentCoord, 3))
            notification.set_urgency(1)
            notification.show()

        lastCoord = currentCoord


def splitCoords(text):
    '''Splits a string that represents a coordinate into a list of floats

    Arguments:
        text {string} -- The lat/long pair in string format, e.g.: ' 35.281374, 139.663600  '

    Returns:
        list -- A pair of floats, one for latitude and one for longitude.
        boolean -- False, if not a valid coordinate.
    '''
    try:
        match = re.search('^https://maps.google.com/maps\?q=(.+)$', text)
        if match:
            coord = match[1]
            coord = [float(x.strip()) for x in coord.split(',')]
        else:
            coord = [float(x.strip()) for x in text.split(',')]
        if not isinstance(coord[0], float) or not isinstance(coord[1], float):
            raise 'Not a coordinate'
    except:
        return False
    else:
        return coord


def calculate(lat1, lon1, lat2, lon2):
    '''Calculates the Harvesian distance between two coordinates

    Returns:
        float -- The distance in kilometers, rounded to two decimal places.
    '''
    dist = gpxpy.geo.haversine_distance(lat1, lon1, lat2, lon2)
    dist = dist / 1000
    dist = round(dist, 2)
    return dist


def calculateCD(dist):
    time = 0
    if dist >= 1500:
        time = 120
    elif dist >= 1403 and dist < 1500:
        time = 120
    elif dist >= 1344 and dist < 1403:
        time = 119
    elif dist >= 1300 and dist < 1344:
        time = 117
    elif dist >= 1221 and dist < 1300:
        time = 112
    elif dist >= 1180 and dist < 1221:
        time = 109
    elif dist >= 1020 and dist < 1180:
        time = 101
    elif dist >= 1007 and dist < 1020:
        time = 97
    elif dist >= 948 and dist < 1007:
        time = 94
    elif dist >= 897 and dist < 948:
        time = 90
    elif dist >= 839 and dist < 897:
        time = 88
    elif dist >= 802 and dist < 839:
        time = 83
    elif dist >= 751 and dist < 802:
        time = 81
    elif dist >= 700 and dist < 751:
        time = 76
    elif dist >= 650 and dist < 700:
        time = 73
    elif dist >= 600 and dist < 650:
        time = 69
    elif dist >= 550 and dist < 600:
        time = 65
    elif dist >= 500 and dist < 550:
        time = 61
    elif dist >= 450 and dist < 500:
        time = 58
    elif dist >= 400 and dist < 450:
        time = 54
    elif dist >= 350 and dist < 400:
        time = 49
    elif dist >= 328 and dist < 350:
        time = 48
    elif dist >= 300 and dist < 328:
        time = 46
    elif dist >= 250 and dist < 300:
        time = 41
    elif dist >= 201 and dist < 250:
        time = 36
    elif dist >= 175 and dist < 201:
        time = 33
    elif dist >= 150 and dist < 175:
        time = 31
    elif dist >= 125 and dist < 150:
        time = 28
    elif dist >= 100 and dist < 125:
        time = 26
    elif dist >= 90 and dist < 100:
        time = 24
    elif dist >= 80 and dist < 90:
        time = 23
    elif dist >= 70 and dist < 80:
        time = 22
    elif dist >= 60 and dist < 70:
        time = 21
    elif dist >= 50 and dist < 60:
        time = 20
    elif dist >= 45 and dist < 50:
        time = 19
    elif dist >= 40 and dist < 45:
        time = 18
    elif dist >= 35 and dist < 40:
        time = 17
    elif dist >= 30 and dist < 35:
        time = 16
    elif dist >= 25 and dist < 30:
        time = 14
    elif dist >= 20 and dist < 25:
        time = 11
    elif dist >= 15 and dist < 20:
        time = 8
    elif dist >= 10 and dist < 15:
        time = 6
    elif dist >= 6 and dist < 10:
        time = 4
    elif dist >= 5 and dist < 6:
        time = 3
    elif dist >= 4 and dist < 5:
        time = 2
    elif dist >= 3 and dist < 4:
        time = 2
    elif dist >= 2 and dist < 3:
        time = 1
    elif dist >= 1 and dist < 2:
        time = 0.8

    return time


if __name__ == "__main__":
    # Initializes the Notify instance
    Notify.init('CoolmDown')
    print(CBOLD + CGREEN + "Keep me cool you dirty spoofer!" + CEND)
    clip = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
    clip.connect('owner-change', newClipboardDetected)
    Gtk.main()
    Notify.uninit()
