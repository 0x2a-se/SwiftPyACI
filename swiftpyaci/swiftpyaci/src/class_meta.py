import re

from .base_class import Base


class ClassMetaProperty(Base):
    """Class meta property"""
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
    
    def is_configurable(self):
        if getattr(self, "isConfigurable", False):
            return True
        return False


class ClassMetaProperties(Base):
    """List of class meta properties

    Args:
        Base (_type_): _description_
    """
    def __init__(self,**kwargs):
        for k,v in kwargs.items():
            setattr(self,k,ClassMetaProperty(k, **v))

    def all(self):
        res = list()
        for k,v in self:
            res.append(k)
        return res

    def get_mandatory(self):
        for k,v in self:
            if v.is_mandatory():
                yield k

    def naming(self):
        for k,v in self:
            if v.is_mandatory():
                yield k
    
    def filter(self, **kwargs):
        """Filter properties
        """
        res = list()
        for prop_name, prop in self:
            match = {}
            for k,v in kwargs.items():
                match.update({k: getattr(prop,k)})
            if match == kwargs:
                res.append(prop_name)
        
        return res
    

class ClassMeta(Base):
    """This class are for generating RN and verify attributes and values. Input are json meta data that can be collected from APIC, i.e https://<apic>/doc/jsonmeta/<pkg>/<class.json, https://<apic>/doc/jsonmeta/fv/Tenant.json
    """
    def __init__(self, *, rnFormat: str, identifiedBy: dict, properties: dict = None, **kwargs):
        self.rn_format = rnFormat
        self.identified_by = identifiedBy
        self.properties = ClassMetaProperties(**properties)
        self.set_attrs(**kwargs)
    
    
    def __str__(self):
        return f"ClassMeta:{self.class_name}"

    @property
    def class_name(self):
        return f"{self.classPkg}{self.className}"

    def rn(self,**kwargs):
        """Builds RN from kwargs based on rnFormat, i.e tn-{name} for tenant.

        Returns:
            rn: string
        """
        rn = self.rn_format
        for attr in self.properties.naming():
            rn = rn.replace(f"{{{attr}}}", kwargs[attr])
        return rn


def get_class_meta(request_handler, class_name):
    full_class_name = re.sub( r"([A-Z])", r":\1", class_name, count=1)
    category, name = full_class_name.split(":")

    resp = request_handler.get(f"doc/jsonmeta/{category}/{name}", use_api_uri = False)
    return resp.get(full_class_name,{})
    
