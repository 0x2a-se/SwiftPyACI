import logging
import json
import re

from copy import deepcopy
from .base_class import Base
from .base_class import Generic


class ManagedObject:
    def __init__(self, class_name, dn = None,rn = None,parent_dn = None,  mo_class = None, request_handler = None, class_meta = None, load = False, **kwargs):
        

        self.__log = logging.getLogger()
        self.__class_name = class_name
        self.__mo_class = mo_class
        self.__dn = dn
        self.__rn = rn
        self.__parent_dn = parent_dn
        self.__req = request_handler
        self.__cache_attributes = None
        self.__exists = None
        self.__children = list()
        self.set_attrs(**kwargs)
        if load:
            self.load()

    @property
    def dn(self):
        if self.__dn:
            return self.__dn
        
        self.__log.debug(f"rn: '{self.rn}, parent_dn: '{self.__parent_dn}")
        if self.rn and self.__parent_dn:
            return f"{self.__parent_dn}/{self.rn}"
        
        self.__log.error(f"Invalid dn '{self.__dn}'")
        raise ValueError(f"Could not construct DN for '{self.__class_name}'")

    @property
    def rn(self):
        if self.__rn:
            return self.__rn
        
        rn = self.__mo_class.rn_format
        for attr in self.__mo_class.naming:
            rn = rn.replace(f"{{{attr}}}", getattr(self,attr))
        if rn:
            return rn
        self.__log.error(f"Invalid rn '{rn}'")
        raise ValueError(f"Could not construct rn for '{self.__class_name}'")

    def __setattr__(self, name, value):
        if name == "dn":
            name = "__dn"

        elif not name.startswith("_") and name and not self.__mo_class.is_valid_attribute(name):
            raise ValueError(f"{name} is not a valid attribute")
        
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
    def meta(self):
        return self.__mo_class

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
        # Load MO data from APIC
        mo_data = self.__req.get_mo(self.uri, params = {"rsp-prop-include": "config-only"})

        if not mo_data:
            self.__exists = False
            return False
        self.__exists = True
        self.set_attrs(**mo_data.get(self.class_name, {}).get("attributes"))
        self.set_cache()
        return True

    def save_data(self):
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
        data = self.save_data()
        if not data:
            return None

        self.__log.info(data)
        self.__req.post(self.uri, data = data)
        self.load()


    def diff(self):
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
            setattr(self, k,v)

    def list_attributes(self):
        return [k for k,v in self]

    def serilize(self):
        res = {"attributes": self.serilize_attributes()}
        children = self.serilize_children()
        if children:
            res.update({"children": children})
        return {self.class_name: res}

    def serilize_attributes(self):
        """Serilizes attributes
        Returns:
            Dict: Dict of this objects attributes
        """
        res = dict()
        for k,v in self:
            res.update({k: v})
        
        return res

    def serilize_children(self):
        """Serilizes attributes
        Returns:
            Dict: Dict of this objects attributes
        """
        res = list()
        for child in self.__children:
            res.append(child.serilize())
        
        return res

    def json(self):
        return json.dumps(self.serilize())



class ManagedObjectAttribute(Base):
    def __init__(self, attr_name,**kwargs):
        self.__attr_name = attr_name
        self.set_attrs(**kwargs)

    def __str__(self):
        return self.__attr_name

    @property
    def attr_name(self):
        return self.__attr_name

    def is_naming(self):
        if getattr(self, "isNaming", False):
            return True
        return False
    
    def is_mandatory(self):
        if getattr(self, "mandatory", False) or getattr(self, "isNaming", False):
            return True
        return False


class ManagedObjectAttributes(Base):
    def __init__(self,**kwargs):
        for k,v in kwargs.items():
            setattr(self,k,ManagedObjectAttribute(k, **v))

    def get_mandatory(self):
        for k,v in self:
            if v.is_mandatory():
                yield k

    def get_naming(self):
        for k,v in self:
            if v.is_mandatory():
                yield k

    def get_configurable(self):
        for k,v in self:
            if v.isConfigurable:
                yield k
    


class ManagedObjectClass(Base):
    def __init__(self,class_name, request_handler):
        self.__class_name = class_name
        self.__meta_full_class_name = re.sub( r"([A-Z])", r":\1", class_name, count=1)
        self.__meta_class_category, self.__meta_class_name = self.__meta_full_class_name.split(":")
        self.request_handler = request_handler
        self.set_json_meta()
        self.set_identified_by()
        self.set_attributes()
        self.set_mandatory()
        self.set_naming()
        self.set_configurable_attributes()
        self.rn_format = self.__raw_json_meta.get("rnFormat")

    @property
    def class_name(self):
        return self.__class_name
    
    def set_attributes(self):
        self.attributes = ManagedObjectAttributes(**self.__raw_json_meta.get("properties"))

    def set_configurable_attributes(self):
        self.configurable_attributes = list(self.attributes.get_configurable())
    
    def set_json_meta(self):
        resp = self.request_handler.get(f"doc/jsonmeta/{self.__meta_class_category}/{self.__meta_class_name}", use_api_uri = False)
        self.__raw_json_meta = resp.get(self.__meta_full_class_name,{})
        self.set_attrs(**self.__raw_json_meta)

    def set_identified_by(self):
        self.identified_by = self.__raw_json_meta.get("identifiedBy")

    def set_mandatory(self):
        self.mandatory = list(self.attributes.get_mandatory())
    
    def set_naming(self):
        self.naming = list(self.attributes.get_naming())

    def __str__(self):
        return self.__meta_full_class_name
    
    def is_valid_attribute(self, arg):
        if arg in self.configurable_attributes:
            return True
        return False



class ManagedObjectHandler:
    def __init__(self,class_name, request_handler = None):
        self.class_name = class_name
        self.request_handler = request_handler
        self.mo_class = ManagedObjectClass(class_name, self.request_handler)

    def __str__(self):
        return repr(self)

    def __repr__(self):
        res = [f"{k}='{v}'" for k,v in self]
        return f"{self.__class__.__name__}({','.join(res)})"

    def __iter__(self):
        for k, v in self.__dict__.items():
            yield (k,v)
        

    def get(self, dn = None, load = False, **kwargs):
        mo = ManagedObject(self.class_name, dn = dn, request_handler = self.request_handler, **kwargs)
        if load:
            return mo
        mo.load()
        if not mo.exists:
            raise ValueError(f"Tried to get '{self.class_name}:{dn}' but got no result. Object does not exist")
        return mo
        
    def list(self, load = True, **kwargs):
        params = self.parse_filter_kwargs(**kwargs)
        resp = self.request_handler.list(f"class/{self.class_name}", params=params)
        for mo in resp:
            this = list(mo.values())[0].get("attributes",{})
            yield ManagedObject(self.class_name, this.pop("dn"), request_handler = self.request_handler, mo_class = self.mo_class, load = False, **this)
    
    def create(self, dn = None, load = False, **kwargs):
        mo = ManagedObject(self.class_name, dn = dn, request_handler = self.request_handler, mo_class = self.mo_class, **kwargs)
        mo.load()
        if mo.exists:
            raise ValueError(f"Found '{self.class_name}:{dn}'when trying to create object.")
        return mo
    
    def get_or_create(self, dn = None, load = False, **kwargs):
        mo = ManagedObject(self.class_name, dn = dn, request_handler = self.request_handler, mo_class = self.mo_class, **kwargs)
        mo.load()
        return mo 

    @staticmethod
    def parse_filter_kwargs(**kwargs):
        
        operators = ["eq","ne","in"]

        ###
        # for filter/get/all methods we want configuration with subtree
        new_kwargs = {'rsp-subtree': 'full', 'rsp-prop-include': 'config-only'}

        # query-target
        # target-subtree-class
        # query-target-filter
        # rsp-subtree
        # rsp-subtree-class
        # rsp-subtree-filter
        # rsp-subtree-include
        # order-by

        ###
        # if we have no kwargs then we have no filters
        # just return new kwargs
        if not kwargs:
            return new_kwargs

        ###
        # Return filters
        filters = list()

        ###
        # Loop all kwargs and parse them to a format that APIC understands
        # Exampel:
        #  kwargs = (fvBD_name=["bd001","bd002"], fbBD_ctx_name__ne="vrf003", fbBD_asd="vrf003", fvTenant_name__in=['tn1','tn2'])
        # Returns:
        #  and(and(eq("fvBD.name","bd001"),eq("fvBD.name","bd002")),ne("fbBD.ctx.name","bd002"),eq("fbBD.asd","bd002"),and(in("fvTenant.name","tn1"),in("fvTenant.name","tn2")))
        for k,v in kwargs.items():
            
            ###
            # logical operators that are not 'eq' should be separated on kwarg key with dunder at the end:
            # fvTenant_name__ne -> fvTenant.name 'not equal'
            
            # split on first occurance from end 
            this_object_arr = k.rsplit("__",1)

            # object attribute (fvTenant_Name) should be the first element
            # replace _ with . so that APIC understands it
            this_object = this_object_arr[0]

            if "_" in this_object:
                this_object = this_object.replace("_",".",1)
                

            # if we have an logical operator that should be in the last element
            # if we dont have an logical operator set it to 'eq'
            this_operator = "eq"
            this_filter_is_list = False
            if len(this_object_arr) > 1:
                
                # if operator are a list
                if this_object_arr[-1] in ["in", "not_in"]:
                    this_filter_is_list = True

                    # not_in is a list of 'ne'
                    if this_object_arr[-1] == "not_in":
                        this_operator = "ne"

                else:
                    # if we have a operator at the ond of attribute
                    this_operator = this_object_arr[-1]


            ###
            # make filters
            # if values are not an list then it is just a simple logic
            # i.e 'eq("fvTenant.name", "Tenant001")'

            # if value are a list then we have and/or logic depending on operator
            # i.e 'and(eq("fvBD.name", "bd001"),eq("fvBD.name", "bd002")'
            if not isinstance(v, list):
                filters.append(f'{this_operator}({this_object},"{v}")')
            else:
                
                this_filter = list()
                for item in v:
                    this_filter.append(f'{this_operator}({this_object},"{item}")')
                
                this_list_logic = "or"

                if this_operator in ["in","not_in"]:
                    this_list_logic = "and"
                    if this_operator == "not_in":
                        operator = "ne"
                
                # join filters in this list so we get 'and/or(eq("fvBD.name", "bd001"),eq("fvBD.name", "bd002")'
                filters.append(f"{this_list_logic}({','.join(this_filter)})")
        
        # join all filters
        # and(and(eq("fvBD.name","bd001"),eq("fvBD.name","bd002")),ne("fbBD.ctx.name","bd002"),eq("fbBD.asd","bd002"),and(in("fvTenant.name","tn1"),in("fvTenant.name","tn2")))
        if len(filters) > 1:
            final_filters = f'and({",".join(filters)})'
        if len(filters) < 1:
            return new_kwargs
        else:
            final_filters = filters[0]
            
       
        ###
        # update kwargs with filters
        new_kwargs.update({'query-target-filter': final_filters})
        return new_kwargs


