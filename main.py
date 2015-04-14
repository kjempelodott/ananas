#-*- coding: utf-8 -*-

import time, re
import httplib, urllib
from urlparse import urlparse
from socket import gaierror

class Cookie:
    def __init__(self, host, name = None, path = "/", content = None):
        self.host = host
        self.name = name
        self.path = path
        self.content = content

    def __str__(self):
        return self.name + "=" + self.content


class Connection(httplib.HTTPSConnection, object):
    
    def __init__(self, host, header = None):
        super(Connection, self).__init__(host)
        self.header = header if header else {}
        self.cookies = []

    def addcookie(self, cookie):
        try:
            assert(cookie.host == self.host)
        except:
            print "WARNING (in Cookie): host mismatch (%s)" % cookie.name
            return False
        if self.header.has_key("Cookie"):
            self.header["Cookie"] += ";" + str(cookie)
        else:
            self.header["Cookie"] = str(cookie)
        self.cookies.append(cookie)
        return True

    def request(self, url, method, body = None, header = {}, DEBUG = False):
        try:
            header.update(self.header)
            if body:
                body = "&".join("%s=%s" % entry for entry in body)
            if DEBUG:
                print "REQUEST\n" + urllib.unquote(url)
                print "REQUEST HEADER\n" + str(header)
                print "REQUEST BODY\n" + str(body)
            super(Connection, self).request(method, url, body, header)
            response = self.getresponse()
            content = response.read()
            if DEBUG:
                print "RESPONSE HEADER\n" + str(response.getheaders())
                print "CONTENT\n" + content + "\n"
            return response, content
        except gaierror as e:
            print("Name or service not known: " + host)
            exit(1)


class Fronter(object):

    SERVICE_PROVIDER = "sp.fronter.com"
    IDENTITY_PROVIDER = "idp.feide.no"
    SP_HEADER = {"User-Agent" : "httplib"}
    IDP_HEADER = {"User-Agent" : "httplib"}

    def __init__(self):
        self.cookies = {
            "org_feide"     : Cookie(Fronter.IDENTITY_PROVIDER, "org_feide", "/simplesaml/module.php/feide/", "uio.no"),
            "SAMLSessionID" : None,
            "SAMLAuthToken" : None,
            "shibsession"   : None
        }
        self.connect()

    def connect(self):
        self.__SPConnection__ = \
                    Connection(Fronter.SERVICE_PROVIDER, Fronter.SP_HEADER)
        self.__IDPConnection__ = \
                    Connection(Fronter.IDENTITY_PROVIDER, Fronter.IDP_HEADER)
        self.__SPConnection__.connect()
        self.__IDPConnection__.connect()
        self.__IDPConnection__.addcookie(self.cookies["org_feide"])

    def close(self):
        self.__SPConnection__.close()
        self.__IDPConnection__.close()

    def login(self):
        sp_query, login_url = self.__SPrequestResource__()
        saml_response, relay_state = self.__fillLoginForm__(login_url)
        self.__SPsendResponse__(saml_response, relay_state, sp_query)

    def __SPrequestResource__(self):
        # Get SAMLRequest from SP
        body = (
            ("shire"      , "SHIBBOLETH_SP_SHIRE"),
            ("target"     , "http://fronter.com/uio/"),
            ("time"       , str(int(time.time()))),
            ("providerId" , "SHIBBOLETH_SP_PROVIDER_ID")
        )
        path = "/sso/shibboleth2/sp/feide-idp"
        response, content = self.__SPConnection__.request(path, "GET", body)
        status = response.status
        if status != 302:
            print("Exception in SAMLRequest (SP): %s (%s)" %
                  (status, response.reason))
            exit(1)
        saml_request = urlparse(response.getheader("Location"))

        # Get SAMLSessionID cookie from IDP
        url = saml_request.path + "?" + saml_request.query
        response, content = self.__IDPConnection__.request(url, "GET")
        status = response.status
        if status != 302:
            print("Exception in SAMLRequest (IDP): %s (%s)" %
                  (status, response.reason))
            exit(1)

        # Set SAMLSessionID cookie
        c = response.getheader("Set-Cookie").split(",")[1]
        c = re.match(".*?(?P<name>SimpleSAMLSessionID)=(?P<content>(.+?)); path=(?P<path>(.+?));", c).groupdict()
        self.cookies["SAMLSessionID"] = Cookie(Fronter.IDENTITY_PROVIDER, c["name"], c["path"], c["content"])
        self.__IDPConnection__.addcookie(self.cookies["SAMLSessionID"])

        # Return login request url and SP query (timestamp)
        return body, urlparse(response.getheader("Location"))

    def __fillLoginForm__(self, login_url):
        # Login with IDP
        url = login_url.path + "?" + login_url.query
        from getpass import getpass
        body = (
            ("feidename", raw_input("Username: ")),
            ("password" , getpass()),
        )
        header = {
            "Accept"       : "text/html,application/xhtml+xml,appication/xml",
            "Content-type" : "application/x-www-form-urlencoded",
        }
        response, content = self.__IDPConnection__.request(url, "POST", body, header)
        status = response.status
        if status != 200:
            print("Exception in login (IDP): %s (%s)" %
                  (status, response.reason))
            exit(1)

        # Set SAMLAuthToken cookie
        c = re.match(".*?(?P<name>SimpleSAMLAuthToken)=(?P<content>(.+?)); path=(?P<path>(.+?));", response.getheader("Set-Cookie")).groupdict()
        self.cookies["SAMLAuthToken"] = Cookie(Fronter.IDENTITY_PROVIDER, c["name"], c["path"], c["content"])
        self.__IDPConnection__.addcookie(self.cookies["SAMLAuthToken"])

        # Return SAMLResponse and RelayState
        saml_response = urllib.quote(re.findall("name=\"SAMLResponse\" value=\"(.+?)\"", content)[-1])
        relay_state = re.findall("name=\"RelayState\" value=\"(.+?)\"", content)[-1]
        return saml_response, relay_state

    def __SPsendResponse__(self, saml_response, relay_state, sp_query):
        # Return SAMLResponse to SP
        path = "/Shibboleth.sso/SAML2/POST"
        body = (
            ("SAMLResponse", saml_response),
            ("RelayState"  , relay_state),
        )
        header = {
            "Accept"       : "text/html,application/xhtml+xml,appication/xml",
            "Content-type" : "application/x-www-form-urlencoded",
        }
        response, content = self.__SPConnection__.request(path, "POST", body, header)
        status = response.status
        if status != 302:
            print("Exception in SAMLResponse return (SP): %s (%s)" %
                  (status, response.reason))
            exit(1)

        # Set shibsession cookie
        c = re.match(".*?(?P<name>.+?)=(?P<content>(.+?)); path=(?P<path>(.+?));", response.getheader("Set-Cookie")).groupdict()
        self.cookies["shibsession"] = Cookie(Fronter.SERVICE_PROVIDER, c["name"], c["path"], c["content"])
        self.__SPConnection__.addcookie(self.cookies["shibsession"])

        # Authorize
        path = "/sso/shibboleth2/sp/feide-idp"
        header = {
            "Accept" : "text/html,application/xhtml+xml,appication/xml",
        }
        response, content = self.__SPConnection__.request(path, "GET", sp_query, header)
        status = response.status
        if status != 200:
            print("Exception in Shibboleth authorization (SP): %s (%s)" %
                  (status, response.reason))
            exit(1)
        
        #TODO: Authorization failed ...
        print content

if __name__ == "__main__":
    cli = Fronter()
    cli.login()
                

