def type_to_str(_type : type | tuple, sep : str =" or "):
    """
    Converts type or tuple of types to string
    e. g. <class 'bin_types.functions.Function'> -> function
    For tuples will separate types with argument sep, standard sep is " or "
    """
    
    if isinstance(_type, tuple):
        types = []
        for i in _type:
            types.append(type_to_str(i))

        return sep.join(types)

    if _type is None:
        return "none"

    res = str(_type)
    main_part = str(_type).find("'")+1
    end_main_part = str(_type).rfind("'")
    res = res[main_part:end_main_part]
    res = res.split(".")[-1] # removes modules names

    return res.lower()