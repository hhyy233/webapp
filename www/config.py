#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import config_default

class Dict(dict):
	# allow x.y access
	def __init__(self, names=(), values=(), **kw):
		super(Dict, self).__init__(**kw)
		for k, v in zip(names, values):
			self[k] = v
		
	def __getattr__(self, key):
		try:
			return self[key]
		except KeyError:
			raise AttributeError(r"Dict object has no attribute %s" % key)
			
	def __setattr__(self, key, value):
		self[key] = value
		
		
def merge(defaults, override):
	r = {}
	for k, v in defaults.items():
		if k in override:
			if isinstance(v, dict):
				r[k] = merge(v, override[k])
			else:
				r[k] = v
		else:
			r[k] = v
	return r
	
def toDict(d):
	D = Dict()
	for k, v in d.items():
		# print(k,v)
		D[k] = toDict(v) if isinstance(v, dict) else v 
		# print(k, type(D[k]))
	return D

configs = config_default.configs

try:
	import config_override
	configs = merge(configs, config_override.configs)
except ImportError:
	pass
	
configs = toDict(configs)
# print(configs)
# print(configs.session, type(configs.session))
# print(configs.db, type(configs.db))