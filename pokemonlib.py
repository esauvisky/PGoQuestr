from io import BytesIO
from PIL import Image
import asyncio
import logging
import subprocess
import re
from colorlog import ColoredFormatter


logger = logging.getLogger('PokemonGo')
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
formatter = ColoredFormatter("  %(log_color)s%(levelname)-8s%(reset)s | %(log_color)s%(message)s%(reset)s")
ch.setFormatter(formatter)
logger.addHandler(ch)

RE_CLIPBOARD_TEXT = re.compile(r"^./ClipboardReceiver\(\s*\d+\): Clipboard text: (.+)$")

class CalcyIVError(Exception):
    # logger.error('CalcyIV did not find any combinations.')
    pass

class RedBarError(Exception):
    # logger.error('The red bar is covering the pokémon CP.')
    pass

class PhoneNotConnectedError(Exception):
    # logger.error('Your phone does not appear to be connected. Try \'adb devices\' and see if it is listed there :)')
    pass

class LogcatNotRunningError(Exception):
    # logger.error('For some reason, I can\'t run the logcat on your phone! :( Try to run \'adb logcat\' and see if something happens. Message the developers as well!')
    pass

class PokemonGo(object):
    def __init__(self):
        self.device_id = None
        self.calcy_pid = None
        self.use_fallback_screenshots = False

    async def screencap(self):
        if not self.use_fallback_screenshots:
            return_code, stdout, stderr = await self.run(["adb", "-s", await self.get_device(), "exec-out", "screencap", "-p"])
            try:
                return Image.open(BytesIO(stdout))
            except (OSError, IOError):
                logger.debug("Screenshot failed, using fallback method")
                # self.use_fallback_screenshots = True
        return_code, stdout, stderr = await self.run(["adb", "-s", await self.get_device(), "shell", "screencap", "-p", "/sdcard/screen.png"])
        return_code, stdout, stderr = await self.run(["adb", "-s", await self.get_device(), "pull", "/sdcard/screen.png", "."])
        image = Image.open("screen.png")
        return image

    async def set_device(self, device_id=None):
        self.device_id = device_id

    async def get_device(self):
        if self.device_id:
            return self.device_id
        devices = await self.get_devices()
        if devices == []:
            raise PhoneNotConnectedError
        self.device_id = devices[0]
        return self.device_id

    async def run(self, args):
        logger.info("Running %s", args)
        p = subprocess.Popen([str(arg) for arg in args], stdout=subprocess.PIPE)
        stdout, stderr = p.communicate()
        logger.debug("Return code %d", p.returncode)
        return (p.returncode, stdout, stderr)

    async def get_devices(self):
        code, stdout, stderr = await self.run(["adb", "devices"])
        devices = []

        for line in stdout.decode('utf-8').splitlines()[1:-1]:
            device_id, name = line.split('\t')
            devices.append(device_id)
        return devices

    async def start_logcat(self):
        # return_code, stdout, stderr = await self.run(["adb", "-s", await self.get_device(), "shell", "pidof", "-s", "tesmath.calcy"])
        # logger.info("Running pidof calcy got code %d: %s", return_code, stdout)
        # self.calcy_pid = stdout.decode('utf-8').strip()
        # cmd = ["adb", "-s", await self.get_device(), "logcat", "-T", "1", "-v", "brief", "--pid", self.calcy_pid]
        cmd = ["adb", "-s", await self.get_device(), "logcat", "-T", "1", "-v", "brief"]
        logger.info("Starting logcat %s", cmd)
        self.logcat_task = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await self.logcat_task.stdout.readline() # Read and discard the one line as -T 0 doesn't work

    async def seek_to_end(self):
        # Seek to the end of the file
        while True:
            try:
                task = await asyncio.wait_for(self.logcat_task.stdout.readline(), 0.2)
            except asyncio.TimeoutError:
                break

    async def read_logcat(self):
        if self.logcat_task.returncode != None:
            logger.error("Logcat process is not running")
            logger.error("stdout %s", await self.logcat_task.stdout.read())
            logger.error("stderr %s", await self.logcat_task.stderr.read())
            raise LogcatNotRunningError()

        line = await self.logcat_task.stdout.readline()
        line = line.decode('utf-8', errors='ignore').rstrip()
        #while line.split()[2].decode('utf-8') != self.calcy_pid:
        #    line = await self.logcat_task.stdout.readline()
        #logger.debug("Received logcat line: %s", line)
        return line

    async def get_clipboard(self):
        await self.send_intent("clipper.get")
        while True:
            line = await self.read_logcat()
            match = RE_CLIPBOARD_TEXT.match(line)
            if match:
                logger.info("RE_CLIPBOARD_TEXT matched.")
                return match.group(1)

    async def send_intent(self, intent, package=None, extra_values=[]):
        cmd = "am broadcast -a {}".format(intent)
        if package:
            cmd = cmd + " -n {}".format(package)
        for key, value in extra_values:
            if isinstance(value, bool):
                cmd = cmd + " --ez {} {}".format(key, "true" if value else "false")
            elif '--user' in key:
                cmd = cmd + " --user {}".format(value)
            else:
                cmd = cmd + " -e {} '{}'".format(key, value)
        logger.info("Sending intent: " + cmd)
        await self.run(["adb", "-s", await self.get_device(), "shell", cmd])

    async def tap(self, x, y):
        await self.run(["adb", "-s", await self.get_device(), "shell", "input", "tap", x, y])

    async def key(self, key):
        await self.run(["adb", "-s", await self.get_device(), "shell", "input", "keyevent", key])

    async def text(self, text):
        await self.run(["adb", "-s", await self.get_device(), "shell", "input", "text", text])

    async def swipe(self, x1, y1, x2, y2, duration=None):
        args = [
            "adb",
            "-s",
            await self.get_device(),
            "shell",
            "input",
            "swipe",
            x1,
            y1,
            x2,
            y2
        ]
        if duration:
            args.append(duration)
        await self.run(args)
