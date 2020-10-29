from enumm import *

class Beatmap():

	def __init__(self, osumap) -> None:
		self.map = osumap.splitlines()
		self.general = {}
		self.editor = {}
		self.colors = {}
		self.meta_data = {}
		self.events = []
		self.timing_points = []
		self.difficulty_data = {}
		self.hit_objects = []

	def parse(self):
		self.get_meta_data()
		self.get_difficulty_data()
		self.get_general_info()
		self.get_editor_info()
		self.get_event_info()
		self.get_timing_points()
		self.get_combo_colors()
		self.get_hit_objects()

	def get_general_info(self):
		_general_info = self.map.index('[General]')
		general_info = self.map[_general_info + 1:]
		for info in general_info:
			if info == '':
				continue
			if '[' in info:
				break
			if '//' in info:
				continue
			info = info.split(':')
			info_type = info[0]
			if info[1] == '':
				info[1] = ' '
			if info_type == 'Mode':
				self.general[info_type] = GameMode(int(info[1][1:] if ' ' in info[1] else info[1]))
				continue
			self.general[info_type] = info[1][1:] if ' ' in info[1] else info[1]
			continue

	def get_meta_data(self):
		_meta_data = self.map.index('[Metadata]')
		meta_data = self.map[_meta_data + 1:]
		for info in meta_data:
			if info == '':
				continue
			if '[' in info:
				break
			if '//' in info:
				continue
			info = info.split(':')
			info_type = info[0]
			if info[1] == '':
				info[1] = ' '
			if info_type == 'Tags':
				self.meta_data[info_type] = info[1].split(' ')
				continue
			self.meta_data[info_type] = info[1][1:] if info[1][0] == ' ' else info[1]
			continue

	def get_event_info(self):
		_event_info = self.map.index('[Events]')
		event_info = self.map[_event_info + 1:]
		for info in event_info:
			if info == '':
				continue
			if '[' in info:
				break
			if '//' in info:
				continue
			info = info.split(',')
			info[2] = info[2].replace('"', '')
			self.events.append(info)
			continue

	def get_timing_points(self):
		_timing_points = self.map.index('[TimingPoints]')
		timing_points = self.map[_timing_points + 1:]
		for info in timing_points:
			if info == '':
				continue
			if '[' in info:
				break
			if '//' in info:
				continue
			self.timing_points.append(info)
			continue

	def get_difficulty_data(self):
		_difficulty_data = self.map.index('[Difficulty]')
		difficulty_data = self.map[_difficulty_data + 1:]
		for info in difficulty_data:
			if info == '':
				continue
			if '[' in info:
				break
			if '//' in info:
				continue
			info = info.split(':')
			if info[1] == '':
				info[1] = ' '
			info_type = info[0]
			self.difficulty_data[info_type] = info[1][1:] if info[1][0] == ' ' else info[1]
			continue
	
	def get_editor_info(self):
		_editor_info = self.map.index('[Editor]')
		editor_info = self.map[_editor_info + 1:]
		for info in editor_info:
			if info == '':
				continue
			if '[' in info:
				break
			if '//' in info:
				continue
			info = info.split(':')
			if info[1] == '':
				info[1] = ' '
			info_type = info[0]
			if info_type == 'Bookmarks':
				self.editor[info_type] = info[1][1:].split(',') if ' ' in info[1] else info[1].split(',')
				continue
			self.editor[info_type] = info[1][1:] if ' ' in info[1] else info[1]
			continue

	def get_combo_colors(self):
		_combo_colors = self.map.index('[Colours]')
		combo_colors = self.map[_combo_colors + 1:]
		for info in combo_colors:
			if info == '':
				continue
			if '[' in info:
				break
			if '//' in info:
				continue
			info = info.split(':')
			if info[1] == '':
				info[1] = ' '
			info_type = info[0]
			self.colors[info_type] = info[1][1:] if ' ' in info[1] else info[1]
			continue

	def get_hit_objects(self):
		_hit_objects = self.map.index('[HitObjects]')
		hit_objects = self.map[_hit_objects + 1:]
		for info in hit_objects:
			if info == '':
				continue
			if '[' in info:
				break
			if '//' in info:
				continue
			info = info.split('|')
			self.hit_objects.append(info)
			continue