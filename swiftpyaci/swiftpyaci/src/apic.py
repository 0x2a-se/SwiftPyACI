import requests
import logging

from .managed_object import ManagedObject, ManagedObjectHandler
from .class_meta import ClassMeta, get_class_meta
from .request_handler import RequestHandler



class APIC:
    def __init__(self, url, username, password, verify_ssl = True):
        self.log = logging.getLogger()
        
        self.base_url = url
        self.session = None
        self.request_handler = None
        if url:
            self.request_handler = RequestHandler(url, verify_ssl=verify_ssl)
            self.login(username, password, verify_ssl=verify_ssl)

    def login(self, username, password, verify_ssl):
        resp = self.request_handler.post("aaaLogin", data = f'<aaaUser name="{username}" pwd="{password}"/>', data_format = "xml")
        return True

    def logout(self):
        resp = self.request_handler.post("aaaLogout")
        return True

    def mo(self, class_name, dn = None, load = False, **kwargs):
        return ManagedObject(class_name, dn, request_handler = self.request_handler, class_meta = ClassMeta(**get_class_meta(self.request_handler,class_name)), load = FALSE, **kwargs)
    
    def class_meta(self, class_name):
        return ClassMeta(**get_class_meta(self.request_handler,class_name))
    
    def dn(self, dn):
        return ManagedObject(None, dn, request_handler = self.request_handler, load = True)

    def get(self,class_name = None, dn = dn,  **kwargs):
        return ManagedObjectHandler(class_name, request_handler = self.request_handler).get(**kwargs)

    def list(self,class_name, **kwargs):
        return ManagedObjectHandler(class_name, request_handler = self.request_handler).list(**kwargs)

    def create(self,class_name, **kwargs):
        return ManagedObjectHandler(class_name, request_handler = self.request_handler).create(**kwargs)
    
    def get_or_create(self,class_name, **kwargs):
        return ManagedObjectHandler(class_name, request_handler = self.request_handler).get_or_create(**kwargs)

    def __getattr__(self, class_name):
        return ManagedObjectHandler(class_name, request_handler = self.request_handler)


