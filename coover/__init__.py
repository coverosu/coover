"""\
This package is mainly for people who want to code with python around osu, but doesn't want to write anything
Using this packag for code that I tend to rewrite a lot such as `requests` type code.
"""

__title__ = 'coover'
__author__ = 'coverosu'
__license__ = 'MIT'
__copyright__ = 'Copyright 2020 coverosu'
__version__ = '0.1'

from .OsuAPIWrapper import *
from .Beatmap import *
from .OsuApiV2 import *
from .replayparser import *