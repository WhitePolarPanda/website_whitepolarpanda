"""Restricted mathematical expressions, evaluated with NumPy, never Python eval."""
import ast
import numpy as np

FUNCS = {n: getattr(np, f) for n, f in {
    'sin':'sin','cos':'cos','tan':'tan','exp':'exp','log':'log','sqrt':'sqrt',
    'abs':'abs','asin':'arcsin','acos':'arccos','atan':'arctan',
    'sinh':'sinh','cosh':'cosh','tanh':'tanh'}.items()}
OPS = {ast.Add:np.add, ast.Sub:np.subtract, ast.Mult:np.multiply,
       ast.Div:np.divide, ast.Pow:np.power}

def parse_expression(expr_str, allowed_symbols):
    if len(expr_str) > 512: raise ValueError('Expression is too long.')
    try: tree = ast.parse(expr_str.replace('^','**'), mode='eval')
    except (SyntaxError, RecursionError) as exc: raise ValueError('Enter a valid mathematical expression.') from exc
    if sum(1 for _ in ast.walk(tree)) > 128: raise ValueError('Simplify the expression.')
    names = {str(s) for s in allowed_symbols}
    def validate(node, depth=0):
        if depth > 16: raise ValueError('Simplify the expression.')
        if isinstance(node, ast.Constant) and type(node.value) in (int,float):
            if not np.isfinite(float(node.value)): raise ValueError('Use finite numbers.')
        elif isinstance(node, ast.Name) and node.id in names | {'pi'}: pass
        elif isinstance(node, ast.BinOp) and type(node.op) in OPS:
            validate(node.left,depth+1);validate(node.right,depth+1)
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op,(ast.UAdd,ast.USub)): validate(node.operand,depth+1)
        elif isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id in FUNCS and len(node.args)==1 and not node.keywords: validate(node.args[0],depth+1)
        else: raise ValueError('Use supported mathematical functions and variables only.')
    validate(tree.body)
    return tree.body

def build_lambdify(expr, symbols):
    def call(*values):
        env=dict(zip(map(str,symbols),values));env['pi']=np.pi
        def visit(node):
            if isinstance(node,ast.Constant): return np.float64(node.value)
            if isinstance(node,ast.Name): return env[node.id]
            if isinstance(node,ast.BinOp): return OPS[type(node.op)](visit(node.left),visit(node.right))
            if isinstance(node,ast.UnaryOp): return (-1 if isinstance(node.op,ast.USub) else 1)*visit(node.operand)
            return FUNCS[node.func.id](visit(node.args[0]))
        try:
            with np.errstate(all='ignore'): result=visit(expr)
            if np.iscomplexobj(result) or not np.isfinite(result).all(): raise ValueError('Expression must produce finite real values across the domain.')
            return result
        except (OverflowError,TypeError,FloatingPointError) as exc: raise ValueError('Expression must produce finite real values.') from exc
    return call
