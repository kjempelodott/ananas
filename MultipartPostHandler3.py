#!/usr/bin/python

####
# 02/2006 Will Holcomb <wholcomb@gmail.com>
# 
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
# 
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
"""
Usage:
  Enables the use of multipart/form-data for posting forms

Inspirations:
  Upload files in python:
    http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/146306
  urllib2_file:
    Fabien Seisen: <fabien@seisen.org>

Example:
  import MultipartPostHandler, urllib, cookielib

  cookies = cookielib.CookieJar()
  opener = urllib.request.build_opener(urllib2.HTTPCookieProcessor(cookies),
                                MultipartPostHandler.MultipartPostHandler)
  params = { "username" : "bob", "password" : "riviera",
             "file" : open("filename", "rb") }
  opener.open("http://wwww.bobsite.com/upload/", params)

Further Example:
  The main function of this file is a sample which downloads a page and
  then uploads it to the W3C validator.
"""

from urllib.request import HTTPHandler, BaseHandler, build_opener
from urllib.parse import urlencode
from email.generator import _make_boundary as choose_boundary
import mimetypes
import os, stat

# Controls how sequences are uncoded. If true, elements may be given multiple values by
#  assigning a sequence.
doseq = 1

class MultipartPostHandler(BaseHandler):
    handler_order = HTTPHandler.handler_order - 10 # needs to run first

    def http_request(self, request):
        data = request.data
        if data is not None and type(data) != bytes:
            v_files = []
            v_vars = []
            try:
                 for(key, value) in data.items():
                     if hasattr(value, 'fileno'):
                         v_files.append((key, value))
                     else:
                         v_vars.append((key, value))
            except TypeError:
                systype, value, traceback = sys.exc_info()
                raise TypeError("not a valid non-string sequence or mapping object", traceback)

            if len(v_files) == 0:
                data = urlencode(v_vars, doseq)
            else:
                boundary, data = self.multipart_encode(v_vars, v_files)
                contenttype = 'multipart/form-data; boundary=%s' % boundary
                if(request.has_header('Content-Type')
                   and request.get_header('Content-Type').find('multipart/form-data') != 0):
                    print("Replacing %s with %s" % (request.get_header('content-type'), 'multipart/form-data'))
                request.add_unredirected_header('Content-Type', contenttype)
            request.data = data
        return request

    def multipart_encode(self, vars, files, boundary = None, buffer = None):
        if boundary is None:
            boundary = choose_boundary()
        if buffer is None:
            buffer = ''
        for(key, value) in vars:
            buffer += '--%s\r\n' % boundary
            buffer += 'Content-Disposition: form-data; name="%s"' % key
            buffer += '\r\n\r\n' + value + '\r\n'
        buffer = buffer.encode('utf-8')
        for(key, fd) in files:
            file_size = os.fstat(fd.fileno())[stat.ST_SIZE]
            filename = fd.name.split('/')[-1]
            contenttype = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
            tmp = '--%s\r\n' % boundary
            tmp += 'Content-Disposition: form-data; name="%s"; filename="%s"\r\n' % (key, filename)
            tmp += 'Content-Type: %s\r\n' % contenttype
            # tmp += 'Content-Length: %s\r\n' % file_size
            fd.seek(0)
            buffer += tmp.encode('utf-8')
            buffer += b'\r\n' + fd.read() + b'\r\n'
        buffer += b'--' + boundary.encode('utf-8') + b'--\r\n\r\n'
        return boundary, buffer

    https_request = http_request

def main():
    import tempfile, sys

    validatorURL = "http://validator.w3.org/check"
    opener = build_opener(MultipartPostHandler)

    def validateFile(url):
        temp = tempfile.mkstemp(suffix=".html")
        os.write(temp[0], opener.open(url).read())
        params = { "ss" : "0",            # show source
                   "doctype" : "Inline",
                   "uploaded_file" : open(temp[1], "rb") }
        print(opener.open(validatorURL, params).read())
        os.remove(temp[1])

    if len(sys.argv[1:]) > 0:
        for arg in sys.argv[1:]:
            validateFile(arg)
    else:
        validateFile("http://www.google.com")

if __name__=="__main__":
    main()
