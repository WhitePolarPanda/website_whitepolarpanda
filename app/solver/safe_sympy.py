import sympy

ALLOWED_FUNCS = {
    'sin': sympy.sin,
    'cos': sympy.cos,
    'tan': sympy.tan,
    'exp': sympy.exp,
    'log': sympy.log,
    'sqrt': sympy.sqrt,
    'pi': sympy.pi,
    'abs': sympy.Abs,
    'asin': sympy.asin,
    'acos': sympy.acos,
    'atan': sympy.atan,
    'sinh': sympy.sinh,
    'cosh': sympy.cosh,
    'tanh': sympy.tanh,
}


def parse_expression(expr_str, allowed_symbols):
    symbols_map = {sym.name: sym for sym in allowed_symbols}
    locals_map = {**ALLOWED_FUNCS, **symbols_map}

    try:
        expr = sympy.sympify(expr_str, locals=locals_map)
    except (sympy.SympifyError, TypeError) as exc:
        raise ValueError(f"Invalid expression: {exc}") from exc

    free_symbols = expr.free_symbols
    if not free_symbols.issubset(set(allowed_symbols)):
        bad = sorted({sym.name for sym in free_symbols - set(allowed_symbols)})
        raise ValueError(f"Invalid symbols in expression: {', '.join(bad)}")

    return expr


def build_lambdify(expr, symbols):
    return sympy.lambdify(symbols, expr, 'numpy')