import requests
import logging

from .managed_object import ManagedObject, ManagedObjectHandler, ManagedObjectClass
from .request_handler import RequestHandler



class APIC:
    def __init__(self, url, username, password, verify_ssl = True):
        self.log = logging.getLogger()
        
        self.base_url = url
        self.session = None
        self.request_handler = RequestHandler(url, verify_ssl=verify_ssl)
        self.login(username, password, verify_ssl=verify_ssl)

    def login(self, username, password, verify_ssl):
        resp = self.request_handler.post("aaaLogin", data = f'<aaaUser name="{username}" pwd="{password}"/>', data_format = "xml")
        return True

    def logout(self):
        resp = self.request_handler.post("aaaLogout")
        return True

    def mo(self, class_name, dn, load = False, **kwargs):
        return ManagedObject(self.class_name, dn, request_handler = self.request_handler, mo_class = ManagedObjectClass(class_name, self.request_handler), load = False, **kwargs)
    
    def get(self,class_name, load = False, **kwargs):
        return ManagedObjectHandler(class_name, request_handler = self.request_handler).get(**kwargs)

    def list(self,class_name, load = False, **kwargs):
        return ManagedObjectHandler(class_name, request_handler = self.request_handler).list(**kwargs)

    def create(self,class_name, load = False, **kwargs):
        return ManagedObjectHandler(class_name, request_handler = self.request_handler).create(**kwargs)
    
    def get_or_create(self,class_name, load = False, **kwargs):
        return ManagedObjectHandler(class_name, request_handler = self.request_handler).get_or_create(**kwargs)
    
    # def set(self,class_name, load = False, **kwargs):
    #     # sets mo to passed kwargs
    #     return ManagedObjectHandler(class_name, request_handler = self.request_handler).set(**kwargs)

    def __getattr__(self, class_name):
        return ManagedObjectHandler(class_name, request_handler = self.request_handler)


