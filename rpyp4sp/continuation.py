"""
- Each eval_exp_cps returns either:
  - A Next: (ctx, exp, continuation) - evaluate exp then apply continuation
  - A Done: (continuation, value) - apply continuation to value immediately
- Expression classes implement their own continuation logic via the apply method
"""
from rpython.rlib import jit


class AbstractCont(object):
    pass


class Cont(AbstractCont):
    _immutable_fields_ = ['exp', 'ctx', 'k',]

    def __init__(self, exp, ctx, k):
        self.exp = exp
        self.ctx = ctx
        self.k = k

    def apply(self, value):
        "application of k"
        return self.exp.apply(self, value)


class ListCont(Cont):
    _immutable_fields_ = ['exp', 'ctx', 'k', 'index', 'values[*]']
    def __init__(self, exp, ctx, k, index, values):
        self.exp = exp
        self.ctx = ctx
        self.k = k
        self.index = index
        self.values = values


class ValCont(AbstractCont):
    """A continuation that captures a value."""
    _immutable_fields_ = ['value', 'k']

    def __init__(self, value, k):
        self.value = value
        self.k = k


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
