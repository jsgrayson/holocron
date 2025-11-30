# lua_parser.py
# Simple Lua Table Parser for Python

import re

def parse_lua_table(lua_string):
    """
    Parses a Lua table string into a Python dictionary.
    Handles nested tables, string keys, and basic values.
    """
    # Remove comments
    lua_string = re.sub(r'--.*', '', lua_string)
    
    idx = 0
    n = len(lua_string)
    
    def skip_whitespace():
        nonlocal idx
        while idx < n and lua_string[idx].isspace():
            idx += 1
            
    def parse_value():
        nonlocal idx
        skip_whitespace()
        if idx >= n: return None
        
        char = lua_string[idx]
        
        if char == '{':
            return parse_object()
        elif char == '"':
            return parse_string()
        elif char.isdigit() or char == '-':
            return parse_number()
        elif lua_string[idx:idx+4] == 'true':
            idx += 4
            return True
        elif lua_string[idx:idx+5] == 'false':
            idx += 5
            return False
        elif lua_string[idx:idx+3] == 'nil':
            idx += 3
            return None
        else:
            # Try to parse unquoted string/identifier
            start = idx
            while idx < n and (lua_string[idx].isalnum() or lua_string[idx] == '_'):
                idx += 1
            return lua_string[start:idx]

    def parse_string():
        nonlocal idx
        idx += 1 # Skip opening quote
        start = idx
        while idx < n and lua_string[idx] != '"':
            if lua_string[idx] == '\\':
                idx += 2
            else:
                idx += 1
        val = lua_string[start:idx]
        idx += 1 # Skip closing quote
        return val

    def parse_number():
        nonlocal idx
        start = idx
        if lua_string[idx] == '-':
            idx += 1
        while idx < n and (lua_string[idx].isdigit() or lua_string[idx] == '.'):
            idx += 1
        try:
            val = float(lua_string[start:idx])
            if val.is_integer():
                return int(val)
            return val
        except ValueError:
            return 0

    def parse_object():
        nonlocal idx
        idx += 1 # Skip {
        obj = {}
        is_array = True
        array_idx = 1
        
        while idx < n:
            skip_whitespace()
            if idx < n and lua_string[idx] == '}':
                idx += 1
                return list(obj.values()) if is_array and obj else obj
            
            # Key
            key = None
            if lua_string[idx] == '[':
                is_array = False
                idx += 1
                skip_whitespace()
                if lua_string[idx] == '"':
                    key = parse_string()
                else:
                    key = parse_number()
                skip_whitespace()
                if lua_string[idx] == ']':
                    idx += 1
                skip_whitespace()
                if lua_string[idx] == '=':
                    idx += 1
            elif lua_string[idx].isalpha() or lua_string[idx] == '_':
                is_array = False
                # Unquoted key
                start = idx
                while idx < n and (lua_string[idx].isalnum() or lua_string[idx] == '_'):
                    idx += 1
                key = lua_string[start:idx]
                skip_whitespace()
                if lua_string[idx] == '=':
                    idx += 1
            else:
                # Array item
                key = array_idx
                array_idx += 1
                
            # Value
            val = parse_value()
            obj[key] = val
            
            skip_whitespace()
            if idx < n and (lua_string[idx] == ',' or lua_string[idx] == ';'):
                idx += 1
                
        return obj

    # Find the first assignment "Var = {"
    match = re.search(r'(\w+)\s*=\s*\{', lua_string)
    if match:
        idx = match.start() + len(match.group(1))
        skip_whitespace()
        if lua_string[idx] == '=':
            idx += 1
            return {match.group(1): parse_value()}
            
    return {}
