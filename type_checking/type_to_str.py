from type_checking.types import *

def type_to_str(_type):
    """
    Converts cont type object to string
    """
    if isinstance(_type, Int):
        return "int"
    elif isinstance(_type, Ptr):
        if _type.typ is not None:
            return "*" + type_to_str(_type.typ)
        else:
            return "ptr"
    elif _type is None:
        return "any"
    else:
        assert False, f"Unimplemented type in type_to_str: {_type}"