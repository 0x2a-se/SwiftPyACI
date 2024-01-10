import logging
import json
import re
import yaml
from copy import deepcopy
from .base_class import Base
from .base_class import Generic
from .class_meta import ClassMeta, get_class_meta



class ManagedObject:
    def __init__(self, class_name = None, dn = None,rn = None,parent_dn = None,  class_meta = None, request_handler = None, load = False, **kwargs):
        self.__log = logging.getLogger()
        self.__class_name = class_name
        self.__class_meta = class_meta
        self.__dn = dn
        self.__rn = rn
        self.__parent_dn = parent_dn
        self.__parent = None
        self.__req = request_handler
        self.__cache_attributes = None
        self.__exists = None
        self.__children = list()
        
        self.set_attrs(**kwargs) # need before load so that we can construct dn and rn
        if load:
            self.__log.debug("Loading data from APIC")
            self.load()
            self.set_attrs(**kwargs) # need again to find any changes passed in kwargs
        self.set_dn()
        self.set_parent_dn()

    @property
    def dn(self):
        if not self.__dn:
            self.set_dn()
        return self.__dn
        

    def get_dn(self):
        self.__log.debug(f"rn: '{self.rn}, parent_dn: '{self.__parent_dn}")
        if self.rn and self.__parent_dn:
            return f"{self.__parent_dn}/{self.rn}"
        
        self.__log.error(f"Invalid dn '{self.__dn}'")
        raise ValueError(f"Could not construct DN for '{self.__class_name}'")
    
    def set_dn(self):
        if not self.__dn:
            self.__dn = self.get_dn()

    @property
    def rn(self):
        if self.__rn:
            return self.__rn
        return self.__class_meta.rn(**{id_attr: getattr(self,id_attr) for id_attr in self.__class_meta.identified_by})

    @property
    def parent_dn(self):
        return self.__parent_dn
    
    @property
    def parent(self):
        if not self.__parent:
            self.resolve_parent()
        return self.__parent

    @property
    def delete(self):
        return getattr(self,"__delete", False)
    

    def __setattr__(self, name, value):
        if name == "dn":
            name = "__dn"
        
        elif name == "delete":
            if not type(value) == bool:
                raise TypeError("Attribute 'delete' need to be bool.")
            name = "__delete"

        #elif not name.startswith("_") and name and not self.__class_meta.is_valid_attribute(name):
        #    raise ValueError(f"{name} is not a valid attribute")
        
        super().__setattr__(name, value)
        


    def __str__(self):
        return self.dn
        

    def __repr__(self):
        res = [f"{k}='{v}'" for k,v in self]
        return f"{self.class_name}({','.join(res)})"

    def __iter__(self):
        yield ("dn",self.dn)
        for k, v in self.__dict__.items():
            if not k.startswith("_"):
                yield (k,v)


    @property
    def class_name(self):
        return self.__class_name
    
    @property
    def class_meta(self):
        return self.__class_meta

    @property
    def uri(self):
        return f"mo/{self.dn}"

    @property
    def exists(self):
        return self.__exists
    
    @property
    def children(self):
        return self.__children
    
    def child(self,class_name, **kwargs):
        kwargs.update({"parent_dn": self.dn})
        self.__log.debug(f"parent_dn: '{kwargs.get('parent_dn')}'")
        child = ManagedObjectHandler(class_name, request_handler = self.__req).get_or_create(**kwargs)
        self.__children.append(child)

    def get_cache(self):
        return self.__cache_attributes or {}

    def set_cache(self):
        self.__cache_attributes = deepcopy(self.serilize_attributes())

    def load(self):
        if not self.__req:
            raise ConnectionError("Offline mode, cannot load Managed Object")
        
        if not self.__class_name and not self.__dn: ## So that we can get Mo with DN and dont need to pass class_name
            raise ValueError(f"Missing either 'class_name' and/or 'dn'")

        # Load MO data from APIC
        mo_data = self.__req.get_mo(self.uri, params = {"rsp-prop-include": "all"})
        if not self.__class_meta:
            self.__class_meta = ClassMeta(**get_class_meta(self.__req,next(iter(mo_data))))
        if not self.__class_name:
            self.__class_name = self.__class_meta.class_name
        if not mo_data:
            self.__exists = False
            return False
        self.__exists = True
        self.set_attrs(**mo_data.get(self.class_name, {}).get("attributes"))

        for child in self.__children:
            child.load()

        self.set_cache()
        return True

    def save_data(self):
        if self.delete:
            return {self.class_name: {"attributes": {"status": "deleted"}}}
        res = {"attributes": {k: v["new"] for k,v in self.diff_atributes().items() if v["action"] in ["changed", "new"]}}
        children = list()
        for child in self.__children:
            if child.have_diff():
                children.append(child.save_data())
        
        if children:
            res.update({"children": children})
        
        if not self.have_diff and not children:
            return {}
        return {self.class_name: res}

    def save(self):
        if not self.__req:
            raise ConnectionError("Offline mode, cannot save Managed Object")
        data = self.save_data()
        if not data:
            return None

        self.__log.info(data)
        self.__req.post(self.uri, data = data)
        self.load()
    


    def set_parent_dn(self):
        
        if not self.__parent_dn:
            # Use a regular expression to split the DN into components
            components = re.split(r'(?<!\\)/(?![^\[]*\])', self.dn)

            # Remove the last component (the child itself) to get the parent components
            parent_components = components[:-1]

            if parent_components:
                # Join the parent components to form the parent DN
                self.__parent_dn = '/'.join(parent_components)
            else:
                self.__parent_dn = "topRoot"

    def resolve_parent(self):
        if self.__parent_dn != "topRoot":
            self.__log.debug(f"Getting parent with DN '{self.parent_dn}'")
            self.__parent = ManagedObject(dn = self.parent_dn, request_handler = self.__req, load = True)
        else:
            self.__log.debug(f"'{self.dn}' does not have any parent")

    def subtree(self):
        if not self.__req:
            raise ConnectionError("Offline mode, cannot get subtree for Managed Object")
        return self.__req.get_mo(self.uri, params = {"rsp-prop-include": "config-only", "rsp-subtree": "full"})


    def diff(self):
        if self.delete:
            return self.subtree()
        res = {"attributes": self.diff_atributes()}
        children = self.diff_children()
        if children:
            res.update({"children": self.diff_children()})
        return res

    def diff_atributes(self):
        dict_a = self.get_cache()
        dict_b = self.serilize_attributes()

        common_keys =  set(dict_a) & set(dict_b)
        res = {
            k: {"previous": dict_a[k], "new": dict_b[k], "action": "changed"}
            for k in common_keys
            if dict_a[k] != dict_b[k]
        }

        res.update({k: {"previous": "", "new": dict_b[k], "action": "new"} for k in set(dict_b) - set(dict_a)})
        res.update({k: {"previous": dict_a[k], "new": "", "action": "removed"} for k in set(dict_a) - set(dict_b)})

        return res
    
    def diff_children(self):
        return [child.diff() for child in self.__children]
    
    def have_diff(self):
        if self.diff_atributes():
            return True
        return False

    def print_diff(self):
        diff = self.diff_atributes()
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
            self.__log.debug(f"Setting attr '{k}'")
            setattr(self, k,v)

    def list_attributes(self):
        return [k for k,v in self]

    def serilize(self, **kwargs):
        res = {"attributes": self.serilize_attributes(**kwargs)}
        children = self.serilize_children(**kwargs)
        if children:
            res.update({"children": children})
        return {self.class_name: res}
        
    def config(self):
        return self.serilize(include = 'dn',isConfigurable = True)

    def serilize_attributes(self, include = None, **kwargs):
        """Serilizes attributes to dict

        Args:
            include (list or string, optional): List of or string with 1 property to be included in result. Defaults to None.
        kwargs:
            Kwargs will be treated as property filterm i.e isMandatory = True will include all mandatory attributes.

        Returns:
            dict: dict with serilized attributes. If include and kwargs are not passed then all properties will be included.
        """


        # attributes show be a dict of attributes filter, or all
        include_all_attributes = False

        include_attributes = list()
        if kwargs:
            include_attributes = self.__class_meta.properties.filter(**kwargs)

        if type(include) == list:
            include_attributes = include_attributes + include
        elif include:
            include_attributes.append(include)

        res = dict()
        for k,v in self:
            if k in include_attributes or len(include_attributes) == 0:
                res.update({k: v})
        
        return res

    def serilize_children(self, **kwargs):
        """Serilizes attributes
        Returns:
            Dict: Dict of this objects attributes
        """
        res = list()
        for child in self.__children:
            res.append(child.serilize(**kwargs))
        
        return res

    def json(self):
        return json.dumps(self.serilize())
    
    def yaml(self):
        return yaml.dump(self.serilize())



class ManagedObjectHandler:
    def __init__(self,class_name, request_handler = None):
        self.class_name = class_name
        self.request_handler = request_handler
        self.class_meta = ClassMeta(**get_class_meta(self.request_handler,class_name))

    def __str__(self):
        return repr(self)

    def __repr__(self):
        res = [f"{k}='{v}'" for k,v in self]
        return f"{self.__class__.__name__}({','.join(res)})"

    def __iter__(self):
        for k, v in self.__dict__.items():
            yield (k,v)

    def get(self, dn = None, **kwargs):
        mo = ManagedObject(class_name = self.class_name, dn = dn, load = True, request_handler = self.request_handler, class_meta = self.class_meta, **kwargs)
        if not mo.exists:
            raise ValueError(f"Tried to get '{mo.class_name}:{mo.dn}' but got no result. Object does not exist")
        return mo
        
    def list(self, load = True, params = None, **kwargs):
        parsed_params = self.params_parser(**kwargs)
        resp = self.request_handler.list(f"class/{self.class_name}", params=parsed_params)
        for mo in resp:
            this = list(mo.values())[0].get("attributes",{})
            yield ManagedObject(class_name = self.class_name, dn = this.pop("dn"), request_handler = self.request_handler, class_meta = self.class_meta, load = False, **this)
    
    def create(self, save = False, **kwargs):
        mo = ManagedObject(class_name = self.class_name, load = True, request_handler = self.request_handler, class_meta = self.class_meta, **kwargs)
        if mo.exists:
            raise ValueError(f"Found '{mo.class_name}:{mo.dn}'when trying to create object.")
        if save:
            mo.save()
        return mo
    
    def get_or_create(self, save = False, **kwargs):
        mo = ManagedObject(class_name = self.class_name, request_handler = self.request_handler, class_meta = self.class_meta, **kwargs)
        if save:
            mo.save()
        return mo 
    
    def params_parser(self, **kwargs):
        params = [
            "query_target",
            "target_subtree_class",
            "query_target_filter",
            "rsp_subtree",
            "rsp_subtree_class",
            "rsp_subtree_filter",
            "rsp_subtree_include",
            "order_by",
            "page",
            "page_size",
            "time_range"
        ]
        
        res = dict()
        for k,v in kwargs.items():
            if k in params:
                k = k.replace("_", "-")
                res.update({k: v})
            else:
                raise KeyError(f"Arg '{k}' is invalid, valid arugments are '{params}'")

        return res
