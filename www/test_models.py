#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import orm, asyncio, sys, hashlib, time, logging
from models import User, Blog, Comment, next_id
logging.basicConfig(level=logging.INFO)

async def test(loop):
	# 'host':'idea-PC',
	db_dict = {'user':'www-data', 'password':'www-data', 'db':'awesome'}
	
	await orm.create_pool(loop=loop, **db_dict)
	
	# uid = next_id()
	# passwd='administrator'
	# email='admin@admin.com'
	# passwd = hashlib.sha1(('%s:%s' % (email, passwd)).encode('utf-8'))
	# sha1_passwd = '%s:%s' % (uid, passwd)
	# # u = User(name='admin', email='admin@admin.com', passwd='administrator', image='about:blank', admin=True)
	# u = User(id=uid, name='admin', email, passwd=hashlib.sha1(sha1_passwd.encode('utf-8')).hexdigest(), image='about:blank', admin=True)
	# await u.save()
	
	# summary = 'Lorem ipsum dolor sit amet, consectetur adipisicing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.'
	# b = Blog(id='1', name='Test Blog', summary=summary, created_at=time.time()-120, user_image='about:blank', user_id='11', user_name='111', content='test')
	# await b.save()
	
	await orm.close_pool()
	
loop = asyncio.get_event_loop()
loop.run_until_complete(test(loop))
loop.close()