from typing import Union, Set, Tuple
import requests	
import re
from collections import defaultdict
from enum import Enum, unique

@unique
class Server(Enum):
	Bancho = 'https://osu.ppy.sh/api'
	Akatsuki = 'https://akatsuki.pw/api/v1'
	Ripple = 'https://ripple.moe/api/v1'
	Gatari = 'https://api.gatari.pw'

	def __init__(self, *args, **kwargs) -> None:
		# make `self.url` a reference of `self.value`
		self.url = self.value

regexes = {
	'beatmap': re.compile(
		r'https?://(?:osu\.(?:ppy\.sh|gatari\.pw)|ripple\.moe|akatsuki\.pw)'
		r'/(?P<type>b|d|beatmapset)/(?P<id>\d{1,10})'
	)
}

class OsuAPIWrapper:
	def __init__(self, api_key: str) -> None:
		"""
		Hello!
		This class allows you to get the following
		recent scores | best scores | scores | beatmap info | mapid's | user's stats
		Coolest thing about this is, it returns the same formatted dictionary for the servers supported.
		Remember that this is still a working progress!
		TODO:
			Move to bancho api v2 at some point
			Accuracy on bancho for modes like Catch the Beat and Mania
		This is how you can use this class!
		------------------------
		from coover import OsuAPIWrapper
		with OsuAPIWrapper(api_key='abc123') as osu:
			stats = osu.profile('[Cover]')
		if not stats:
			print('No stats found!')
		else:
			for k, v in stats.items():
				print(f'{k}: {v}')
		------------------------
		To get more information about each function, you can simply do
		------------------------
		from coverosu import OsuAPIWrapper
		osu = OsuAPIWrapper()
		print(osu.profile.__doc__)
		------------------------
		"""
		self.api_key = api_key
		self.http_sess = requests.Session()

	def __enter__(self):
		return self

	def __exit__(self):
		self.http_sess.close()

	@staticmethod
	def resolve(server_name: str) -> Server:
		# resolve a server by it's name.
		return defaultdict(lambda: None, {
			'bancho': Server.Bancho,
			'akatsuki': Server.Akatsuki,
			'ripple': Server.Ripple,
			'gatari': Server.Gatari
		})[server_name.strip().lower()]

	def get_mapids(self, s: str) -> Tuple[Set[int], Set[int]]:
		"""
		Parses `s` for beatmap url links, returning all map & set ids.
		Such as "https://akatsuki.pw/b/123 guys check out my map!".
		This function returns a list of all the ids provided. (Removes duplicates!)
		Note that this doesn't determine if an id is a set or an individual map.
		"""

		ids = set_ids = set()

		for m in regexes['beatmap'].findall(s):
			# add to beatmap id set, or beatmap set id set
			# depending on the type of the url link (b/d/beatmapset).
			appr_set = ids if m['type'] == 'b' \
				  else set_ids

			appr_set.add(int(m['id']))

		return (ids, set_ids)

	def get_beatmap(self, map_or_set_id: int, mode: int = 0, is_set: bool = False):
		"""
		Gets beatmap information from the beatmap ID.
		Required:
			map_or_set_id: Either a beatmap id, or a beatmap set_id, depending on is_set param.
		Optional:
			is_set: Whether `map_or_set_id` should be interpreted as a set id.
			mode: 0 is std, 1 is taiko, 2 is ctb, 3 is mania
		"""
		params = {
			'k': self.api_key,
			'm': mode,
			's' if is_set else 'b': map_or_set_id,
			'a': 1
		}

		r = self.http_sess.get('https://osu.ppy.sh/api/get_beatmaps', params=params)

		if not r or r.status_code != 200:
			return

		if not (json := r.json()):
			return

		return json

	def get_score(self, user: int, beatmapid: int,
				  mode: int = 0, relax: bool = False, limit: int = 0, server_name: str = 'bancho'):
		"""
		Get a user's score a on specified beatmap.
		Required:
			user: Either the player's userid, or name.
			beatmapid: The map's id. (e.g, 2514777 in https://akatsuki.pw/b/2514777)
		Optional:
			mode: game mode as an integer. (0-3)
			relax: (rx servers only) whether you'd like to search for relax scores. (T/F)
			limit: offset from the user's best play on the map. (1 for second best play, etc.)
		"""
		server_name = self.resolve(server_name)
		if not server_name:
			raise ValueError(f'Could not find api named "{server_name}"!')

		# since we'll need the userid for things
		# like the user's avatar, we might as well
		# just use it for everything for simplicity.

		path = ''
		params = {}

		if server_name == Server.Bancho:
			params = {
				'k': self.api_key,
				'b': beatmapid,
				'u': user,
				'm': mode,
				'type': 'id'
			}

			path = 'get_scores'
		elif server_name == Server.Akatsuki:
			params = {
				'u': user,
				'm': mode,
				'rx': int(relax),
				'b': beatmapid
			}

			path = 'get_scores'
		elif server_name == Server.Ripple:
			params = {
				'u': user,
				'mode': mode,
				'relax': int(relax),
				'b': beatmapid
			}

			path = 'get_scores'
		elif server_name == Server.Gatari:
			params = {
				'u': user,
				'mode': mode,
				'b': beatmapid
			}

			path = 'beatmap/user/score'

		r = self.http_sess.get(f'{server_name.url}/{path}', params=params)
		if not r or r.status_code != 200:
			return

		json = r.json()
		if not json:
			return
		return json

	def profile(self, user: Union[str, int],
	            mode: int = 0, relax: int = 0, server_name: str = 'bancho'):
		"""
		Gets a user's stats
		Required:
			user: Either the user ID, or username of the player.
		Optional:
			relax: 1 if you want a relax score (only supported on relax servers) and 0 if you don't
			mode: 0 is std, 1 is taiko, 2 is ctb, 3 is mania
		"""
		server_name = self.resolve(server_name)
		if not server_name:
			raise ValueError(f'Could not find api named "{server_name}"!')

		if server_name == Server.Bancho:
			params = {
				'k': self.api_key,
				'u': user,
				'm': mode,
				'type': 'id' if isinstance(user, int) else 'string'
			}

			r = self.http_sess.get(f"{server_name.url}/get_user", params=params)
			if not r or r.status_code != 200:
				return

			json = r.json()
			if not json:
				return
			return json

		elif server_name == Server.Akatsuki:
			params = {
				'id' if isinstance(user, int) else 'name': user,
				'm': mode,
			}

			r = self.http_sess.get(f"{server_name.url}/users/full", params=params)
			if not r or r.status_code != 200:
				return

			stats = r.json()
			if not stats:
				return
			return stats


		elif server_name == Server.Ripple:
			params = {
				'id' if isinstance(user, int) else 'name': user,
				'm': mode,
				'relax': relax
			}

			r = self.http_sess.get(f"{server_name.url}/users/full", params=params)
			if not r or r.status_code != 200:
				return

			stats = r.json()
			if not stats:
				return

			return stats

		elif server_name == Server.Gatari:
			params = {
				'u': user,
			}

			r = self.http_sess.get(f"{server_name.url}/users/get", params=params)
			if not r or r.status_code != 200:
				return

			userinfo = r.json()
			params = {
				'u': user,
				'mode': mode
			}

			r = self.http_sess.get(f"{server_name.url}/user/stats", params=params)
			if not r or r.status_code != 200:
				return

			stats = r.json()
			if not stats:
				return

			return userinfo, stats

	def recent_score(self, user: Union[str, int], mode: int = 0,
	                 relax: int = 0, limit: int = 0, server_name: str = 'bancho'):
		"""
		Gets a user's recent score
		Required:
			user: Either the user ID, or username of the player.
		Optional:
			relax: 1 if you want a relax score (only supported on relax servers) and 0 if you don't
			mode: 0 is std, 1 is taiko, 2 is ctb, 3 is mania
			limit: If a user has multiple scores on a map, you can literate through them using this! Setting limit to 1 will get the user's 2nd best play on the map
		"""
		server_name = self.resolve(server_name)
		if not server_name:
			raise ValueError(f'Could not find api named "{server_name}"!')
		
		if server_name == Server.Bancho:
			params = {
				'k': self.api_key,
				'u': user,
				'm': mode,
				'type': 'id' if isinstance(user, int) else 'string'
			}

			r = self.http_sess.get(f"{server_name.url}/get_user_recent", params=params)
			if not r or r.status_code != 200:
				return

			json = r.json()
			if not json:
				return

			return json

		elif server_name == Server.Akatsuki:
			params = {
				'id' if isinstance(user, int) else 'name': user,
				'mode': mode,
				'rx': relax
			}

			r = self.http_sess.get(f"{server_name.url}/users/scores/recent", params=params)
			if not r or r.status_code != 200:
				return

			json = r.json()
			if not json:
				return

			return json

		elif server_name == Server.Ripple:
			params = {
				'id' if isinstance(user, int) else 'name': user,
				'm': mode,
				'relax': relax
			}

			r = self.http_sess.get(f"{server_name.url}/users/scores/recent", params=params)
			if not r or r.status_code != 200:
				return

			json = r.json()
			if not json:
				return

			return json

		elif server_name == Server.Gatari:
			params = {
				'id': self.profile(user, server_name=server_name)['userid'] if isinstance(user, str) else user,
				'mode': mode,
				'f': 0
			}

			r = self.http_sess.get(f"{server_name.url}/user/scores/recent", params=params)
			if not r or r.status_code != 200:
				return

			json = r.json()
			if not json:
				return

			return json

	def best_score(self, user: Union[str, int], mode: int = 0,
	               relax: int = 0, limit: int = 0, server_name: str = 'bancho'):
		"""
		Gets a user's best score
		Required:
			user: Either the user ID, or username of the player.
		Optional:
			relax: 1 if you want a relax score (only supported on relax servers) and 0 if you don't
			mode: 0 is std, 1 is taiko, 2 is ctb, 3 is mania
			limit: If a user has multiple scores on a map, you can literate through them using this! Setting limit to 1 will get the user's 2nd best play on the map
		"""
		server_name = self.resolve(server_name)
		if not server_name:
			raise ValueError(f'Could not find api named "{server_name}"!')
		
		if server_name == Server.Bancho:
			params = {
				'k': self.api_key,
				'u': user,
				'm': mode,
				'type': 'id' if isinstance(user, int) else 'string'
			}

			r = self.http_sess.get(f"{server_name.url}/get_user_best", params=params)
			if not r or r.status_code != 200:
				return

			json = r.json()
			if not json:
				return

			return json

		elif server_name == Server.Akatsuki:
			params = {
				'id' if isinstance(user, int) else 'name': user,
				'mode': mode,
				'rx': relax
			}

			r = self.http_sess.get(f"{server_name.url}/users/scores/best", params=params)
			if not r or r.status_code != 200:
				return

			json = r.json()
			if not json:
				return

			return json

		elif server_name == Server.Ripple:
			params = {
				'id' if isinstance(user, int) else 'name': user,
				'm': mode,
				'relax': relax
			}

			r = self.http_sess.get(f"{server_name.url}/users/scores/best", params=params)
			if not r or r.status_code != 200:
				return

			json = r.json()
			if not json:
				return

			return json

		elif server_name == Server.Gatari:
			params = {
				'id': self.profile(user, server_name=server_name)['userid'] if isinstance(user, str) else user,
				'mode': mode,
			}

			r = self.http_sess.get(f"{server_name.url}/user/scores/best", params=params)
			if not r or r.status_code != 200:
				return

			json = r.json()
			if not json:
				return

			return json