#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re, time, json, logging, hashlib, base64, asyncio, markdown2
import random
from models import User, Comment, Blog, next_id
from coroweb import get, post
from config import configs
from apis import APIValueError, APIResourceNotFoundError, Page
from aiohttp import web

COOKIE_NAME = 'awesession'
_COOKIE_KEY = configs.session.secret


def check_admin(request):
	if request.__user__ is None or not request.__user__.admin:
		raise APIPermissionError()
		
def get_page_index(page_str):
	p = 1
	try: 
		p = int(page_str)
	except ValueError as e:
		pass
	if p < 1:
		p = 1
	return p
	
def text2html(text):
	lines = map(lambda s: '<p>%s</p>' % s.replace('&', '&amp;').replace('<', '&lt;').replace('>','&gt;'), filter(lambda s: s.strip() != '', text.split('\n')))
	return ''.join(lines)

def user2cookie(user, max_age):
	expires = str(int(time.time() + max_age))
	s = '%s-%s-%s-%s' % (user.id, user.passwd, expires, _COOKIE_KEY)
	L = [user.id, expires, hashlib.sha1(s.encode('utf-8')).hexdigest()]
	return '-'.join(L)
	
async def cookie2user(cookie_str):
	if not cookie_str:
		return None
	try:
		L = cookie_str.split('-')
		if len(L) != 3:
			return None
		uid, expires, sha1 = L
		if int(expires) < time.time():
			return None
		user = await User.find(uid)
		if user is None:
			return None
		s = '%s-%s-%s-%s' % (user.id, user.passwd, expires, _COOKIE_KEY)
		if sha1 != hashlib.sha1(s.encode('utf-8')).hexdigest():
			logging.info('invalid sha1')
			return None
		user.passwd = '******'
		return user
	except Exception as e:
		logging.exception(e)
		return None


@get('/test')
async def index(request):
	print(request)
	users = await User.findAll()
	return {
		'__template__': 'test.html',
		'users': users
	}
	
@get('/')
async def index(*, page='1'):
	# summary = 'Lorem ipsum dolor sit amet, consectetur adipisicing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.'
	# blogs = [
		# Blog(id='1', name='Test Blog', summary=summary, created_at=time.time()-120),
		# Blog(id='2', name='Test Blog 1', summary=summary, created_at=time.time()-3600),
		# Blog(id='3', name='Test Blog 2', summary=summary, created_at=time.time()-7200),
	# ]
	
	page_index = get_page_index(page)
	num = await Blog.findNumber('count(id)')
	page = Page(num)
	if num==0:
		blogs = []
	else:
		blogs = await Blog.findAll(orderBy='created_at desc', limit=(page.offset, page.limit))

	return {
		'__template__': 'blogs.html',
		'page': page,
		'blogs': blogs
	}
	
@get('/api/users/test')
async def api_get_users():
	users = await User.findAll(orderBy='created_at desc')
	for u in users:
		u.passwd = '******'
	return dict(users=users)

@get('/register')
def register():
	print('-----in register-----')
	return {
		'__template__': 'register.html'
	}

@get('/signin')
def signin():
	return {
		'__template__': 'signin.html'
	}

@post('/api/authenticate')
async def authenticate(*, email, passwd):
	if not email:
		raise APIValueError('email', 'Invalid Email.')
	if not passwd:
		raise APIValueError('passwd', 'Invalid password.')
	users = await User.findAll('email=?', [email])
	if len(users) == 0:
		raise APIValueError('email', 'Email not exist.')
	user = users[0]
	sha1 = hashlib.sha1()
	sha1.update(user.id.encode('utf-8'))
	sha1.update(b':')
	sha1.update(passwd.encode('utf-8'))
	if user.passwd != sha1.hexdigest():
		raise APIValueError('passwd', 'Invalid password.')
	r = web.Response()
	r.set_cookie(COOKIE_NAME, user2cookie(user, 86400), max_age=86400, httponly=True)
	user.passwd = '******'
	r.content_type = 'application/json'
	r.body = json.dumps(user, ensure_ascii=False).encode('utf-8')
	return r
	
@post('/api/blogs/{id}')
async def api_update_blog(id, request, *, name, summary, content):
	check_admin(request)
	blog = await Blog.find(id)
	if not name or not name.strip():
		raise APIValueError('name', 'name cannot be empty.')
	if not summary or not summary.strip():
		raise APIValueError('summary', 'summary cannot be empty.')
	if not content or not content.strip():
		raise APIValueError('content', 'content cannot be empty.')
	blog.name = name.strip()
	blog.summary = summary.strip()
	blog.content = content.strip()
	await blog.update()
	return blog
	
@get('/api/comments')
async def api_comments(*, page='1'):
	page_index = get_page_index(page)
	num = await Comment.findNumber('count(id)')
	p = Page(num, page_index)
	if num == 0:
		return dict(page=p, comments=())
	comments = await Comment.findAll(orderBy='created_at desc', limit=(p.offset, p.limit))
	return dict(page=p, comments=comments)

@post('/api/blogs/{id}/comments')
async def api_create_comment(id, request, *, content):
	user = request.__user__
	if user is None:
		raise APIPermissionError('Please signin first.')
	if not content or not content.strip():
		raise APIValueError('content')
	blog = await Blog.find(id)
	if blog is None:
		raise APIResourceNotFoundError('Blog')
	comment = Comment(blog_id=blog.id, user_id=user.id, user_name=user.name, user_image=user.image, content=content.strip())
	await comment.save()
	return comment
	
@post('/api/comments/{id}/delete')
async def api_delete_comments(id, request):
	check_admin(request)
	c = await Comment.find(id)
	if c is None:
		raise APIResourceNotFoundError('Comment')
	await c.remove()
	return dict(id=id)
	
@get('/signout')
def signout(request):
	referer = request.headers.get('Referer')
	r = web.HTTPFound(referer or '/')
	r.set_cookie(COOKIE_NAME, '-delete-', max_age=0, httponly=True)
	logging.info('user signed out.')
	return r

_RE_EMAIL = re.compile(r'^[a-z0-9\.\-\_]+\@[a-z0-9\-\_]+(\.[a-z0-9\-\_]+){1,4}$')
_RE_SHA1 = re.compile(r'^[0-9a-f]{40}$')

@post('/api/users')
async def api_register_user(*, email, name, passwd):
	# logging.warning('got user %s' % name)
	if not name or not name.strip():
		raise APIValueError('name')
	if not email or not _RE_EMAIL.match(email):
		raise APIValueError('email')
	if not passwd or not _RE_SHA1.match(passwd):
		raise APIValueError('passwd')
	users = await User.findAll('email=?', [email])
	if len(users) > 0:
		raise APIError('register:failed', 'email', 'Email is already in use.')
	uid = next_id()
	sha1_passwd = '%s:%s' % (uid, passwd)
	user = User(id=uid, name=name.strip(), email=email, passwd=hashlib.sha1(sha1_passwd.encode('utf-8')).hexdigest(), image='http://www.gravatar.com/avatar/%s?d=mm&s=120' % hashlib.md5(email.encode('utf-8')).hexdigest())
	# user = User(admin=True, id=uid, name=name.strip(), email=email, passwd=hashlib.sha1(sha1_passwd.encode('utf-8')).hexdigest(), image='about:blank')
	await user.save()
	r = web.Response()
	r.set_cookie(COOKIE_NAME, user2cookie(user, 86400), max_age=86400, httponly=True)
	user.passwd = '******'
	r.content_type = 'application/json'
	r.body = json.dumps(user, ensure_ascii=False).encode('utf-8')
	return r
	
@get('/api/users')
async def api_get_users(*, page='1'):
	page_index = get_page_index(page)
	num = await User.findNumber('count(id)')
	p = Page(num, page_index)
	if num == 0:
		return dict(page=p, users=())
	users = await User.findAll(orderBy='created_at desc', limit=(p.offset, p.limit))
	for u in users:
		u.passwd = '******'
	return dict(page=p, users=users)

@get('/blog/{id}')
async def get_blog(id):
	blog = await Blog.find(id)
	comments = await Comment.findAll('blog_id=?', [id], orderBy='created_at desc')
	for c in comments:
		c.html_content = text2html(c.content)
	blog.html_content = markdown2.markdown(blog.content)
	return {
		'__template__': 'blog.html',
		'blog': blog,
		'comments': comments
	}
	
@get('/pickone')
async def pick_one():
	blogs = await Blog.findAll()
	num = len(blogs)
	pos = random.randint(0, num-1)
	blog = blogs[pos]
	return 'redirect:/blog/%s' % blog.id

@get('/manage/blogs/create')
def manage_create_blog():
	# check_admin(request)
	return {
		'__template__': 'manage_blog_edit.html',
		'id': '',
		'action': '/api/blogs'
	}

@get('/manage/blogs')
def manage_blogs(*, page='1'):
	return {
		'__template__': 'manage_blogs.html',
		'page_index': get_page_index(page)
	}
	
@get('/manage/blogs/edit')
def manage_edit_blogs(*, id):
	return {
		'__template__': 'manage_blog_edit.html',
		'id': id,
		'action': '/api/blogs/%s' % id
	}
	
@get('/manage/')
def manage():
	return 'redirect:/manage/comments'
	
@get('/manage/comments')
def manage_comments(*, page='1'):
	return {
		'__template__': 'manage_comments.html',
		'page_index': get_page_index(page)
	}
	
@get('/manage/users')
def manage_users(*, page='1'):
	return {
		'__template__': 'manage_users.html',
		'page_index': get_page_index(page)
	}

@get('/api/blogs/{id}')
async def api_get_blog(*, id):
	blog = await Blog.find(id)
	return blog
	
@post('/api/blogs')
async def api_create_blog(request, *, name, summary, content):
	check_admin(request)
	if not name or not name.strip():
		raise APIValueError('name', 'name cannot be empty.')	
	if not summary or not summary.strip():
		raise APIValueError('summary', 'summary cannot be empty.')	
	if not content or not content.strip():
		raise APIValueError('content', 'content cannot be empty.')
	logging.warning('Saving blogs...')
	blog = Blog(user_id=request.__user__.id, user_name=request.__user__.name, user_image=request.__user__.image, name=name.strip(), summary=summary.strip(), content=content.strip())
	await blog.save()
	return blog
	
@get('/api/blogs')
async def api_blogs(*, page='1'):
	page_index = get_page_index(page)
	num = await Blog.findNumber('count(id)')
	p = Page(num, page_index)
	if num == 0:
		return dict(page=p, blogs=())
	blogs = await Blog.findAll(orderBy='created_at desc', limit=(p.offset, p.limit))
	return dict(page=p, blogs=blogs)

@post('/api/blogs/{id}/delete')
async def api_delete_blog(request, *, id):
	check_admin(request)
	blog = await Blog.find(id)
	await blog.remove()
	#delete comment
	comments = await Comment.findAll('blog_id=?', [id])
	for c in comments:
		await c.remove()
		
	return dict(id=id)


	
