import requests
import logging

from .mo import MO, MOInterface
from .request_handler import RequestHandler



class APIC:
    def __init__(self, url, username, password, verify_ssl = True):
        self.log = logging.getLogger()
        
        self.base_url = url
        self.session = None
        self.req = RequestHandler(url, verify_ssl=verify_ssl)
        self.login(username, password, verify_ssl=verify_ssl)
    
    def login(self, username, password, verify_ssl):
        resp = self.req.post("aaaLogin", data = f'<aaaUser name="{username}" pwd="{password}"/>', data_format = "xml")
        return True

    def logout(self):
        resp = self.req.post("aaaLogout")
        return True

    @property
    #def mo(self, class_name, dn):
    def mo(self):
        return MOInterface(request_handler = self.req)


