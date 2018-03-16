#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import orm, asyncio, sys
from models import User, Blog, Comment

async def test(loop):
	# 'host':'idea-PC',
	db_dict = {'user':'www-data', 'password':'www-data', 'db':'awesome'}
	
	await orm.create_pool(loop=loop, **db_dict)
	
	u = User(name='Test', email='test@example.com', passwd='1234567890', image='about:blank')
	
	await u.save()
	await orm.close_pool()
	
loop = asyncio.get_event_loop()
loop.run_until_complete(test(loop))
loop.close()