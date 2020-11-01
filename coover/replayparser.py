import struct
import lzma
from enum import Enum, IntFlag, unique 

@unique
class GameMode(Enum):
    Standard = 0
    Taiko = 1
    CatchTheBeat = 2
    Osumania = 3


@unique
class Mods(IntFlag):
    NOMOD       = 0
    NOFAIL      = 1 << 0
    EASY        = 1 << 1
    TOUCHSCREEN = 1 << 2 # old: 'NOVIDEO'
    HIDDEN      = 1 << 3
    HARDROCK    = 1 << 4
    SUDDENDEATH = 1 << 5
    DOUBLETIME  = 1 << 6
    RELAX       = 1 << 7
    HALFTIME    = 1 << 8
    NIGHTCORE   = 1 << 9
    FLASHLIGHT  = 1 << 10
    AUTOPLAY    = 1 << 11
    SPUNOUT     = 1 << 12
    AUTOPILOT   = 1 << 13
    PERFECT     = 1 << 14
    KEY4        = 1 << 15
    KEY5        = 1 << 16
    KEY6        = 1 << 17
    KEY7        = 1 << 18
    KEY8        = 1 << 19
    FADEIN      = 1 << 20
    RANDOM      = 1 << 21
    CINEMA      = 1 << 22
    TARGET      = 1 << 23
    KEY9        = 1 << 24
    KEYCOOP     = 1 << 25
    KEY1        = 1 << 26
    KEY3        = 1 << 27
    KEY2        = 1 << 28
    SCOREV2     = 1 << 29
    MIRROR      = 1 << 30

    SPEED_CHANGING = DOUBLETIME | NIGHTCORE | HALFTIME

# Byte     Game mode of the replay (0 = osu! Standard, 1 = Taiko, 2 = Catch the Beat, 3 = osu!mania)
# Integer  Version of the game when the replay was created (ex. 20131216)
# String   osu! beatmap MD5 hash
# String   Player name
# String   osu! replay MD5 hash (includes certain properties of the replay)
# Short    Number of 300s
# Short    Number of 100s in standard, 150s in Taiko, 100s in CTB, 100s in mania
# Short    Number of 50s in standard, small fruit in CTB, 50s in mania
# Short    Number of Gekis in standard, Max 300s in mania
# Short    Number of Katus in standard, 200s in mania
# Short    Number of misses
# Integer  Total score displayed on the score report
# Short    Greatest combo displayed on the score report
# Byte     Perfect/full combo (1 = no misses and no slider breaks and no early finished sliders)
# Integer  Mods used. See below for list of mod values.
# String   Life bar graph: comma separated pairs u/v, where u is the time in milliseconds into the song and v is a floating point
#          value from 0 - 1 that represents the amount of life you have at the given time (0 = life bar is empty, 1= life bar is full)
# Long     Time stamp (Windows ticks)
# Integer  Length in bytes of compressed replay data
# LZMA     Compressed replay data (ask cmyui)
# Long     Online Score ID
# Double   Additional mod information. Only present if Target Practice is enabled.

class Replay:
	def __init__(self, data: bytes) -> None:
		self._data = data
		self.offset = 0
		self.game_mode = None
		self.game_version = None
		self.beatmap_md5 = None
		self.replay_md5 = None
		self.player = None
		self.count300 = None
		self.count100 = None
		self.count50 = None
		self.gekis = None
		self.katus = None
		self.miss = None
		self.totalscore = None
		self.combo = None
		self.perfect = None
		self.mods = None
		self.barGraph = None
		self.timestamp = None
		self.scoreid = None
		self.additional_mods= None
		self.frames = None
		self.parse()
	
	@property
	def data(self):
		return self._data[self.offset:]
	
	def parse(self) -> None:
		self.game_mode = self.read_byte()
		self.game_version = self.read_int()
		self.beatmap_md5 = self.read_string()
		self.player = self.read_string()
		self.replay_md5 = self.read_string()
		self.count300 = self.read_short()
		self.count100 = self.read_short()
		self.count50 = self.read_short()
		self.gekis = self.read_short()
		self.katus = self.read_short()
		self.miss = self.read_short()
		self.totalscore = self.read_int()
		self.combo = self.read_short()
		self.perfect = self.read_byte()
		self.mods = self.read_int()
		self.barGraph = self.read_string()
		self.timestamp = self.read_long_long()
		self.frames = lzma.decompress(self.read_raw(self.read_int())).decode().split(',')	
		self.scoreid = self.read_long_long()
		self.additional_mods = (self.mods & Mods.TARGET and self.read_double()) or None
	
	def read_byte(self) -> int:
		format_specifer = '<b'
		val, = struct.unpack(format_specifer, self.data[:1])
		self.offset += 1
		return val

	def read_short(self) -> int:
		format_specifer = '<h'
		val, = struct.unpack(format_specifer, self.data[:2])
		self.offset += 2
		return val

	def read_int(self) -> int:
		format_specifer = '<i'
		val, = struct.unpack(format_specifer, self.data[:4])
		self.offset += 4
		return val

	def read_long_long(self) -> int:
		format_specifer = '<q' # really peppys
		val, = struct.unpack(format_specifer, self.data[:8])
		self.offset += 8
		return val

	def read_double(self) -> int:
		format_specifer = '<d'
		val, = struct.unpack(format_specifer, self.data[:8])
		self.offset += 8
		return val

	def read_uleb128(self) -> int:
		val = shift = 0

		while True:
			b = self.data[0]
			self.offset += 1

			val |= ((b & 0b01111111) << shift)
			if (b & 0b10000000) == 0:
				break


			shift += 7

		return val

	def read_string(self) -> str:
		if self.read_byte() == 0x0b:
 			return self.read_raw(self.read_uleb128()).decode()

		return ''

	def read_raw(self, length: int) -> bytes:
		val = self.data[:length]
		self.offset += length
		return val