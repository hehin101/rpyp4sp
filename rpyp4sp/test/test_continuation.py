"""Tests for the CPS (Continuation-Passing Style) interpreter implementation."""
from __future__ import print_function
import pytest

from rpyp4sp import p4specast, objects, interp
from rpyp4sp.continuation import *


def make_num(val, typ=None):
    if typ is None:
        typ = p4specast.NumT.INT
    return objects.NumV.fromstr(str(val), p4specast.IntT.INSTANCE, typ)

def make_nat(val):
    return objects.NumV.fromstr(str(val), p4specast.NatT.INSTANCE, p4specast.NumT.NAT)

def make_bool(val):
    return objects.BoolV.make(val, p4specast.BoolT.INSTANCE)

def make_text(val):
    return objects.TextV(val, p4specast.TextT())

def make_num_exp(val, typ=None):
    if typ is None:
        typ = p4specast.NumT.INT
    exp = p4specast.NumE.fromstr(str(val), p4specast.IntT.INSTANCE)
    exp.typ = typ
    return exp

def make_nat_exp(val):
    exp = p4specast.NumE.fromstr(str(val), p4specast.NatT.INSTANCE)
    exp.typ = p4specast.NumT.NAT
    return exp

def make_bool_exp(val):
    exp = p4specast.BoolE(val)
    exp.typ = p4specast.BoolT.INSTANCE
    return exp

def make_text_exp(val):
    exp = p4specast.TextE(val)
    exp.typ = p4specast.TextT()
    return exp

def make_opt_exp(inner_exp=None):
    if inner_exp is not None:
        inner_typ = inner_exp.typ
    else:
        inner_typ = p4specast.NumT.INT
    opt_typ = p4specast.IterT(inner_typ, p4specast.Opt())
    exp = p4specast.OptE(inner_exp, opt_typ)
    return exp

def make_tuple_exp(elts):
    elt_types = [e.typ for e in elts]
    typ = p4specast.TupleT(elt_types)
    exp = p4specast.TupleE(elts, typ)
    return exp

def make_list_exp(elts):
    if elts:
        inner_typ = elts[0].typ
    else:
        inner_typ = p4specast.NumT.INT
    typ = p4specast.IterT(inner_typ, p4specast.List())
    exp = p4specast.ListE(elts, typ)
    return exp

def make_cons_exp(head_exp, tail_exp):
    inner_typ = head_exp.typ
    typ = p4specast.IterT(inner_typ, p4specast.List())
    exp = p4specast.ConsE(head_exp, tail_exp, typ)
    return exp

def make_cmp_exp(left_exp, right_exp, cmpop='EqOp'):
    typ = p4specast.BoolT.INSTANCE
    optyp = left_exp.typ
    exp = p4specast.CmpE(cmpop, optyp, left_exp, right_exp, typ)
    return exp

def make_bin_exp(left_exp, right_exp, binop='AddOp'):
    typ = left_exp.typ
    optyp = left_exp.typ
    if binop in ('AndOp', 'OrOp', 'ImplOp', 'EquivOp'):
        typ = p4specast.BoolT.INSTANCE
    exp = p4specast.BinE(binop, optyp, left_exp, right_exp, typ)
    return exp

def make_un_exp(inner_exp, unop='NotOp'):
    if unop == 'NotOp':
        typ = p4specast.BoolT.INSTANCE
        optyp = 'boolT'
    else:
        typ = inner_exp.typ
        optyp = 'intT'
    exp = p4specast.UnE(unop, optyp, inner_exp, typ)
    return exp

def make_mem_exp(elem_exp, lst_exp):
    typ = p4specast.BoolT.INSTANCE
    exp = p4specast.MemE(elem_exp, lst_exp, typ)
    return exp

def make_downcast_exp(inner_exp, check_typ):
    exp = p4specast.DownCastE(check_typ, inner_exp, check_typ)
    return exp

def make_upcast_exp(inner_exp, check_typ):
    exp = p4specast.UpCastE(check_typ, inner_exp, check_typ)
    return exp

def make_match_exp(inner_exp, pattern):
    typ = p4specast.BoolT.INSTANCE
    exp = p4specast.MatchE(inner_exp, pattern, typ)
    return exp


class MockCont(object):
    def __init__(self):
        self.result = None
    def apply(self, value):
        self.result = value
        return None


def test_num_literal_cps():
    exp = make_num_exp(42)
    ctx = None
    k = MockCont()
    result = exp.eval_cps(ctx, k)

    assert isinstance(result, Done)
    assert result.k is k
    expected_value = make_num(42)
    assert result.value.value.val == expected_value.value.val


def test_bool_literal_cps():
    exp = make_bool_exp(True)
    ctx = None
    k = MockCont()
    result = exp.eval_cps(ctx, k)

    assert isinstance(result, Done)
    assert result.k is k
    expected_value = make_bool(True)
    assert result.value.value == expected_value.value


def test_text_literal_cps():
    exp = make_text_exp("hello")
    ctx = None
    k = MockCont()
    result = exp.eval_cps(ctx, k)

    assert isinstance(result, Done)
    assert result.k is k
    expected_value = make_text("hello")
    assert result.value.value == expected_value.value


def test_opt_none_cps():
    exp = make_opt_exp(None)
    ctx = None
    k = MockCont()
    result = exp.eval_cps(ctx, k)

    assert isinstance(result, Done)
    assert result.value is not None
    assert isinstance(result.value, objects.OptV)


def test_opt_some_cps():
    inner_exp = make_num_exp(42)
    exp = make_opt_exp(inner_exp)
    ctx = None
    k = MockCont()
    result = exp.eval_cps(ctx, k)

    assert isinstance(result, Next)
    assert result.exp is inner_exp
    assert isinstance(result.k, Cont)
    assert result.k.exp is exp
    assert result.k.k is k


def test_opt_apply_cps():
    inner_exp = make_num_exp(42)
    exp = make_opt_exp(inner_exp)
    ctx = None
    k = MockCont()
    inner_value = make_num(42)

    cont = Cont(exp, ctx, k)
    result = cont.apply(inner_value)

    assert isinstance(result, Done)
    assert result.k is k
    assert isinstance(result.value, objects.OptVSome)
    assert result.value.get_opt_value() is inner_value


def test_bool_false_literal_cps():
    exp = make_bool_exp(False)
    ctx = None
    k = MockCont()
    result = exp.eval_cps(ctx, k)

    assert isinstance(result, Done)
    assert result.k is k
    expected_value = make_bool(False)
    assert result.value.value == expected_value.value


def test_bool_cps_returns_correct_type():
    exp = make_bool_exp(True)
    ctx = None
    k = MockCont()
    result = exp.eval_cps(ctx, k)

    assert isinstance(result, Done)
    assert isinstance(result.value, objects.BoolV)
    assert result.value.get_typ() == p4specast.BoolT.INSTANCE


def test_bool_cps_with_different_continuations():
    exp = make_bool_exp(True)
    ctx = None

    k1 = MockCont()
    result1 = exp.eval_cps(ctx, k1)
    assert result1.k is k1

    k2 = MockCont()
    result2 = exp.eval_cps(ctx, k2)
    assert result2.k is k2
    assert result2.k is not k1


def test_bool_apply_raises():
    exp = make_bool_exp(True)
    cont = Cont(exp, None, MockCont())
    value = make_bool(True)

    with pytest.raises(AssertionError):
        exp.apply(cont, value)


def test_num_zero_cps():
    exp = make_num_exp(0)
    ctx = None
    k = MockCont()
    result = exp.eval_cps(ctx, k)

    assert isinstance(result, Done)
    assert result.k is k
    assert result.value.value.val == 0


def test_num_negative_cps():
    exp = make_num_exp(-42)
    ctx = None
    k = MockCont()
    result = exp.eval_cps(ctx, k)

    assert isinstance(result, Done)
    assert result.k is k
    assert result.value.value.val == -42


def test_num_large_positive_cps():
    exp = make_num_exp(1000000)
    ctx = None
    k = MockCont()
    result = exp.eval_cps(ctx, k)

    assert isinstance(result, Done)
    assert result.k is k
    assert result.value.value.val == 1000000


def test_num_large_negative_cps():
    exp = make_num_exp(-999999)
    ctx = None
    k = MockCont()
    result = exp.eval_cps(ctx, k)

    assert isinstance(result, Done)
    assert result.k is k
    assert result.value.value.val == -999999


def test_nat_literal_cps():
    exp = make_nat_exp(100)
    ctx = None
    k = MockCont()
    result = exp.eval_cps(ctx, k)

    assert isinstance(result, Done)
    assert result.k is k
    assert result.value.value.val == 100
    assert result.value.get_what() == p4specast.NatT.INSTANCE


def test_nat_zero_cps():
    exp = make_nat_exp(0)
    ctx = None
    k = MockCont()
    result = exp.eval_cps(ctx, k)

    assert isinstance(result, Done)
    assert result.k is k
    assert result.value.value.val == 0


def test_num_cps_returns_correct_type():
    exp = make_num_exp(42)
    ctx = None
    k = MockCont()
    result = exp.eval_cps(ctx, k)

    assert isinstance(result, Done)
    assert isinstance(result.value, objects.NumV)


def test_num_apply_raises():
    exp = make_num_exp(42)
    cont = Cont(exp, None, MockCont())
    value = make_num(42)

    with pytest.raises(AssertionError):
        exp.apply(cont, value)


def test_text_empty_cps():
    exp = make_text_exp("")
    ctx = None
    k = MockCont()
    result = exp.eval_cps(ctx, k)

    assert isinstance(result, Done)
    assert result.k is k
    assert result.value.value == ""


def test_text_whitespace_cps():
    exp = make_text_exp("   ")
    ctx = None
    k = MockCont()
    result = exp.eval_cps(ctx, k)

    assert isinstance(result, Done)
    assert result.k is k
    assert result.value.value == "   "


def test_text_special_chars_cps():
    exp = make_text_exp("hello\nworld\ttab")
    ctx = None
    k = MockCont()
    result = exp.eval_cps(ctx, k)

    assert isinstance(result, Done)
    assert result.k is k
    assert result.value.value == "hello\nworld\ttab"


def test_text_long_string_cps():
    long_text = "x" * 1000
    exp = make_text_exp(long_text)
    ctx = None
    k = MockCont()
    result = exp.eval_cps(ctx, k)

    assert isinstance(result, Done)
    assert result.k is k
    assert result.value.value == long_text
    assert len(result.value.value) == 1000


def test_text_cps_returns_correct_type():
    exp = make_text_exp("test")
    ctx = None
    k = MockCont()
    result = exp.eval_cps(ctx, k)

    assert isinstance(result, Done)
    assert isinstance(result.value, objects.TextV)


def test_text_apply_raises():
    exp = make_text_exp("test")
    cont = Cont(exp, None, MockCont())
    value = make_text("test")

    with pytest.raises(AssertionError):
        exp.apply(cont, value)


def test_opt_none_returns_optv():
    exp = make_opt_exp(None)
    ctx = None
    k = MockCont()
    result = exp.eval_cps(ctx, k)

    assert isinstance(result, Done)
    assert isinstance(result.value, objects.OptV)
    assert result.value.is_opt_none()


def test_opt_some_with_bool_cps():
    inner_exp = make_bool_exp(True)
    opt_typ = p4specast.IterT(inner_exp.typ, p4specast.Opt())
    exp = p4specast.OptE(inner_exp, opt_typ)
    ctx = None
    k = MockCont()
    result = exp.eval_cps(ctx, k)

    assert isinstance(result, Next)
    assert result.exp is inner_exp
    assert isinstance(result.k, Cont)


def test_opt_some_with_text_cps():
    inner_exp = make_text_exp("hello")
    opt_typ = p4specast.IterT(inner_exp.typ, p4specast.Opt())
    exp = p4specast.OptE(inner_exp, opt_typ)
    ctx = None
    k = MockCont()
    result = exp.eval_cps(ctx, k)

    assert isinstance(result, Next)
    assert result.exp is inner_exp


def test_opt_apply_with_bool_value():
    inner_exp = make_bool_exp(True)
    opt_typ = p4specast.IterT(inner_exp.typ, p4specast.Opt())
    exp = p4specast.OptE(inner_exp, opt_typ)
    ctx = None
    k = MockCont()
    inner_value = make_bool(True)

    cont = Cont(exp, ctx, k)
    result = cont.apply(inner_value)

    assert isinstance(result, Done)
    assert result.k is k
    assert isinstance(result.value, objects.OptVSome)
    assert result.value.get_opt_value() is inner_value


def test_opt_apply_with_text_value():
    inner_exp = make_text_exp("world")
    opt_typ = p4specast.IterT(inner_exp.typ, p4specast.Opt())
    exp = p4specast.OptE(inner_exp, opt_typ)
    ctx = None
    k = MockCont()
    inner_value = make_text("world")

    cont = Cont(exp, ctx, k)
    result = cont.apply(inner_value)

    assert isinstance(result, Done)
    assert result.k is k
    assert isinstance(result.value, objects.OptVSome)
    assert result.value.get_opt_value() is inner_value


def test_opt_nested_cps():
    inner_num_exp = make_num_exp(42)
    inner_opt_typ = p4specast.IterT(inner_num_exp.typ, p4specast.Opt())
    inner_opt_exp = p4specast.OptE(inner_num_exp, inner_opt_typ)

    outer_opt_typ = p4specast.IterT(inner_opt_typ, p4specast.Opt())
    outer_opt_exp = p4specast.OptE(inner_opt_exp, outer_opt_typ)
    ctx = None
    k = MockCont()
    result = outer_opt_exp.eval_cps(ctx, k)

    assert isinstance(result, Next)
    assert result.exp is inner_opt_exp


def test_opt_preserves_type():
    inner_exp = make_num_exp(42)
    exp = make_opt_exp(inner_exp)
    ctx = None
    k = MockCont()
    inner_value = make_num(42)

    cont = Cont(exp, ctx, k)
    result = cont.apply(inner_value)

    assert isinstance(result, Done)
    assert result.value.typ is exp.typ


def test_tuple_empty_cps():
    exp = make_tuple_exp([])
    ctx = None
    k = MockCont()
    result = exp.eval_cps(ctx, k)

    assert isinstance(result, Done)
    assert result.k is k
    assert isinstance(result.value, objects.TupleV)
    assert len(result.value.get_tuple()) == 0


def test_tuple_single_cps():
    inner_exp = make_num_exp(42)
    exp = make_tuple_exp([inner_exp])
    ctx = None
    k = MockCont()
    result = exp.eval_cps(ctx, k)

    assert isinstance(result, Next)
    assert result.exp is inner_exp
    assert isinstance(result.k, Cont)
    assert result.k.exp is exp
    assert result.k.k is k


def test_tuple_multiple_cps():
    exp1 = make_num_exp(1)
    exp2 = make_num_exp(2)
    exp3 = make_num_exp(3)
    exp = make_tuple_exp([exp1, exp2, exp3])
    ctx = None
    k = MockCont()
    result = exp.eval_cps(ctx, k)

    assert isinstance(result, Next)
    assert result.exp is exp1
    assert isinstance(result.k, Cont)
    assert result.k.k is k


def test_tuple_apply_single_cps():
    inner_exp = make_num_exp(42)
    exp = make_tuple_exp([inner_exp])
    ctx = None
    k = MockCont()
    inner_value = make_num(42)

    cont = Cont(exp, ctx, k)
    result = exp.apply(cont, inner_value)

    assert isinstance(result, Done)
    assert result.k is k
    assert isinstance(result.value, objects.TupleV)
    tuple_values = result.value.get_tuple()
    assert len(tuple_values) == 1
    assert tuple_values[0] is inner_value


def test_tuple_apply_multiple_cps():
    exp1 = make_num_exp(1)
    exp2 = make_num_exp(2)
    exp3 = make_num_exp(3)
    exp = make_tuple_exp([exp1, exp2, exp3])
    ctx = None
    k = MockCont()
    val1 = make_num(1)
    val2 = make_num(2)
    val3 = make_num(3)

    cont = Cont(exp, ctx, k)
    result = exp.apply(cont, val1)

    assert isinstance(result, Next)
    assert result.exp is exp2
    assert isinstance(result.k, Cont)
    assert isinstance(result.k.k, ValCont)
    assert result.k.k.value is val1

    cont2 = result.k
    result2 = exp.apply(cont2, val2)

    assert isinstance(result2, Next)
    assert result2.exp is exp3
    assert isinstance(result2.k.k, ValCont)
    assert result2.k.k.value is val2
    assert isinstance(result2.k.k.k, ValCont)
    assert result2.k.k.k.value is val1

    cont3 = result2.k
    result3 = exp.apply(cont3, val3)

    assert isinstance(result3, Done)
    assert result3.k is k
    assert isinstance(result3.value, objects.TupleV)
    tuple_values = result3.value.get_tuple()
    assert len(tuple_values) == 3
    assert tuple_values[0] is val1
    assert tuple_values[1] is val2
    assert tuple_values[2] is val3


def test_list_empty_cps():
    exp = make_list_exp([])
    ctx = None
    k = MockCont()
    result = exp.eval_cps(ctx, k)

    assert isinstance(result, Done)
    assert result.k is k
    assert isinstance(result.value, objects.ListV)
    assert len(result.value.get_list()) == 0


def test_list_single_cps():
    inner_exp = make_num_exp(42)
    exp = make_list_exp([inner_exp])
    ctx = None
    k = MockCont()
    result = exp.eval_cps(ctx, k)

    assert isinstance(result, Next)
    assert result.exp is inner_exp
    assert isinstance(result.k, Cont)
    assert result.k.exp is exp
    assert result.k.k is k


def test_list_multiple_cps():
    exp1 = make_num_exp(1)
    exp2 = make_num_exp(2)
    exp3 = make_num_exp(3)
    exp = make_list_exp([exp1, exp2, exp3])
    ctx = None
    k = MockCont()
    result = exp.eval_cps(ctx, k)

    assert isinstance(result, Next)
    assert result.exp is exp1
    assert isinstance(result.k, Cont)
    assert result.k.k is k


def test_list_apply_single_cps():
    inner_exp = make_num_exp(42)
    exp = make_list_exp([inner_exp])
    ctx = None
    k = MockCont()
    inner_value = make_num(42)

    cont = Cont(exp, ctx, k)
    result = exp.apply(cont, inner_value)

    assert isinstance(result, Done)
    assert result.k is k
    assert isinstance(result.value, objects.ListV)
    list_values = result.value.get_list()
    assert len(list_values) == 1
    assert list_values[0] is inner_value


def test_list_apply_multiple_cps():
    exp1 = make_num_exp(1)
    exp2 = make_num_exp(2)
    exp3 = make_num_exp(3)
    exp = make_list_exp([exp1, exp2, exp3])
    ctx = None
    k = MockCont()
    val1 = make_num(1)
    val2 = make_num(2)
    val3 = make_num(3)

    cont = Cont(exp, ctx, k)
    result = exp.apply(cont, val1)

    assert isinstance(result, Next)
    assert result.exp is exp2
    assert isinstance(result.k, Cont)
    assert isinstance(result.k.k, ValCont)
    assert result.k.k.value is val1

    cont2 = result.k
    result2 = exp.apply(cont2, val2)

    assert isinstance(result2, Next)
    assert result2.exp is exp3
    assert isinstance(result2.k.k, ValCont)
    assert result2.k.k.value is val2
    assert isinstance(result2.k.k.k, ValCont)
    assert result2.k.k.k.value is val1

    cont3 = result2.k
    result3 = exp.apply(cont3, val3)

    assert isinstance(result3, Done)
    assert result3.k is k
    assert isinstance(result3.value, objects.ListV)
    list_values = result3.value.get_list()
    assert len(list_values) == 3
    assert list_values[0] is val1
    assert list_values[1] is val2
    assert list_values[2] is val3


def test_cons_cps():
    head_exp = make_num_exp(1)
    tail_exp = make_list_exp([make_num_exp(2), make_num_exp(3)])
    exp = make_cons_exp(head_exp, tail_exp)
    ctx = None
    k = MockCont()
    result = exp.eval_cps(ctx, k)

    assert isinstance(result, Next)
    assert result.exp is head_exp
    assert isinstance(result.k, Cont)
    assert result.k.exp is exp
    assert result.k.k is k


def test_cons_apply_head_cps():
    head_exp = make_num_exp(1)
    tail_exp = make_list_exp([make_num_exp(2), make_num_exp(3)])
    exp = make_cons_exp(head_exp, tail_exp)
    ctx = None
    k = MockCont()
    head_value = make_num(1)

    cont = Cont(exp, ctx, k)
    result = exp.apply(cont, head_value)

    assert isinstance(result, Next)
    assert result.exp is tail_exp
    assert isinstance(result.k, Cont)
    assert isinstance(result.k.k, ValCont)
    assert result.k.k.value is head_value


def test_cons_apply_tail_cps():
    head_exp = make_num_exp(1)
    tail_exp = make_list_exp([make_num_exp(2), make_num_exp(3)])
    exp = make_cons_exp(head_exp, tail_exp)
    ctx = None
    k = MockCont()
    head_value = make_num(1)
    tail_value = objects.ListV.make([make_num(2), make_num(3)], tail_exp.typ)

    val_k = ValCont(head_value, k)
    cont = Cont(exp, ctx, val_k)
    result = exp.apply(cont, tail_value)

    assert isinstance(result, Done)
    assert result.k is k
    assert isinstance(result.value, objects.ListV)
    list_values = result.value.get_list()
    assert len(list_values) == 3
    assert list_values[0].value.val == head_value.value.val


def test_cmp_cps():
    left_exp = make_num_exp(1)
    right_exp = make_num_exp(2)
    exp = make_cmp_exp(left_exp, right_exp, 'EqOp')
    ctx = None
    k = MockCont()
    result = exp.eval_cps(ctx, k)

    assert isinstance(result, Next)
    assert result.exp is left_exp
    assert isinstance(result.k, Cont)
    assert result.k.exp is exp
    assert result.k.k is k


def test_cmp_apply_left_cps():
    left_exp = make_num_exp(1)
    right_exp = make_num_exp(2)
    exp = make_cmp_exp(left_exp, right_exp, 'EqOp')
    ctx = None
    k = MockCont()
    left_value = make_num(1)

    cont = Cont(exp, ctx, k)
    result = exp.apply(cont, left_value)

    assert isinstance(result, Next)
    assert result.exp is right_exp
    assert isinstance(result.k, Cont)
    assert isinstance(result.k.k, ValCont)
    assert result.k.k.value is left_value


def test_cmp_apply_right_eq_cps():
    left_exp = make_num_exp(42)
    right_exp = make_num_exp(42)
    exp = make_cmp_exp(left_exp, right_exp, 'EqOp')
    ctx = None
    k = MockCont()
    left_value = make_num(42)
    right_value = make_num(42)

    val_k = ValCont(left_value, k)
    cont = Cont(exp, ctx, val_k)
    result = exp.apply(cont, right_value)

    assert isinstance(result, Done)
    assert result.k is k
    assert isinstance(result.value, objects.BoolV)
    assert result.value.value == True


def test_cmp_apply_right_ne_cps():
    left_exp = make_num_exp(1)
    right_exp = make_num_exp(2)
    exp = make_cmp_exp(left_exp, right_exp, 'NeOp')
    ctx = None
    k = MockCont()
    left_value = make_num(1)
    right_value = make_num(2)

    val_k = ValCont(left_value, k)
    cont = Cont(exp, ctx, val_k)
    result = exp.apply(cont, right_value)

    assert isinstance(result, Done)
    assert result.k is k
    assert isinstance(result.value, objects.BoolV)
    assert result.value.value == True


def test_cmp_apply_right_lt_cps():
    left_exp = make_num_exp(1)
    right_exp = make_num_exp(2)
    exp = make_cmp_exp(left_exp, right_exp, 'LtOp')
    ctx = None
    k = MockCont()
    left_value = make_num(1)
    right_value = make_num(2)

    val_k = ValCont(left_value, k)
    cont = Cont(exp, ctx, val_k)
    result = exp.apply(cont, right_value)

    assert isinstance(result, Done)
    assert result.k is k
    assert isinstance(result.value, objects.BoolV)
    assert result.value.value == True


def test_bin_cps():
    left_exp = make_num_exp(1)
    right_exp = make_num_exp(2)
    exp = make_bin_exp(left_exp, right_exp, 'AddOp')
    ctx = None
    k = MockCont()
    result = exp.eval_cps(ctx, k)

    assert isinstance(result, Next)
    assert result.exp is left_exp
    assert isinstance(result.k, Cont)
    assert result.k.exp is exp
    assert result.k.k is k


def test_bin_apply_left_cps():
    left_exp = make_num_exp(1)
    right_exp = make_num_exp(2)
    exp = make_bin_exp(left_exp, right_exp, 'AddOp')
    ctx = None
    k = MockCont()
    left_value = make_num(1)

    cont = Cont(exp, ctx, k)
    result = exp.apply(cont, left_value)

    assert isinstance(result, Next)
    assert result.exp is right_exp
    assert isinstance(result.k, Cont)
    assert isinstance(result.k.k, ValCont)
    assert result.k.k.value is left_value


def test_bin_apply_right_add_cps():
    left_exp = make_num_exp(1)
    right_exp = make_num_exp(2)
    exp = make_bin_exp(left_exp, right_exp, 'AddOp')
    ctx = None
    k = MockCont()
    left_value = make_num(1)
    right_value = make_num(2)

    val_k = ValCont(left_value, k)
    cont = Cont(exp, ctx, val_k)
    result = exp.apply(cont, right_value)

    assert isinstance(result, Done)
    assert result.k is k
    assert isinstance(result.value, objects.NumV)
    assert result.value.value.val == 3


def test_bin_apply_right_sub_cps():
    left_exp = make_num_exp(5)
    right_exp = make_num_exp(3)
    exp = make_bin_exp(left_exp, right_exp, 'SubOp')
    ctx = None
    k = MockCont()
    left_value = make_num(5)
    right_value = make_num(3)

    val_k = ValCont(left_value, k)
    cont = Cont(exp, ctx, val_k)
    result = exp.apply(cont, right_value)

    assert isinstance(result, Done)
    assert result.k is k
    assert isinstance(result.value, objects.NumV)
    assert result.value.value.val == 2


def test_bin_apply_right_mul_cps():
    left_exp = make_num_exp(3)
    right_exp = make_num_exp(4)
    exp = make_bin_exp(left_exp, right_exp, 'MulOp')
    ctx = None
    k = MockCont()
    left_value = make_num(3)
    right_value = make_num(4)

    val_k = ValCont(left_value, k)
    cont = Cont(exp, ctx, val_k)
    result = exp.apply(cont, right_value)

    assert isinstance(result, Done)
    assert result.k is k
    assert isinstance(result.value, objects.NumV)
    assert result.value.value.val == 12


def test_bin_apply_right_and_cps():
    left_exp = make_bool_exp(True)
    right_exp = make_bool_exp(False)
    exp = make_bin_exp(left_exp, right_exp, 'AndOp')
    ctx = None
    k = MockCont()
    left_value = make_bool(True)
    right_value = make_bool(False)

    val_k = ValCont(left_value, k)
    cont = Cont(exp, ctx, val_k)
    result = exp.apply(cont, right_value)

    assert isinstance(result, Done)
    assert result.k is k
    assert isinstance(result.value, objects.BoolV)
    assert result.value.value == False


def test_bin_apply_right_or_cps():
    left_exp = make_bool_exp(True)
    right_exp = make_bool_exp(False)
    exp = make_bin_exp(left_exp, right_exp, 'OrOp')
    ctx = None
    k = MockCont()
    left_value = make_bool(True)
    right_value = make_bool(False)

    val_k = ValCont(left_value, k)
    cont = Cont(exp, ctx, val_k)
    result = exp.apply(cont, right_value)

    assert isinstance(result, Done)
    assert result.k is k
    assert isinstance(result.value, objects.BoolV)
    assert result.value.value == True


def test_un_cps():
    inner_exp = make_bool_exp(True)
    exp = make_un_exp(inner_exp, 'NotOp')
    ctx = None
    k = MockCont()
    result = exp.eval_cps(ctx, k)

    assert isinstance(result, Next)
    assert result.exp is inner_exp
    assert isinstance(result.k, Cont)
    assert result.k.exp is exp
    assert result.k.k is k


def test_un_apply_not_true_cps():
    inner_exp = make_bool_exp(True)
    exp = make_un_exp(inner_exp, 'NotOp')
    ctx = None
    k = MockCont()
    inner_value = make_bool(True)

    cont = Cont(exp, ctx, k)
    result = exp.apply(cont, inner_value)

    assert isinstance(result, Done)
    assert result.k is k
    assert isinstance(result.value, objects.BoolV)
    assert result.value.value == False


def test_un_apply_not_false_cps():
    inner_exp = make_bool_exp(False)
    exp = make_un_exp(inner_exp, 'NotOp')
    ctx = None
    k = MockCont()
    inner_value = make_bool(False)

    cont = Cont(exp, ctx, k)
    result = exp.apply(cont, inner_value)

    assert isinstance(result, Done)
    assert result.k is k
    assert isinstance(result.value, objects.BoolV)
    assert result.value.value == True


def test_un_apply_plus_cps():
    inner_exp = make_num_exp(42)
    exp = make_un_exp(inner_exp, 'PlusOp')
    ctx = None
    k = MockCont()
    inner_value = make_num(42)

    cont = Cont(exp, ctx, k)
    result = exp.apply(cont, inner_value)

    assert isinstance(result, Done)
    assert result.k is k
    assert isinstance(result.value, objects.NumV)
    assert result.value.value.val == 42


def test_un_apply_minus_cps():
    inner_exp = make_num_exp(42)
    exp = make_un_exp(inner_exp, 'MinusOp')
    ctx = None
    k = MockCont()
    inner_value = make_num(42)

    cont = Cont(exp, ctx, k)
    result = exp.apply(cont, inner_value)

    assert isinstance(result, Done)
    assert result.k is k
    assert isinstance(result.value, objects.NumV)
    assert result.value.value.val == -42


def test_un_apply_minus_negative_cps():
    inner_exp = make_num_exp(-5)
    exp = make_un_exp(inner_exp, 'MinusOp')
    ctx = None
    k = MockCont()
    inner_value = make_num(-5)

    cont = Cont(exp, ctx, k)
    result = exp.apply(cont, inner_value)

    assert isinstance(result, Done)
    assert result.k is k
    assert isinstance(result.value, objects.NumV)
    assert result.value.value.val == 5


def test_mem_cps():
    elem_exp = make_num_exp(1)
    lst_exp = make_list_exp([make_num_exp(1), make_num_exp(2), make_num_exp(3)])
    exp = make_mem_exp(elem_exp, lst_exp)
    ctx = None
    k = MockCont()
    result = exp.eval_cps(ctx, k)

    assert isinstance(result, Next)
    assert result.exp is elem_exp
    assert isinstance(result.k, Cont)
    assert result.k.exp is exp
    assert result.k.k is k


def test_mem_apply_elem_cps():
    elem_exp = make_num_exp(1)
    lst_exp = make_list_exp([make_num_exp(1), make_num_exp(2)])
    exp = make_mem_exp(elem_exp, lst_exp)
    ctx = None
    k = MockCont()
    elem_value = make_num(1)

    cont = Cont(exp, ctx, k)
    result = exp.apply(cont, elem_value)

    assert isinstance(result, Next)
    assert result.exp is lst_exp
    assert isinstance(result.k, Cont)
    assert isinstance(result.k.k, ValCont)
    assert result.k.k.value is elem_value


def test_mem_apply_lst_found_cps():
    elem_exp = make_num_exp(2)
    lst_exp = make_list_exp([make_num_exp(1), make_num_exp(2), make_num_exp(3)])
    exp = make_mem_exp(elem_exp, lst_exp)
    ctx = None
    k = MockCont()
    elem_value = make_num(2)
    lst_value = objects.ListV.make([make_num(1), make_num(2), make_num(3)], lst_exp.typ)

    val_k = ValCont(elem_value, k)
    cont = Cont(exp, ctx, val_k)
    result = exp.apply(cont, lst_value)

    assert isinstance(result, Done)
    assert result.k is k
    assert isinstance(result.value, objects.BoolV)
    assert result.value.value == True


def test_mem_apply_lst_not_found_cps():
    elem_exp = make_num_exp(5)
    lst_exp = make_list_exp([make_num_exp(1), make_num_exp(2), make_num_exp(3)])
    exp = make_mem_exp(elem_exp, lst_exp)
    ctx = None
    k = MockCont()
    elem_value = make_num(5)
    lst_value = objects.ListV.make([make_num(1), make_num(2), make_num(3)], lst_exp.typ)

    val_k = ValCont(elem_value, k)
    cont = Cont(exp, ctx, val_k)
    result = exp.apply(cont, lst_value)

    assert isinstance(result, Done)
    assert result.k is k
    assert isinstance(result.value, objects.BoolV)
    assert result.value.value == False


def test_mem_apply_empty_list_cps():
    elem_exp = make_num_exp(1)
    lst_exp = make_list_exp([])
    exp = make_mem_exp(elem_exp, lst_exp)
    ctx = None
    k = MockCont()
    elem_value = make_num(1)
    lst_value = objects.ListV.make([], lst_exp.typ)

    val_k = ValCont(elem_value, k)
    cont = Cont(exp, ctx, val_k)
    result = exp.apply(cont, lst_value)

    assert isinstance(result, Done)
    assert result.k is k
    assert isinstance(result.value, objects.BoolV)
    assert result.value.value == False


def test_mem_apply_single_elem_list_cps():
    elem_exp = make_num_exp(42)
    lst_exp = make_list_exp([make_num_exp(42)])
    exp = make_mem_exp(elem_exp, lst_exp)
    ctx = None
    k = MockCont()
    elem_value = make_num(42)
    lst_value = objects.ListV.make([make_num(42)], lst_exp.typ)

    val_k = ValCont(elem_value, k)
    cont = Cont(exp, ctx, val_k)
    result = exp.apply(cont, lst_value)

    assert isinstance(result, Done)
    assert result.k is k
    assert isinstance(result.value, objects.BoolV)
    assert result.value.value == True


def test_downcast_cps():
    inner_exp = make_num_exp(42)
    check_typ = p4specast.NumT.INT
    exp = make_downcast_exp(inner_exp, check_typ)
    ctx = None
    k = MockCont()
    result = exp.eval_cps(ctx, k)

    assert isinstance(result, Next)
    assert result.exp is inner_exp
    assert isinstance(result.k, Cont)
    assert result.k.exp is exp
    assert result.k.k is k


def test_downcast_apply_nat_to_nat_cps():
    inner_exp = make_nat_exp(42)
    check_typ = p4specast.NumT.NAT
    exp = make_downcast_exp(inner_exp, check_typ)

    from rpyp4sp.context import Context
    ctx = Context()
    k = MockCont()
    inner_value = make_nat(42)

    cont = Cont(exp, ctx, k)
    result = exp.apply(cont, inner_value)

    assert isinstance(result, Done)
    assert result.k is k
    assert isinstance(result.value, objects.NumV)
    assert result.value.value.val == 42


def test_downcast_apply_int_to_nat_cps():
    inner_exp = make_num_exp(42)
    check_typ = p4specast.NumT.NAT
    exp = make_downcast_exp(inner_exp, check_typ)

    from rpyp4sp.context import Context
    ctx = Context()
    k = MockCont()
    inner_value = make_num(42)

    cont = Cont(exp, ctx, k)
    result = exp.apply(cont, inner_value)

    assert isinstance(result, Done)
    assert result.k is k
    assert isinstance(result.value, objects.NumV)
    assert result.value.value.val == 42
    assert result.value.get_what() == p4specast.NatT.INSTANCE


def test_upcast_cps():
    inner_exp = make_nat_exp(42)
    check_typ = p4specast.NumT.INT
    exp = make_upcast_exp(inner_exp, check_typ)
    ctx = None
    k = MockCont()
    result = exp.eval_cps(ctx, k)

    assert isinstance(result, Next)
    assert result.exp is inner_exp
    assert isinstance(result.k, Cont)
    assert result.k.exp is exp
    assert result.k.k is k


def test_upcast_apply_nat_to_int_cps():
    inner_exp = make_nat_exp(42)
    check_typ = p4specast.NumT.INT
    exp = make_upcast_exp(inner_exp, check_typ)

    from rpyp4sp.context import Context
    ctx = Context()
    k = MockCont()
    inner_value = make_nat(42)

    cont = Cont(exp, ctx, k)
    result = exp.apply(cont, inner_value)

    assert isinstance(result, Done)
    assert result.k is k
    assert isinstance(result.value, objects.NumV)
    assert result.value.value.val == 42
    assert result.value.get_what() == p4specast.IntT.INSTANCE


def test_match_cps():
    inner_exp = make_list_exp([])
    pattern = p4specast.ListP(p4specast.Nil())
    exp = make_match_exp(inner_exp, pattern)
    ctx = None
    k = MockCont()
    result = exp.eval_cps(ctx, k)

    assert isinstance(result, Next)
    assert result.exp is inner_exp
    assert isinstance(result.k, Cont)
    assert result.k.exp is exp
    assert result.k.k is k


def test_match_apply_list_nil_match_cps():
    inner_exp = make_list_exp([])
    pattern = p4specast.ListP(p4specast.Nil())
    exp = make_match_exp(inner_exp, pattern)
    ctx = None
    k = MockCont()
    inner_value = objects.ListV.make([], inner_exp.typ)

    cont = Cont(exp, ctx, k)
    result = exp.apply(cont, inner_value)

    assert isinstance(result, Done)
    assert result.k is k
    assert isinstance(result.value, objects.BoolV)
    assert result.value.value == True


def test_match_apply_list_nil_no_match_cps():
    inner_exp = make_list_exp([make_num_exp(1)])
    pattern = p4specast.ListP(p4specast.Nil())
    exp = make_match_exp(inner_exp, pattern)
    ctx = None
    k = MockCont()
    inner_value = objects.ListV.make([make_num(1)], inner_exp.typ)

    cont = Cont(exp, ctx, k)
    result = exp.apply(cont, inner_value)

    assert isinstance(result, Done)
    assert result.k is k
    assert isinstance(result.value, objects.BoolV)
    assert result.value.value == False


def test_match_apply_list_cons_match_cps():
    inner_exp = make_list_exp([make_num_exp(1), make_num_exp(2)])
    pattern = p4specast.ListP(p4specast.Cons())
    exp = make_match_exp(inner_exp, pattern)
    ctx = None
    k = MockCont()
    inner_value = objects.ListV.make([make_num(1), make_num(2)], inner_exp.typ)

    cont = Cont(exp, ctx, k)
    result = exp.apply(cont, inner_value)

    assert isinstance(result, Done)
    assert result.k is k
    assert isinstance(result.value, objects.BoolV)
    assert result.value.value == True


def test_match_apply_list_cons_no_match_cps():
    inner_exp = make_list_exp([])
    pattern = p4specast.ListP(p4specast.Cons())
    exp = make_match_exp(inner_exp, pattern)
    ctx = None
    k = MockCont()
    inner_value = objects.ListV.make([], inner_exp.typ)

    cont = Cont(exp, ctx, k)
    result = exp.apply(cont, inner_value)

    assert isinstance(result, Done)
    assert result.k is k
    assert isinstance(result.value, objects.BoolV)
    assert result.value.value == False


def test_match_apply_list_fixed_match_cps():
    inner_exp = make_list_exp([make_num_exp(1), make_num_exp(2), make_num_exp(3)])
    pattern = p4specast.ListP(p4specast.Fixed(3))
    exp = make_match_exp(inner_exp, pattern)
    ctx = None
    k = MockCont()
    inner_value = objects.ListV.make([make_num(1), make_num(2), make_num(3)], inner_exp.typ)

    cont = Cont(exp, ctx, k)
    result = exp.apply(cont, inner_value)

    assert isinstance(result, Done)
    assert result.k is k
    assert isinstance(result.value, objects.BoolV)
    assert result.value.value == True


def test_match_apply_list_fixed_no_match_cps():
    inner_exp = make_list_exp([make_num_exp(1), make_num_exp(2)])
    pattern = p4specast.ListP(p4specast.Fixed(3))
    exp = make_match_exp(inner_exp, pattern)
    ctx = None
    k = MockCont()
    inner_value = objects.ListV.make([make_num(1), make_num(2)], inner_exp.typ)

    cont = Cont(exp, ctx, k)
    result = exp.apply(cont, inner_value)

    assert isinstance(result, Done)
    assert result.k is k
    assert isinstance(result.value, objects.BoolV)
    assert result.value.value == False


def test_match_apply_opt_some_match_cps():
    inner_num_exp = make_num_exp(42)
    inner_exp = make_opt_exp(inner_num_exp)
    pattern = p4specast.OptP('Some')
    exp = make_match_exp(inner_exp, pattern)
    ctx = None
    k = MockCont()
    inner_value = objects.OptVSome(make_num(42), inner_exp.typ)

    cont = Cont(exp, ctx, k)
    result = exp.apply(cont, inner_value)

    assert isinstance(result, Done)
    assert result.k is k
    assert isinstance(result.value, objects.BoolV)
    assert result.value.value == True


def test_match_apply_opt_some_no_match_cps():
    inner_exp = make_opt_exp(None)
    pattern = p4specast.OptP('Some')
    exp = make_match_exp(inner_exp, pattern)
    ctx = None
    k = MockCont()
    inner_value = objects.OptV(inner_exp.typ)

    cont = Cont(exp, ctx, k)
    result = exp.apply(cont, inner_value)

    assert isinstance(result, Done)
    assert result.k is k
    assert isinstance(result.value, objects.BoolV)
    assert result.value.value == False


def test_match_apply_opt_none_match_cps():
    inner_exp = make_opt_exp(None)
    pattern = p4specast.OptP('None')
    exp = make_match_exp(inner_exp, pattern)
    ctx = None
    k = MockCont()
    inner_value = objects.OptV(inner_exp.typ)

    cont = Cont(exp, ctx, k)
    result = exp.apply(cont, inner_value)

    assert isinstance(result, Done)
    assert result.k is k
    assert isinstance(result.value, objects.BoolV)
    assert result.value.value == True


def test_match_apply_opt_none_no_match_cps():
    inner_num_exp = make_num_exp(42)
    inner_exp = make_opt_exp(inner_num_exp)
    pattern = p4specast.OptP('None')
    exp = make_match_exp(inner_exp, pattern)
    ctx = None
    k = MockCont()
    inner_value = objects.OptVSome(make_num(42), inner_exp.typ)

    cont = Cont(exp, ctx, k)
    result = exp.apply(cont, inner_value)

    assert isinstance(result, Done)
    assert result.k is k
    assert isinstance(result.value, objects.BoolV)
    assert result.value.value == False


def make_downcast_exp(inner_exp, check_typ):
    """Create a DownCastE expression (exp as typ)."""
    exp = p4specast.DownCastE(check_typ, inner_exp, check_typ)
    return exp


def test_downcast_cps():
    """Test CPS evaluation of DownCastE - should evaluate inner expression first."""
    inner_exp = make_num_exp(42)
    check_typ = p4specast.NumT.NAT
    exp = make_downcast_exp(inner_exp, check_typ)
    ctx = None

    k = MockCont()
    result = exp.eval_cps(ctx, k)

    # Should return Next to evaluate the inner expression first
    assert isinstance(result, Next), "Expected Next object for DownCastE"
    assert result.exp is inner_exp, "Should evaluate inner expression first"

    # Verify the continuation is Cont
    assert isinstance(result.k, Cont), "Continuation should be Cont"
    assert result.k.exp is exp, "Cont should reference the DownCastE expression"
    assert result.k.k is k, "Cont should preserve the original continuation"


def test_downcast_apply_int_to_nat_cps():
    """Test DownCastE continuation application - int to nat (positive int)."""
    inner_exp = make_num_exp(42)
    check_typ = p4specast.NumT.NAT
    exp = make_downcast_exp(inner_exp, check_typ)
    ctx = None

    k = MockCont()
    inner_value = make_num(42)  # int value

    cont = Cont(exp, ctx, k)
    result = exp.apply(cont, inner_value)

    # Should return Done with downcasted value
    assert isinstance(result, Done), "Expected Done after applying downcast"
    assert result.k is k, "Should use the original continuation"
    assert isinstance(result.value, objects.NumV), "Value should be NumV"
    assert result.value.value.val == 42, "Value should be 42"
    assert result.value.get_what() == p4specast.NatT.INSTANCE, "Should be nat type"


def test_downcast_apply_nat_to_nat_cps():
    """Test DownCastE continuation application - nat to nat (no change)."""
    inner_exp = make_nat_exp(42)
    check_typ = p4specast.NumT.NAT
    exp = make_downcast_exp(inner_exp, check_typ)
    ctx = None

    k = MockCont()
    inner_value = make_nat(42)  # nat value

    cont = Cont(exp, ctx, k)
    result = exp.apply(cont, inner_value)

    # Should return Done with same value (nat already)
    assert isinstance(result, Done), "Expected Done after applying downcast"
    assert result.k is k, "Should use the original continuation"
    assert isinstance(result.value, objects.NumV), "Value should be NumV"
    assert result.value.value.val == 42, "Value should be 42"
    assert result.value.get_what() == p4specast.NatT.INSTANCE, "Should be nat type"


def make_upcast_exp(inner_exp, check_typ):
    """Create an UpCastE expression (exp : typ)."""
    exp = p4specast.UpCastE(check_typ, inner_exp, check_typ)
    return exp


def test_upcast_cps():
    """Test CPS evaluation of UpCastE - should evaluate inner expression first."""
    inner_exp = make_nat_exp(42)
    check_typ = p4specast.NumT.INT
    exp = make_upcast_exp(inner_exp, check_typ)
    ctx = None

    k = MockCont()
    result = exp.eval_cps(ctx, k)

    # Should return Next to evaluate the inner expression first
    assert isinstance(result, Next), "Expected Next object for UpCastE"
    assert result.exp is inner_exp, "Should evaluate inner expression first"

    # Verify the continuation is Cont
    assert isinstance(result.k, Cont), "Continuation should be Cont"
    assert result.k.exp is exp, "Cont should reference the UpCastE expression"
    assert result.k.k is k, "Cont should preserve the original continuation"


def test_upcast_apply_nat_to_int_cps():
    """Test UpCastE continuation application - nat to int."""
    inner_exp = make_nat_exp(42)
    check_typ = p4specast.NumT.INT
    exp = make_upcast_exp(inner_exp, check_typ)
    ctx = None

    k = MockCont()
    inner_value = make_nat(42)  # nat value

    cont = Cont(exp, ctx, k)
    result = exp.apply(cont, inner_value)

    # Should return Done with upcasted value
    assert isinstance(result, Done), "Expected Done after applying upcast"
    assert result.k is k, "Should use the original continuation"
    assert isinstance(result.value, objects.NumV), "Value should be NumV"
    assert result.value.value.val == 42, "Value should be 42"
    assert result.value.get_what() == p4specast.IntT.INSTANCE, "Should be int type"


def make_cat_exp(left_exp, right_exp):
    """Create a CatE expression (left ++ right)."""
    typ = left_exp.typ
    exp = p4specast.CatE(left_exp, right_exp, typ)
    return exp


def test_cat_cps():
    """Test CPS evaluation of CatE - should evaluate left first."""
    left_exp = make_text_exp("hello")
    right_exp = make_text_exp(" world")
    exp = make_cat_exp(left_exp, right_exp)
    ctx = None

    k = MockCont()
    result = exp.eval_cps(ctx, k)

    # Should return Next to evaluate the left expression first
    assert isinstance(result, Next), "Expected Next object for CatE"
    assert result.exp is left_exp, "Should evaluate left expression first"

    # Verify the continuation is Cont
    assert isinstance(result.k, Cont), "Continuation should be Cont"
    assert result.k.exp is exp, "Cont should reference the CatE expression"
    assert result.k.k is k, "Cont should preserve the original continuation"


def test_cat_apply_left_cps():
    """Test CatE continuation application after evaluating left."""
    left_exp = make_text_exp("hello")
    right_exp = make_text_exp(" world")
    exp = make_cat_exp(left_exp, right_exp)
    ctx = None

    k = MockCont()
    left_value = make_text("hello")

    # Create continuation (just evaluated left)
    cont = Cont(exp, ctx, k)
    result = exp.apply(cont, left_value)

    # Should return Next to evaluate the right expression
    from rpyp4sp.continuation import ValCont
    assert isinstance(result, Next), "Expected Next after applying left"
    assert result.exp is right_exp, "Should evaluate right expression"
    assert isinstance(result.k, Cont), "Continuation should be Cont"
    assert isinstance(result.k.k, ValCont), "Cont.k should be ValCont"
    assert result.k.k.value is left_value, "ValCont should store the left value"


def test_cat_apply_right_text_cps():
    """Test CatE continuation application for text concatenation."""
    left_exp = make_text_exp("hello")
    right_exp = make_text_exp(" world")
    exp = make_cat_exp(left_exp, right_exp)
    ctx = None

    k = MockCont()
    left_value = make_text("hello")
    right_value = make_text(" world")

    # Create continuation with ValCont wrapping left_value (just evaluated right)
    from rpyp4sp.continuation import ValCont
    val_k = ValCont(left_value, k)
    cont = Cont(exp, ctx, val_k)
    result = exp.apply(cont, right_value)

    # Should return Done with concatenated text
    assert isinstance(result, Done), "Expected Done after applying right"
    assert result.k is k, "Should use the original continuation"
    assert isinstance(result.value, objects.TextV), "Value should be TextV"
    assert result.value.value == "hello world", "Should be 'hello world'"


def test_cat_apply_right_list_cps():
    """Test CatE continuation application for list concatenation."""
    left_exp = make_list_exp([make_num_exp(1), make_num_exp(2)])
    right_exp = make_list_exp([make_num_exp(3), make_num_exp(4)])
    exp = make_cat_exp(left_exp, right_exp)
    ctx = None

    k = MockCont()
    left_value = objects.ListV.make([make_num(1), make_num(2)], left_exp.typ)
    right_value = objects.ListV.make([make_num(3), make_num(4)], right_exp.typ)

    # Create continuation with ValCont wrapping left_value (just evaluated right)
    from rpyp4sp.continuation import ValCont
    val_k = ValCont(left_value, k)
    cont = Cont(exp, ctx, val_k)
    result = exp.apply(cont, right_value)

    # Should return Done with concatenated list
    assert isinstance(result, Done), "Expected Done after applying right"
    assert result.k is k, "Should use the original continuation"
    assert isinstance(result.value, objects.ListV), "Value should be ListV"
    list_values = result.value.get_list()
    assert len(list_values) == 4, "List should have 4 elements"
    assert list_values[0].value.val == 1
    assert list_values[1].value.val == 2
    assert list_values[2].value.val == 3
    assert list_values[3].value.val == 4


def test_cat_apply_right_empty_left_list_cps():
    """Test CatE continuation application for list concat with empty left."""
    left_exp = make_list_exp([])
    right_exp = make_list_exp([make_num_exp(1), make_num_exp(2)])
    exp = make_cat_exp(left_exp, right_exp)
    ctx = None

    k = MockCont()
    left_value = objects.ListV.make([], left_exp.typ)
    right_value = objects.ListV.make([make_num(1), make_num(2)], right_exp.typ)

    from rpyp4sp.continuation import ValCont
    val_k = ValCont(left_value, k)
    cont = Cont(exp, ctx, val_k)
    result = exp.apply(cont, right_value)

    # Should return Done with right list (optimization for empty left)
    assert isinstance(result, Done), "Expected Done after applying right"
    assert result.k is k, "Should use the original continuation"
    assert isinstance(result.value, objects.ListV), "Value should be ListV"
    assert result.value is right_value, "Should return right list directly"


def test_cat_apply_right_empty_right_list_cps():
    """Test CatE continuation application for list concat with empty right."""
    left_exp = make_list_exp([make_num_exp(1), make_num_exp(2)])
    right_exp = make_list_exp([])
    exp = make_cat_exp(left_exp, right_exp)
    ctx = None

    k = MockCont()
    left_value = objects.ListV.make([make_num(1), make_num(2)], left_exp.typ)
    right_value = objects.ListV.make([], right_exp.typ)

    from rpyp4sp.continuation import ValCont
    val_k = ValCont(left_value, k)
    cont = Cont(exp, ctx, val_k)
    result = exp.apply(cont, right_value)

    # Should return Done with left list (optimization for empty right)
    assert isinstance(result, Done), "Expected Done after applying right"
    assert result.k is k, "Should use the original continuation"
    assert isinstance(result.value, objects.ListV), "Value should be ListV"
    assert result.value is left_value, "Should return left list directly"
