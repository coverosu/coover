from typing import Union, Set, Tuple
import requests
import re
from enum import Enum, IntFlag, unique
from collections import defaultdict
from enumm import *
from Beatmap import Beatmap

regexes = {
	'beatmap': re.compile(
		r'https?://(?:osu\.(?:ppy\.sh|gatari\.pw)|ripple\.moe|akatsuki\.pw)'
		r'/(?P<type>b|d|beatmapset)/(?P<id>\d{1,10})'
	)
}

GAMEMODES = ('std', 'taiko', 'ctb', 'mania')

GRADE_URLS = {
	'SSH': 'https://cdn.discordapp.com/emojis/724849277406281728.png?v=1',
	'SH': 'https://cdn.discordapp.com/emojis/724847645142810624.png?v=1',
	'SS': 'https://cdn.discordapp.com/emojis/724849299300548680.png?v=1',
	'S': 'https://cdn.discordapp.com/emojis/724847668953874493.png?v=1',
	'A': 'https://cdn.discordapp.com/emojis/724841194517037137.png?v=1',
	'B': 'https://cdn.discordapp.com/emojis/724841229602521109.png?v=1',
	'C': 'https://cdn.discordapp.com/emojis/724841244530049095.png?v=1',
	'D': 'https://cdn.discordapp.com/emojis/724841263727116379.png?v=1'
}

def calc_acc(mode: int, n300: int, n100: int, n50: int,
			 nmiss: int, nkatu: int = 0, ngeki: int = 0) -> float:
	if mode == 0:
		# osu!std
		total = sum((n300, n100, n50, nmiss))

		return 100.0 * sum((
			n300 * 300.0,
			n100 * 100.0,
			n50 * 50.0
		)) / (total * 300.0)

	elif mode == 1:
		# osu!taiko
		total = sum((n300, n100, nmiss))

		return 100.0 * sum((
			n300 * 300.0,
			n100 * 150.0
		)) / (total * 300.0)

	elif mode == 2:
		# osu!catch
		return 0.0

	elif mode == 3:
		# osu!mania
		return 0.0

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

	def map_completion_percentage(self, beatmapid, totalhits = 0) -> float:
		if not totalhits or not beatmapid:
			return 0.0
		_beatmap = self.http_sess.get(f"https://osu.ppy.sh/osu/{beatmapid}")
		if not _beatmap or _beatmap.status_code != 200:
			return 0.0
		beatmap =  Beatmap(_beatmap.text)
		beatmap.parse()
		beatmap_total_objects = len(beatmap.hit_objects)
		return round(totalhits / beatmap_total_objects * 100, 2)

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

		return r.json()[0]

	def get_score(self, user: Union[str, int], beatmapid: int,
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
		if isinstance(user, int):
			# user is an id
			user_id = user
		else:
			# user is a name
			p = self.profile(user)
			if not p:
				return

			user_id = p['userid']

		path = ''
		avatar_url = ''
		params = {}

		if server_name == Server.Bancho:
			params = {
				'k': self.api_key,
				'b': beatmapid,
				'u': user_id,
				'm': mode,
				'type': 'id'
			}

			path = 'get_scores'
			avatar_url = f'https://s.ppy.sh/a/{user_id}'
		elif server_name == Server.Akatsuki:
			params = {
				'u': user_id,
				'm': mode,
				'rx': int(relax),
				'b': beatmapid
			}

			path = 'get_scores'
			avatar_url = f'https://a.akatsuki.pw/{user_id}'
		elif server_name == Server.Ripple:
			params = {
				'u': user_id,
				'mode': mode,
				'relax': int(relax),
				'b': beatmapid
			}

			path = 'get_scores'
			avatar_url = f'https://a.ripple.moe/{user_id}'
		elif server_name == Server.Gatari:
			params = {
				'u': user_id,
				'mode': mode,
				'b': beatmapid
			}

			path = 'beatmap/user/score'
			avatar_url = f'https://a.gatari.pw/{user_id}'

		r = self.http_sess.get(f'{server_name.url}/{path}', params=params)
		if not r or r.status_code != 200:
			return

		json = r.json()
		if not json:
			return

		stats = json[limit - 1 if limit > 0 else limit]

		b = self.get_beatmap(beatmapid)
		if not b:
			return

		acc = calc_acc(mode, int(stats['count300']), int(stats['count100']),
							 int(stats['count50']), int(stats['countmiss']))

		return {
			'beatmap_id': beatmapid,
			'beatmapset_id': b['beatmapset_id'],
			'artist': b['artist'],
			'title': b['title'],
			'version': b['version'],
			'ar': b['diff_approach'],
			'od': b['diff_overall'],
			'difficultyrating': float(b['difficultyrating']),
			'score': stats['score'],
			'maxcombo': stats['maxcombo'],
			'fullcombo': b['max_combo'],
			'count_50': stats['count50'],
			'count_100': stats['count100'],
			'count_300': stats['count300'],
			'pp': float(stats['pp']) if stats['pp'] != '0' else 0.0,
			'count_miss': stats['countmiss'],
			'enabled_mods': repr(Mods(stats['enabled_mods'])),
			'intmods': int(stats['enabled_mods']),
			'rank': GRADE_URLS[stats['rank']] if GRADE_URLS else stats['rank'],
			'accuracy': acc,
			'avatar_url': avatar_url
		}

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

			stats = json[0]

			return {
				'userid': stats['user_id'],
				'username': stats['username'],
				'join_date': stats['join_date'],
				'global_rank': stats['pp_rank'],
				'playcount': stats['playcount'],
				'ranked_score': stats['ranked_score'],
				'total_score': stats['total_score'],
				'level': float(stats['level']),
				'pp': float(stats['pp_raw']),
				'accuracy': float(stats['accuracy']),
				'country': stats['country'],
				'country_rank': stats['pp_country_rank'],
				'avatar_url': "https://s.ppy.sh/a/" + str(stats['user_id'])
			}

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

			game_stats = stats['stats'][relax][GAMEMODES[mode]]
			return {
				'userid': stats['id'],
				'username': stats['username'],
				'join_date': stats['registered_on'],
				'global_rank': game_stats['global_leaderboard_rank'],
				'playcount': game_stats['playcount'],
				'ranked_score': game_stats['ranked_score'],
				'total_score': game_stats['total_score'],
				'level': float(game_stats['level']),
				'pp': game_stats['pp'],
				'accuracy': float(game_stats['accuracy']),
				'country': stats['country'],
				'country_rank': game_stats['country_leaderboard_rank'],
				'avatar_url': "https://a.akatsuki.pw/" + str(stats['id'])
			}

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

			game_stats = stats[GAMEMODES[mode]]
			return {
				'userid': stats['id'],
				'username': stats['username'],
				'join_date': stats['registered_on'],
				'global_rank': game_stats['global_leaderboard_rank'],
				'playcount': game_stats['playcount'],
				'ranked_score': game_stats['ranked_score'],
				'total_score': game_stats['total_score'],
				'level': float(game_stats['level']),
				'pp': game_stats['pp'],
				'accuracy': float(game_stats['accuracy']),
				'country': stats['country'],
				'country_rank': game_stats['country_leaderboard_rank'],
				'avatar_url': "https://a.ripple.moe/" + str(stats['id'])
			}

		elif server_name == Server.Gatari:
			params = {
				'u': user,
			}

			r = self.http_sess.get(f"{server_name.url}/users/get", params=params)
			if not r or r.status_code != 200:
				return

			userinfo = r.json()['users'][0]
			params = {
				'u': user,
				'mode': mode
			}

			r = self.http_sess.get(f"{server_name.url}/user/stats", params=params)
			if not r or r.status_code != 200:
				return

			stats = r.json()['stats']
			if not stats:
				return

			return {
				'userid': userinfo['id'],
				'username': userinfo['username'],
				'join_date': userinfo['registered_on'],
				'global_rank': stats['rank'],
				'playcount': stats['playcount'],
				'ranked_score': stats['ranked_score'],
				'total_score': stats['total_score'],
				'level': stats['level'],
				'pp': stats['pp'],
				'accuracy': float(stats['avg_accuracy']),
				'country': userinfo['country'],
				'country_rank': stats['country_rank'],
				'avatar_url': "https://a.gatari.pw/" + str(userinfo['id'])
			}

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

			stats = json[limit - 1 if limit > 0 else limit]
			if not stats:
				return

			if stats['rank'] != 'F':
				params = {
					'k': self.api_key,
					'b': stats['beatmap_id'],
					'u': user,
					'm': mode,
					'type': 'id' if isinstance(user, int) else 'string'
				}

				r = self.http_sess.get(f'{server_name.url}/get_scores', params=params)

				if not r or r.status_code != 200 or not (info := r.json()):
					stats['pp'] = 0
					stats['complete'] = 'No'
				else:
					for score in info:
						# TODO: no
						if score['score'] == stats['score'] and score['maxcombo'] == stats['maxcombo'] and score['count50'] == stats['count50'] and score['count100'] == stats['count100'] and score['count300'] == stats['count300'] and score['countmiss'] == stats['countmiss'] and score['countkatu'] == stats['countkatu'] and score['countgeki'] == stats['countgeki'] and score['perfect'] == stats['perfect'] and score['enabled_mods'] == stats['enabled_mods'] and score['enabled_mods'] == stats['enabled_mods'] and score['rank'] == stats['rank']:
							stats['pp'] = score['pp']
							stats['complete'] = 100.0
						else:
							stats['pp'] = 0
							stats['complete'] = self.map_completion_percentage(
								stats['beatmap_id'], 
								(int(stats['count50']) + int(stats['count100']) + int(stats['count300']) + int(stats['countmiss'])))
			else:
				stats['pp'] = 0
				stats['complete'] = self.map_completion_percentage(
								stats['beatmap_id'], 
								(int(stats['count50']) + int(stats['count100']) + int(stats['count300']) + int(stats['countmiss'])))

			params = {
				'k': self.api_key,
				'b': stats['beatmap_id']
			}

			r = self.http_sess.get(f"{server_name.url}/get_beatmaps", params=params)
			if not r or r.status_code != 200:
				return

			beatmapinfo = r.json()[0]

			acc = calc_acc(mode, int(stats['count300']), int(stats['count100']),
								 int(stats['count50']), int(stats['countmiss']))

			return {
				'beatmap_id': stats['beatmap_id'],
				'beatmapset_id': beatmapinfo['beatmapset_id'],
				'artist': beatmapinfo['artist'],
				'title': beatmapinfo['title'],
				'version': beatmapinfo['version'],
				'ar': beatmapinfo['diff_approach'],
				'od': beatmapinfo['diff_overall'],
				'difficultyrating': float(beatmapinfo['difficultyrating']),
				'score': stats['score'],
				'maxcombo': stats['maxcombo'],
				'fullcombo': beatmapinfo['max_combo'],
				'count_50': stats['count50'],
				'count_100': stats['count100'],
				'count_300': stats['count300'],
				'pp': float(stats['pp']) if stats['pp'] != '0' else 0.0,
				'count_miss': stats['countmiss'],
				'enabled_mods': repr(Mods(stats['enabled_mods'])),
				'intmods': int(stats['enabled_mods']),
				'rank': GRADE_URLS[stats['rank']] if GRADE_URLS else stats['rank'],
				'map_completed': stats['complete'],
				'accuracy': acc,
				'avatar_url': "https://s.ppy.sh/a/" + str(self.profile(user)['userid'])
			}

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

			stats = json['scores'][limit - 1 if limit > 0 else limit]

			return {
				'beatmap_id': stats['beatmap']['beatmap_id'],
				'beatmapset_id': stats['beatmap']['beatmapset_id'],
				'artist': stats['beatmap']['song_name'].split('-')[0][:-1],
				'title': "".join(stats['beatmap']['song_name'].split('-')[1]).split('[')[0][:-1][1:],
				'version': stats['beatmap']['song_name'].split('[')[1][:-1],
				'ar': stats['beatmap']['ar'],
				'od': stats['beatmap']['od'],
				'difficultyrating': float(stats['beatmap']['difficulty2'][GAMEMODES[mode]]),
				'score': stats['score'],
				'maxcombo': stats['max_combo'],
				'fullcombo': stats['beatmap']['max_combo'],
				'count_50': stats['count_50'],
				'count_100': stats['count_100'],
				'count_300': stats['count_300'],
				'pp': float(stats['pp']) if stats['pp'] != '0' else 0.0,
				'count_miss': stats['count_miss'],
				'enabled_mods': repr(Mods(stats['enabled_mods'])),
				'intmods': int(stats['mods']),
				'rank': GRADE_URLS[stats['rank']] if GRADE_URLS else stats['rank'],
				'map_completed': 'No' if stats['completed'] == 0 else 'Yes',
				'accuracy': float(stats['accuracy']),
				'avatar_url': "https://a.akatsuki.pw/" + str(self.profile(user)['userid'])
			}

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

			stats = json['scores'][limit - 1 if limit > 0 else limit]

			return {
				'beatmap_id': stats['beatmap']['beatmap_id'],
				'beatmapset_id': stats['beatmap']['beatmapset_id'],
				'artist': stats['beatmap']['song_name'].split('-')[0][:-1],
				'title': "".join(stats['beatmap']['song_name'].split('-')[1]).split('[')[0][:-1][1:],
				'version': stats['beatmap']['song_name'].split('[')[1][:-1],
				'ar': stats['beatmap']['ar'],
				'od': stats['beatmap']['od'],
				'difficultyrating': float(stats['beatmap']['difficulty2'][GAMEMODES[mode]]),
				'score': stats['score'],
				'maxcombo': stats['max_combo'],
				'fullcombo': stats['beatmap']['max_combo'],
				'count_50': stats['count_50'],
				'count_100': stats['count_100'],
				'count_300': stats['count_300'],
				'pp': float(stats['pp']) if stats['pp'] != '0' else 0.0,
				'count_miss': stats['count_miss'],
				'enabled_mods': repr(Mods(stats['enabled_mods'])),
				'intmods': int(stats['mods']),
				'rank': GRADE_URLS[stats['rank']] if GRADE_URLS else stats['rank'],
				'map_completed': 'No' if stats['completed'] == 0 else 'Yes',
				'accuracy': float(stats['accuracy']),
				'avatar_url': "https://a.ripple.moe/" + str(self.profile(user)['userid'])

			}

		elif server_name == Server.Gatari:
			params = {
				'id': self.profile(user)['userid'] if isinstance(user, str) else user,
				'mode': mode,
				'f': 0
			}

			r = self.http_sess.get(f"{server_name.url}/user/scores/recent", params=params)
			if not r or r.status_code != 200:
				return

			json = r.json()
			if not json:
				return

			stats = json['scores'][limit - 1 if limit > 0 else limit]

			return {
				'beatmap_id': stats['beatmap']['beatmap_id'],
				'beatmapset_id': stats['beatmap']['beatmapset_id'],
				'artist': stats['beatmap']['artist'],
				'title': stats['beatmap']['title'],
				'version': stats['beatmap']['version'],
				'ar': stats['beatmap']['ar'],
				'od': stats['beatmap']['od'],
				'difficultyrating': float(stats['beatmap']['difficulty']),
				'score': stats['score'],
				'maxcombo': stats['max_combo'],
				'fullcombo': stats['beatmap']['fc'],
				'count_50': stats['count_50'],
				'count_100': stats['count_100'],
				'count_300': stats['count_300'],
				'pp': float(stats['pp']) if stats['pp'] != '0' else 0.0,
				'count_miss': stats['count_miss'],
				'enabled_mods': repr(Mods(stats['enabled_mods'])),
				'intmods': int(stats['mods']),
				'rank': GRADE_URLS[stats['ranking']] if GRADE_URLS else stats['ranking'],
				'map_completed': 'No' if stats['completed'] == 0 else 'Yes',
				'accuracy': float(stats['accuracy']),
				'avatar_url': f"https://a.gatari.pw/{str(self.profile(user)['userid'])}"
			}

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

			stats = json['scores'][limit - 1 if limit > 0 else limit]

			params = {
				'k': self.api_key,
				'b': stats['beatmap_id']
			}

			r = self.http_sess.get(f"{server_name.url}/get_beatmaps", params=params)
			if not r or r.status_code != 200:
				return

			beatmapinfo = r.json()[0]

			acc = calc_acc(mode, int(stats['count300']), int(stats['count100']),
								 int(stats['count50']), int(stats['countmiss']),
								 int(stats['countkatu']), int(stats['countgeki']))

			return {
				'beatmap_id': stats['beatmap_id'],
				'beatmapset_id': beatmapinfo['beatmapset_id'],
				'artist': beatmapinfo['artist'],
				'title': beatmapinfo['title'],
				'version': beatmapinfo['version'],
				'ar': beatmapinfo['diff_approach'],
				'od': beatmapinfo['diff_overall'],
				'difficultyrating': float(beatmapinfo['difficultyrating']),
				'score': stats['score'],
				'maxcombo': stats['maxcombo'],
				'fullcombo': beatmapinfo['max_combo'],
				'count_50': stats['count50'],
				'count_100': stats['count100'],
				'count_300': stats['count300'],
				'pp': float(stats['pp']) if stats['pp'] != '0' else 0.0,
				'count_miss': stats['countmiss'],
				'enabled_mods': repr(Mods(stats['enabled_mods'])),
				'intmods': int(stats['enabled_mods']),
				'rank': GRADE_URLS[stats['rank']] if GRADE_URLS else stats['rank'],
				'accuracy': acc,
				'avatar_url': "https://s.ppy.sh/a/" + str(self.profile(user)['userid'])
			}

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

			stats = json['scores'][limit - 1 if limit > 0 else limit]

			return {
				'beatmap_id': stats['beatmap']['beatmap_id'],
				'beatmapset_id': stats['beatmap']['beatmapset_id'],
				'artist': stats['beatmap']['song_name'].split('-')[0][:-1],
				'title': "".join(stats['beatmap']['song_name'].split('-')[1]).split('[')[0][:-1][1:],
				'version': stats['beatmap']['song_name'].split('[')[1][:-1],
				'ar': stats['beatmap']['ar'],
				'od': stats['beatmap']['od'],
				'difficultyrating': float(stats['beatmap']['difficulty2'][GAMEMODES[mode]]),
				'score': stats['score'],
				'maxcombo': stats['max_combo'],
				'fullcombo': stats['beatmap']['max_combo'],
				'count_50': stats['count_50'],
				'count_100': stats['count_100'],
				'count_300': stats['count_300'],
				'pp': float(stats['pp']) if stats['pp'] != '0' else 0.0,
				'count_miss': stats['count_miss'],
				'enabled_mods': repr(Mods(stats['enabled_mods'])),
				'intmods': int(stats['mods']),
				'rank': GRADE_URLS[stats['rank']] if GRADE_URLS else stats['rank'],
				'accuracy': float(stats['accuracy']),
				'avatar_url': "https://a.akatsuki.pw/" + str(self.profile(user)['userid'])
			}

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

			stats = json['scores'][limit - 1 if limit > 0 else limit]

			return {
				'beatmap_id': stats['beatmap']['beatmap_id'],
				'beatmapset_id': stats['beatmap']['beatmapset_id'],
				'artist': stats['beatmap']['song_name'].split('-')[0][:-1],
				'title': "".join(stats['beatmap']['song_name'].split('-')[1]).split('[')[0][:-1][1:],
				'version': stats['beatmap']['song_name'].split('[')[1][:-1],
				'ar': stats['beatmap']['ar'],
				'od': stats['beatmap']['od'],
				'difficultyrating': float(stats['beatmap']['difficulty2'][GAMEMODES[mode]]),
				'score': stats['score'],
				'maxcombo': stats['max_combo'],
				'fullcombo': stats['beatmap']['max_combo'],
				'count_50': stats['count_50'],
				'count_100': stats['count_100'],
				'count_300': stats['count_300'],
				'pp': float(stats['pp']) if stats['pp'] != '0' else 0.0,
				'count_miss': stats['count_miss'],
				'enabled_mods': repr(Mods(stats['enabled_mods'])),
				'rank': GRADE_URLS[stats['rank']] if GRADE_URLS else stats['rank'],
				'accuracy': float(stats['accuracy']),
				'intmods': int(stats['mods']),
				'avatar_url': "https://a.ripple.moe/" + str(self.profile(user)['userid'])
			}

		elif server_name == Server.Gatari:
			params = {
				'id': self.profile(user)['userid'] if isinstance(user, str) else user,
				'mode': mode,
			}

			r = self.http_sess.get(f"{server_name.url}/user/scores/best", params=params)
			if not r or r.status_code != 200:
				return

			json = r.json()
			if not json:
				return

			stats = json['scores'][limit - 1 if limit > 0 else limit]

			return {
				'beatmap_id': stats['beatmap']['beatmap_id'],
				'beatmapset_id': stats['beatmap']['beatmapset_id'],
				'artist': stats['beatmap']['artist'],
				'title': stats['beatmap']['title'],
				'version': stats['beatmap']['version'],
				'ar': stats['beatmap']['ar'],
				'od': stats['beatmap']['od'],
				'difficultyrating': float(stats['beatmap']['difficulty']),
				'score': stats['score'],
				'maxcombo': stats['max_combo'],
				'fullcombo': stats['beatmap']['fc'],
				'count_50': stats['count_50'],
				'count_100': stats['count_100'],
				'count_300': stats['count_300'],
				'pp': float(stats['pp']) if stats['pp'] != '0' else stats['pp'],
				'count_miss': stats['count_miss'],
				'enabled_mods': repr(Mods(stats['enabled_mods'])),
				'intmods': int(stats['mods']),
				'rank': GRADE_URLS[stats['ranking']] if GRADE_URLS else stats['ranking'],
				'accuracy': float(stats['accuracy']),
				'avatar_url': f"https://a.gatari.pw/{str(self.profile(user)['userid'])}"
			}