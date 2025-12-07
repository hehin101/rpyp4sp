"""
- Each eval_exp_cps returns either:
  - A Next: (ctx, exp, continuation) - evaluate exp then apply continuation
  - A Done: (continuation, value) - apply continuation to value immediately
- Expression classes implement their own continuation logic via the apply method
"""
from rpython.rlib import jit


class Cont(object):
    _immutable_fields_ = ['exp', 'ctx', 'k',]

    def __init__(self, exp, ctx, k):
        self.exp = exp
        self.ctx = ctx
        self.k = k

    def apply(self, value):
        "application of k"
        return self.exp.apply(self, value)


class ListECont(Cont):
    _immutable_fields_ = ['exp', 'ctx', 'k', 'index', 'values[*]']
    def __init__(self, exp, ctx, k, index, values):
        self.exp = exp
        self.ctx = ctx
        self.k = k
        self.index = index
        self.values = values


class BinECont(Cont):
    """Continuation for binary expressions (BinE, CmpE, ConsE, etc.) that stores the left operand."""
    _immutable_fields_ = ['exp', 'ctx', 'k', 'left']
    def __init__(self, exp, ctx, k, left):
        self.exp = exp
        self.ctx = ctx
        self.k = k
        self.left = left


# ==============
# Continuation
# ==============

class Next(object):
    """evaluate exp in ctx, then apply continuation k"""
    _immutable_fields_ = ['ctx', 'exp', 'k']

    def __init__(self, ctx, exp, k):
        self.ctx = ctx
        self.exp = exp
        self.k = k


class Done(object):
    """a computed value ready to be passed to continuation k"""
    _immutable_fields_ = ['k', 'value']

    def __init__(self, k, value):
        self.k = k
        self.value = value
