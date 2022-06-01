from type_checking.types import *

def type_to_str(_type):
    """
    Converts cont type object to string
    """
    if _type == object:
        return "any"
    elif isinstance(_type, Int):
        return "int"
    elif isinstance(_type, Ptr):
        return "*" + type_to_str(_type.typ)
    else:
        assert False, f"Unimplemented type in type_to_str: {_type}"