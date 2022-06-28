# -*- coding:Utf-8 -*-

import re


class MacroError(Exception):
    @classmethod
    def invalid_symbol(cls, symbol, position, expected_values):
        return cls(f'invalid symbol {symbol} at position {position}: expected {expected_values}')

def compile_expr(expr):
    pass

def _def_var(vars_, var_name, value):
    vars_[var_name] = value
    return value

def run_macro(macro, vars_):
    if isinstance(macro, str):
        for expr in macro.split(';'):
            value = eval_expr(expr, vars_)
    else:
        for code in macro:
            value = eval_expr(code, vars_)
    return value

def compile_macro(macro, vars_):
    compiled_macro = []
    for expr in macro.split(';'):
        compiled_macro.append(compile_expr(expr, vars_))
    return compiled_macro

def compile_expr(expr, vars_):
    locals().update(vars_)
    in_string = set()
    previous_char = " "
    
    while expr[0] == ' ':
        expr = expr[1:]
        
    new_expr = ''
    for i, char in enumerate(expr):
        if char in ('"', "'"):
            if char in in_string:
                in_string.remove(char)
            else:
                in_string.add(char)
        if not in_string:
            if (previous_char not in 'azertyuiopqsdfghjklmwxcvbnAZERTYUIOPQSDFGHJKLMWXCVBN_.'
                and char in 'azertyuioipqsdfghjklmwxcvbnAZERTYUIOPQSDFGHJKLMWXCVBN'):
                if char not in ('r', 'b') or expr[(i + 1) % len(expr)] not in ('"', "'"):
                    new_expr += '_'
        new_expr += char
        previous_char = char

    expr = new_expr

    
    expr = expr.replace('_True', 'True').replace('_False', 'False').replace('_None', 'None')
    expr = expr.replace('_and', 'and').replace('_or', 'or').replace('_not', 'not')
    expr = re.sub(r"(\?\|[^$]+\$\|)", r"eval_if('''\1''', vars_)", expr)
    expr = re.sub(r'^([a-zA-Z_]+) ?<- ?(.*)', r'def_var(vars_, "\1", \2)', expr)
    expr = expr.replace('&&', 'and').replace('||', 'or')
    expr = re.sub(r'!([^=])', r'not \1', expr)
    expr = re.sub(r'([^!<>+*/|%^&=-])=([^=])', r'\1==\2', expr)

    code = compile(expr, '', 'eval')
    return code
    
def eval_expr(expr, vars_):
    vars_['__builtins__'] = {}
    vars_['eval_if'] = eval_if
    vars_['def_var'] = _def_var
    vars_['vars_'] = vars_
    if isinstance(expr, str):
        code = compile_expr(expr, vars_)
    else:
        code = expr
    return eval(code, vars_, vars_)
    
def eval_if(expr, vars_):
    locals().update(vars_)
    condition_state = False
    expr_state = False
    current_subexpr = ''
    previous_char = ''
    condition = False
    
    for i, char in enumerate(expr):
        if i == 0 and char != '?':
            raise MacroError.invalid_symbol(char, i, '"?"')
        if i == 1 and char != '|':
            raise MacroError.invalid_symbol(char, i, '"|"')
        if i == len(expr) - 2 and char != '$':
            raise MacroError.invalid_symbol(char, i, '"$"')
        if i == len(expr) - 1 and char != '|':
            raise MacroError.invalid_symbol(char, i, '"|"')

        if i == 2:
            condition_state = True
            
        if condition_state:
            if previous_char == '-' and char == '>':
                if not condition:
                    condition = eval_expr(current_subexpr[:-1], vars_)
                expr_state = True
                condition_state = False
                current_subexpr = ''
                
            elif previous_char == '|' and char == '.':
                condition = True
                
            else:
                current_subexpr += char
                
        elif expr_state:
            if char in ('|', '$'):
                if condition:
                    return eval_expr(current_subexpr, vars_)
                else:
                    current_subexpr = ''
                    expr_state = False
                    condition_state = True
            else:
                current_subexpr += char

        previous_char = char

