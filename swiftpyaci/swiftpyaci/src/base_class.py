import yaml
import json

class Base:
    

    @property
    def _class_name(self):
        
        return getattr(self,"_class_name_override", None) or self.__class__.__name__

    def __str__(self):
        return self._class_name

    def __repr__(self):
        res = [f"{k}='{v}'" for k,v in self]
        return f"{self._class_name}({','.join(res)})"

    def __iter__(self):
        for k, v in self.__dict__.items():
            if not k.startswith("_"):
                yield (k,v)

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
    
    def yaml(self):
        return yaml.dump(self.serilize()) 

class Generic(Base):

    def __init__(self,_obj_name, **kwargs):
        self.__obj_name = _obj_name
        self.set_attrs(**kwargs)

    def __str__(self):
        return self.__obj_name