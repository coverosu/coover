import requests
import asyncio

class OsuApiV2Wrapper():
	def __init__(self, client_id: int, client_secret: str) -> None:
		self.client_id = client_id
		self.client_secret = client_secret
		self.sess = requests.Session()
		self.headers = None
		self.token_info = None
		asyncio.run(self.get_access_token()) 

	async def __enter__(self):
		return self

	async def __exit__(self):
		return self.sess.close()

	async def get_access_token(self):
		url = 'https://osu.ppy.sh/oauth/token'
		data = {
			'client_id': self.client_id,
			'client_secret': self.client_secret,
			'grant_type': 'client_credentials',
			'scope': 'public'
		}
		req = self.sess.post(url, data=data)
		if not req or req.status_code != 200:
			raise Exception("Bad request")
		information = req.json()
		if not information:
			raise Exception("No Token Found!")
		self.token_info = {'token': information['access_token'],
						   'expire_time': information['expires_in']
					      }
		self.headers = {"Authorization": f"Bearer {self.token_info['token']}"}
		return self.token_info

	async def profile(self, userid: int, mode: str = 'osu') -> dict:
		await self.get_access_token()
		url = f'https://osu.ppy.sh/api/v2' \
			  f'/users/{userid}/{mode}'
		req = self.sess.get(url, headers=self.headers)
		if not req or req.status_code != 200:
			raise Exception("Bad request")

		return req.json()

	async def get_user_recent_activity(self, userid: int, 
								limit: int = 0, 
								offset: int = 0) -> dict:
		await self.get_access_token()
		url = f'https://osu.ppy.sh/api/v2' \
			  f'/users/{userid}/recent_activity'
		params = {
			'limit': limit,
			'offset': offset
		}
		req = self.sess.get(url, headers=self.headers, params=params)
		if not req or req.status_code != 200:
			raise Exception("Bad request")

		return req.json()	

	async def get_score(self, userid: int, mode: str = 'osu',
						 limit: int = 0, offset: int = 0, 
						 include_fails: int = 1, 
						 type: str = 'best') -> dict:
		await self.get_access_token()
		url = f'https://osu.ppy.sh/api/v2' \
			  f'/users/{userid}/scores/{type}'
		params = {
			'include_fails': include_fails,
			'mode': mode,
			'limit': limit,
			'offset': offset
		}
		req = self.sess.get(url, headers=self.headers, params=params)
		if not req or req.status_code != 200:
			raise Exception("Bad request")

		return req.json()

	async def get_beatmap_score(self, mapid: int, userid: int = 0, mode: str = 'osu',
								limit: int = 0, offset: int = 0, 
								include_fails: int = 1, 
								type: str = 'best') -> dict:
		await self.get_access_token()
		params = {} # ONE DAY!!!
		url = f'https://osu.ppy.sh/api/v2' \
			  f'/beatmaps/{mapid}/scores'
		req = self.sess.get(url, headers=self.headers) #params=params
		if not req or req.status_code != 200:
			raise Exception("Bad request")

		return req.json()

	async def get_user_beatmap(self, userid: int, type: str,
							   limit: int = 0, offset: int = 0, 
							   ) -> dict:
		
		await self.get_access_token()
		url = ('https://osu.ppy.sh/api/v2' 
			  f'/users/{userid}/beatmapsets/{type}')
		params = {
			'limit': limit,
			'offset': offset
		}
		req = self.sess.get(url, headers=self.headers, params=params)
		if not req or req.status_code != 200:
			raise Exception("Bad request")

		return req.json()
