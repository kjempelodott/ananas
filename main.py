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
            print("WARNING (in Cookie): host mismatch (%s)" % cookie.name)
            return False

        if self.header.has_key("Cookie"):
            self.header["Cookie"] += ";" + str(cookie)
        else:
            self.header["Cookie"] = str(cookie)

        self.cookies.append(cookie)
        return True

    def request(self, url, method, body = None, header = {}):
        try:
            print url
            header.update(self.header)
            if body:
                body = "&".join("%s=%s" % entry for entry in body)
            super(Connection, self).request(method, url, body, header)
            response = self.getresponse()
            content = response.read()
            return response, content

        except gaierror as e:
            print("Name or service not known: " + host)
            exit(1)


class Fronter(object):

    SERVICE_PROVIDER = "sp.fronter.com"
    IDENTITY_PROVIDER = "idp.feide.no"
    TARGET = "http://fronter.com/uio/"
    HEADER = {
        "Accept"       : "text/html,application/xhtml+xml,appication/xml",
        "Content-type" : "application/x-www-form-urlencoded",
    }

    def __init__(self):
        self.cookies = {
            "org_feide"     : Cookie(Fronter.IDENTITY_PROVIDER, "org_feide",
                                     "/simplesaml/module.php/feide/", "uio.no"),
            "SAMLSessionID" : None,
            "SAMLAuthToken" : None,
            "shibsession"   : None
        }
        self.connect()

    def connect(self):
        self._SPConnection = Connection(Fronter.SERVICE_PROVIDER)
        self._IDPConnection = Connection(Fronter.IDENTITY_PROVIDER, Fronter.HEADER)
        self._SPConnection.connect()
        self._IDPConnection.connect()
        self._IDPConnection.addcookie(self.cookies["org_feide"])

    def close(self):
        self._SPConnection.close()
        self._IDPConnection.close()

    def login(self):
        timestr = str(int(time.time()))
        sso_request_redir = self._requestTargetResource(timestr, True)
        login_redir = self._requestSSOService(sso_request_redir)
        saml_response, relay_state = self._feideLogin(login_redir)
        self._requestAssertionConsumerService(saml_response, relay_state)
        self._requestTargetResource(timestr)


    def _requestTargetResource(self, timestr, redir=False):

        """
        Request target resource
        # 1, 7
        """ 

        body = (
            ("shire"      , "SHIBBOLETH_SP_SHIRE"),
            ("target"     , Fronter.TARGET),
            ("time"       , timestr),
            ("providerId" , "SHIBBOLETH_SP_PROVIDER_ID")
        )
        path = "/sso/shibboleth2/sp/feide-idp"

        response, content = self._SPConnection.request(path, "GET", body)
        status = response.status

        if not redir:
            if status != 200:
                print("Exception in SP request: %s (%s)" % (status, response.reason))
                exit(1)
            return

        else:
            if status != 302:
                print("Exception in SP request: %s (%s)" % (status, response.reason))
                exit(1)
            sso_request_redir = urlparse(response.getheader("Location"))
            return sso_request_redir

        
    def _requestSSOService(self, request):
        
        """
        Request SSO service and recieve SAMLSessionID cookie from IDP
        # 3
        """

        url = request.path + "?" + request.query
        response, content = self._IDPConnection.request(url, "GET")
        status = response.status
        if status != 302:
            print("Exception in IDP request: %s (%s)" % (status, response.reason))
            exit(1)

        # Set SAMLSessionID cookie
        cookie = response.getheader("Set-Cookie").split(",")[-1]
        pattern = ".*?(?P<name>SimpleSAMLSessionID)=(?P<content>(.+?)); path=(?P<path>(.+?));"
        cookie = re.match(pattern, cookie).groupdict()
        self.cookies["SAMLSessionID"] = Cookie(Fronter.IDENTITY_PROVIDER, cookie["name"],
                                               cookie["path"], cookie["content"])
        self._IDPConnection.addcookie(self.cookies["SAMLSessionID"])

        # Return URL to login form
        return urlparse(response.getheader("Location"))


    def _feideLogin(self, login_redir):

        """
        Login with feide, the identity provider and receive SAMLAuthToken cookie from IDP
        # 4
        """

        url = login_redir.path + "?" + login_redir.query
        from getpass import getpass
        body = (
            ("feidename", "Username: "),
            ("password" , getpass()),
            ("org"      , "uio.no"),
        )

        response, content = self._IDPConnection.request(url, "POST", body)
        status = response.status
        if status != 200:
            print("Exception in IDP request: %s (%s)" % (status, response.reason))
            exit(1)

        try:
            # Set SAMLAuthToken cookie
            cookie = response.getheader("Set-Cookie")
            pattern = ".*?(?P<name>SimpleSAMLAuthToken)=(?P<content>(.+?)); path=(?P<path>(.+?));"
            cookie = re.match(pattern, cookie).groupdict()
            self.cookies["SAMLAuthToken"] = Cookie(Fronter.IDENTITY_PROVIDER, cookie["name"], 
                                                   cookie["path"], cookie["content"])
            self._IDPConnection.addcookie(self.cookies["SAMLAuthToken"])
        except:
            print("Wrong username and/or password!")
            exit(1)

        # Return SAMLResponse and RelayState
        saml_response = re.findall("name=\"SAMLResponse\" value=\"(.+?)\"", content)[-1]
        relay_state = re.findall("name=\"RelayState\" value=\"(.+?)\"", content)[-1]
        return  urllib.quote(saml_response), urllib.quote(relay_state)


    def _requestAssertionConsumerService(self, saml_response, relay_state):

        """ 
        Request Assertion Consumer Service and receive shibsession cookie from SP
        # 5
        """

        path = "/Shibboleth.sso/SAML2/POST"
        body = (
            ("SAMLResponse", saml_response),
            ("RelayState"  , relay_state),
        )

        response, content = self._SPConnection.request(path, "POST", body)
        status = response.status
        if status != 302:
            print("Exception in SP request: %s (%s)" % (status, response.reason))
            exit(1)

        # Set shibsession cookie
        cookie = response.getheader("Set-Cookie")
        pattern = ".*?(?P<name>_shibsession\w+?)=(?P<content>(.+?)); path=(?P<path>(.+?));"
        cookie = re.match(pattern, cookie).groupdict()
        self.cookies["shibsession"] = Cookie(Fronter.SERVICE_PROVIDER, cookie["name"],
                                             cookie["path"], cookie["content"])
        self._SPConnection.addcookie(self.cookies["shibsession"])



if __name__ == "__main__":
    cli = Fronter()
    cli.login()
                

