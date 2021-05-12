from typing import List


def expand_dict_to_str(obj) -> List[str]:
    """
    Expand the dictionary to str recursively
    """
    # get a dict representation or return as list of str
    if hasattr(obj, 'to_dict'):
        d = obj.to_dict().values()
    elif isinstance(obj, dict):
        d = obj.values()
    else:
        d = [obj]

    # expand
    out = []
    for value in d:
        # handle recursion
        if isinstance(value, dict):
            out.extend(expand_dict_to_str(value))
        if isinstance(value, (list, tuple)):
            for v in value:
                out.extend(expand_dict_to_str(v))
        
        # handle values
        if isinstance(value, (str, int, float)):
            out.extend([str(value)])
    
    return out        
