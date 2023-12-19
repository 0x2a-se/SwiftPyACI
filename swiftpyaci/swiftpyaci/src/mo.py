import logging
import json
import re

from copy import deepcopy

class MO:
    def __init__(self, class_name, dn, mo_class = None request_handler = None, **kwargs):
        self.__log = logging.getLogger()
        self.__class_name = class_name
        self.__mo_class = mo_class
        self.dn = dn
        self.__req = request_handler
        self.__cache_attributes = None
        self.__exists = None
        self.__children = list()
        self.set_attrs(**kwargs)

    def __str__(self):
        return self.dn
        

    def __repr__(self):
        res = [f"{k}='{v}'" for k,v in self]
        return f"{self.class_name}({','.join(res)})"

    def __iter__(self):
        for k, v in self.__dict__.items():
            if not k.startswith("_"):
                yield (k,v)

    @property
    def class_name(self):
        return self.__class_name
    
    @property
    def uri(self):
        return f"mo/{self.dn}"

    @property
    def exists(self):
        return self.__exists

    def child(self,class_name, dn, **kwargs):
        child = MO(class_name,dn, **kwargs)
        self.__children()

    def get_cache(self):
        return self.__cache_attributes or {}

    def set_cache(self):
        self.__cache_attributes = deepcopy(self.serilize())

    def load(self):
        # Load MO data from APIC
        mo_data = self.__req.get_mo(self.uri, params = {"rsp-prop-include": "config-only"})

        if not mo_data:
            self.__exists = False
            return False
        self.__exists = True
        self.set_attrs(**mo_data.get(self.class_name, {}).get("attributes"))
        self.set_cache()
        return True

    def save(self):
        if not self.diff():
            return None

        data = {
            self.class_name: {
                "attributes": {k: v["new"] for k,v in self.diff().items() if v["action"] in ["changed", "new"]}
            }
        }

        self.__log.info(data)
        self.__req.post(self.uri, data = data)
        self.load()


    def diff(self):
        dict_a = self.get_cache()
        dict_b = self.serilize()

        common_keys =  set(dict_a) & set(dict_b)
        res = {
            k: {"previous": dict_a[k], "new": dict_b[k], "action": "changed"}
            for k in common_keys
            if dict_a[k] != dict_b[k]
        }

        res.update({k: {"previous": "", "new": dict_b[k], "action": "new"} for k in set(dict_b) - set(dict_a)})
        res.update({k: {"previous": dict_a[k], "new": "", "action": "removed"} for k in set(dict_a) - set(dict_b)})

        return res
    
    def have_diff(self):
        if self.diff():
            return True
        return False

    def print_diff(self):
        diff = self.diff()
        print ()
        if diff.get("added", {}):
            print ("New attributes:")
            for k,v in diff.get("added", {}).items():
                print (f" {k}: '{v}'")
            print ()
        
        if diff.get("removed", {}):
            print ("Removed attributes:")
            for k,v in diff.get("removed", {}).items():
                print (f" {k}: '{v}'")
            print ()

        if diff.get("value_diffs", {}):
            print ("Changed attributes:")
            for k,v in diff.get("value_diffs", {}).items():
                print (f" {k}: '{v[0]}' -> '{v[1]}'")
            print ()

    def set_attrs(self, **kwargs):
        """Sets attributes from kwargs
        """
        for k,v in kwargs.items():
            setattr(self, k,v)

    def list_attributes(self):
        return [k for k,v in self]

    def serilize(self):
        """Serilizes attributes
        Returns:
            Dict: Dict of this objects attributes
        """
        res = dict()
        for k,v in self:
            res.update({k: v})
        
        return res

    def json(self):
        return json.dumps(self.serilize())

class MOClass:
    def __init__(self,class_name, request_handler):
        self.class_name = class_name
        self.meta_full_class_name = re.sub( r"([A-Z])", r":\1", class_name, count=1)
        self.meta_class_category, self.meta_class_name = self.meta_full_class_name.split(":")
        self.request_handler = request_handler
        resp = self.request_handler.get(f"doc/jsonmeta/{self.meta_class_category}/{self.meta_class_name}", use_api_uri = False)
        self.json_meta = resp.get(self.meta_full_class_name,{})
        self.identified_by = self.json_meta.get("identifiedBy")
        self.configurable_attributes = {k: v for k,v in self.json_meta.get("properties").items() if v.get("isConfigurable", False)}
        self.rn_format = self.json_meta.get("rnFormat")


class MOHandler:
    def __init__(self,class_name, request_handler = None):
        self.class_name = class_name
        self.request_handler = request_handler
        self.mo_class = MOClass(class_name, self.request_handler)
    
    def get(self, dn, **kwargs):
        mo = MO(self.class_name, dn, self.request_handler, **kwargs)
        mo.load()
        if not mo.exists:
            raise ValueError(f"Tried to get '{self.class_name}:{dn}' but got no result. Object does not exist")
        return mo
    
    def create(self, dn, **kwargs):
        mo = MO(self.class_name, dn, self.request_handler, **kwargs)
        mo.load()
        if mo.exists:
            raise ValueError(f"Found '{self.class_name}:{dn}'when trying to create object.")
        return mo
    
    def get_or_create(self, dn, **kwargs):
        mo = MO(self.class_name, dn, self.request_handler, mo_class = self.mo_class, **kwargs)
        mo.load()
        return mo 



class MOInterface:

    def __init__(self, request_handler = None):
        self.__log = logging.getLogger()
        self.request_handler = request_handler

    def get(self,class_name, dn):
        return MOHandler(class_name, request_handler = self.request_handler).get(dn)

    def create(self,class_name, dn, **kwargs):
        return MOHandler(class_name, request_handler = self.request_handler).create(dn, **kwargs)
    
    def get_or_create(self,class_name, dn, **kwargs):
        return MOHandler(class_name, request_handler = self.request_handler).ger_or_create(dn, **kwargs)

    def __getattr__(self, class_name):
        return MOHandler(class_name, request_handler = self.request_handler)
    