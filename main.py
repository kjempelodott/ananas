#-*- coding: utf-8 -*-

import re
from urllib2 import HTTPCookieProcessor, HTTPRedirectHandler, build_opener
from urllib import urlencode
from getpass import getuser, getpass

TARGET = 'https://fronter.com/uio'

cookie_jar = HTTPCookieProcessor()
opener = build_opener(HTTPRedirectHandler, cookie_jar)


# Step 1: Get SimpleSAMLSessionID
#
#         TARGET -> Service Provider (SP)
#         SP     -> Identity Provider (IDP) 
#         IDP requests SAML cookie
#         Cookie!
#
response = opener.open(TARGET)


# Step 2: Choose affiliation (UiO)
response = opener.open(response.url + '&org=uio.no')


# Step 3: Login
#
#         IDP -> SP
#
# Fetch hidden fields from content
payload = dict(re.findall('name="(\w+)" value="(.+?)"', response.read()))
# Add username and password
payload['feidename'] = getuser()
payload['password'] = getpass()
data = urlencode(payload).encode('ascii')
response = opener.open(response.url, data)


# Step 4: Submit SAMLResponse
content = response.read()
url = re.findall('action="(.+?)"', content)[0]
payload = dict(re.findall('name="(\w+)" value="(.+?)"', contentr))
data = urlencode(payload).encode('ascii')
response = opener.open(url, data)




