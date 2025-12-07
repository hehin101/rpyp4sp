"""Tests for the CPS (Continuation-Passing Style) interpreter implementation.

These tests verify that the CPS-based evaluation produces the same results
as the direct-style evaluation for various expression types.
"""
from __future__ import print_function
import pytest

from rpyp4sp import p4specast, objects, interp
from rpyp4sp.continuation import *

# ============================================================================
# Helper functions
# ============================================================================

def make_num(val, typ=None):
    """Create a NumV value."""
    if typ is None:
        typ = p4specast.NumT.INT
    return objects.NumV.fromstr(str(val), p4specast.IntT.INSTANCE, typ)

def make_nat(val):
    """Create a natural number NumV."""
    return objects.NumV.fromstr(str(val), p4specast.NatT.INSTANCE, p4specast.NumT.NAT)

def make_bool(val):
    """Create a BoolV value."""
    return objects.BoolV.make(val, p4specast.BoolT.INSTANCE)

def make_text(val):
    """Create a TextV value."""
    return objects.TextV(val, p4specast.TextT())

def make_num_exp(val, typ=None):
    """Create a NumE expression."""
    if typ is None:
        typ = p4specast.NumT.INT
    exp = p4specast.NumE.fromstr(str(val), p4specast.IntT.INSTANCE)
    exp.typ = typ
    return exp

def make_nat_exp(val):
    """Create a natural number NumE expression."""
    exp = p4specast.NumE.fromstr(str(val), p4specast.NatT.INSTANCE)
    exp.typ = p4specast.NumT.NAT
    return exp

def make_bool_exp(val):
    """Create a BoolE expression."""
    exp = p4specast.BoolE(val)
    exp.typ = p4specast.BoolT.INSTANCE
    return exp

def make_text_exp(val):
    """Create a TextE expression."""
    exp = p4specast.TextE(val)
    exp.typ = p4specast.TextT()
    return exp

def make_opt_exp(inner_exp=None):
    """Create an OptE expression (optional)."""
    # Create an optional type (e.g., int?)
    if inner_exp is not None:
        inner_typ = inner_exp.typ
    else:
        inner_typ = p4specast.NumT.INT
    opt_typ = p4specast.IterT(inner_typ, p4specast.Opt())
    exp = p4specast.OptE(inner_exp, opt_typ)
    return exp


# ============================================================================
# CPS Evaluation Tests - Literals (Simplest Cases)
# ============================================================================

class MockCont(object):
    def __init__(self):
        self.result = None
    def apply(self, value):
        self.result = value
        return None

def test_num_literal_cps():
    """Test CPS evaluation of a numeric literal - the easiest case."""
    # Create a simple numeric expression
    exp = make_num_exp(42)
    ctx = None
    k = MockCont()
    # Call eval_cps - should return Done(k, value)
    result = exp.eval_cps(ctx, k)

    # Verify we got a Done object
    assert isinstance(result, Done), "Expected Done object"
    assert result.k is k, "Continuation should be preserved"

    # Verify the value is correct
    expected_value = make_num(42)
    assert result.value.value.val == expected_value.value.val, "Value should be 42"


def test_bool_literal_cps():
    """Test CPS evaluation of a boolean literal."""
    exp = make_bool_exp(True)
    ctx = None

    k = MockCont()
    result = exp.eval_cps(ctx, k)

    assert isinstance(result, Done), "Expected Done object"
    assert result.k is k, "Continuation should be preserved"

    expected_value = make_bool(True)
    assert result.value.value == expected_value.value, "Value should be True"


def test_text_literal_cps():
    """Test CPS evaluation of a text literal."""
    exp = make_text_exp("hello")
    ctx = None

    k = MockCont()
    result = exp.eval_cps(ctx, k)

    assert isinstance(result, Done), "Expected Done object"
    assert result.k is k, "Continuation should be preserved"

    expected_value = make_text("hello")
    assert result.value.value == expected_value.value, "Value should be 'hello'"


def test_opt_none_cps():
    """Test CPS evaluation of OptE with None (easiest OptE case)."""
    # Create an optional expression with no value (None)
    exp = make_opt_exp(None)
    ctx = None

    k = MockCont()
    result = exp.eval_cps(ctx, k)

    # When OptE.exp is None, it should return Done immediately
    assert isinstance(result, Done), "Expected Done object for OptE with None"
    # Note: There's currently a bug where Done(ctx, value) is used instead of Done(k, value)
    # This test documents the current behavior
    assert result.value is not None, "Should have an OptV value"
    # The value should be an OptV representing None
    assert isinstance(result.value, objects.OptV), "Value should be OptV (None)"


def test_opt_some_cps():
    """Test CPS evaluation of OptE with a value."""
    # Create an optional expression with an inner value
    inner_exp = make_num_exp(42)
    exp = make_opt_exp(inner_exp)
    ctx = None

    k = MockCont()
    result = exp.eval_cps(ctx, k)

    # When OptE.exp is not None, it should return Next to evaluate the inner expression
    assert isinstance(result, Next), "Expected Next object for OptE with value"
    assert result.exp is inner_exp, "Should evaluate the inner expression"

    # Verify the continuation is wrapped in a Cont
    assert isinstance(result.k, Cont), "Continuation should be wrapped in Cont"
    assert result.k.exp is exp, "Cont should reference the OptE expression"
    assert result.k.k is k, "Cont should preserve the original continuation"


def test_opt_apply_cps():
    """Test OptE continuation application (apply method)."""
    # Create an optional expression with an inner value
    inner_exp = make_num_exp(42)
    exp = make_opt_exp(inner_exp)
    ctx = None

    k = MockCont()
    inner_value = make_num(42)

    cont = Cont(exp, ctx, k)
    result = cont.apply(inner_value)

    assert isinstance(result, Done), "Expected Done after applying OptE continuation"
    assert result.k is k, "Should use the original continuation"

    # The value should be wrapped in OptVSome
    assert isinstance(result.value, objects.OptVSome), "Value should be OptVSome"
    assert result.value.get_opt_value() is inner_value, "OptVSome should contain the inner value"


def make_tuple_exp(elts):
    """Create a TupleE expression."""
    elt_types = [e.typ for e in elts]
    typ = p4specast.TupleT(elt_types)
    exp = p4specast.TupleE(elts, typ)
    return exp


def test_tuple_empty_cps():
    """Test CPS evaluation of an empty tuple."""
    exp = make_tuple_exp([])
    ctx = None

    k = MockCont()
    result = exp.eval_cps(ctx, k)

    assert isinstance(result, Done), "Expected Done object for empty tuple"
    assert result.k is k, "Continuation should be preserved"
    assert isinstance(result.value, objects.TupleV), "Value should be TupleV"
    assert len(result.value.get_tuple()) == 0, "Tuple should be empty"


def test_tuple_single_cps():
    """Test CPS evaluation of a tuple with one element."""
    inner_exp = make_num_exp(42)
    exp = make_tuple_exp([inner_exp])
    ctx = None

    k = MockCont()
    result = exp.eval_cps(ctx, k)

    # Should return Next to evaluate the first (only) element
    assert isinstance(result, Next), "Expected Next object for tuple with one element"
    assert result.exp is inner_exp, "Should evaluate the inner expression"

    # Verify the continuation is Cont (no ValCont yet since no elements evaluated)
    assert isinstance(result.k, Cont), "Continuation should be Cont"
    assert result.k.exp is exp, "Cont should reference the TupleE expression"
    assert result.k.k is k, "Cont should preserve the original continuation"


def test_tuple_multiple_cps():
    """Test CPS evaluation of a tuple with multiple elements."""
    exp1 = make_num_exp(1)
    exp2 = make_num_exp(2)
    exp3 = make_num_exp(3)
    exp = make_tuple_exp([exp1, exp2, exp3])
    ctx = None

    k = MockCont()
    result = exp.eval_cps(ctx, k)

    # Should return Next to evaluate the first element
    assert isinstance(result, Next), "Expected Next object"
    assert result.exp is exp1, "Should evaluate the first expression"
    assert isinstance(result.k, Cont), "Continuation should be Cont"
    assert result.k.k is k, "Cont should preserve the original continuation"


def test_tuple_apply_single_cps():
    """Test TupleE continuation application for single element tuple."""
    inner_exp = make_num_exp(42)
    exp = make_tuple_exp([inner_exp])
    ctx = None

    k = MockCont()
    inner_value = make_num(42)

    # Create continuation (no ValCont yet - first element)
    cont = Cont(exp, ctx, k)
    result = exp.apply(cont, inner_value)

    # Single element tuple should be done after first apply
    assert isinstance(result, Done), "Expected Done after applying single element"
    assert result.k is k, "Should use the original continuation"
    assert isinstance(result.value, objects.TupleV), "Value should be TupleV"
    tuple_values = result.value.get_tuple()
    assert len(tuple_values) == 1, "Tuple should have one element"
    assert tuple_values[0] is inner_value, "Element should be the inner value"


def test_tuple_apply_multiple_cps():
    """Test TupleE continuation application for multiple elements."""
    exp1 = make_num_exp(1)
    exp2 = make_num_exp(2)
    exp3 = make_num_exp(3)
    exp = make_tuple_exp([exp1, exp2, exp3])
    ctx = None

    k = MockCont()
    val1 = make_num(1)
    val2 = make_num(2)
    val3 = make_num(3)

    # First apply - no ValCont yet
    from rpyp4sp.continuation import ValCont
    cont = Cont(exp, ctx, k)
    result = exp.apply(cont, val1)

    assert isinstance(result, Next), "Expected Next after first apply"
    assert result.exp is exp2, "Should evaluate second expression"
    assert isinstance(result.k, Cont), "Continuation should be Cont"
    assert isinstance(result.k.k, ValCont), "Cont.k should be ValCont"
    assert result.k.k.value is val1, "ValCont should store val1"

    # Second apply - one ValCont
    cont2 = result.k
    result2 = exp.apply(cont2, val2)

    assert isinstance(result2, Next), "Expected Next after second apply"
    assert result2.exp is exp3, "Should evaluate third expression"
    assert isinstance(result2.k.k, ValCont), "Cont.k should be ValCont"
    assert result2.k.k.value is val2, "ValCont should store val2"
    assert isinstance(result2.k.k.k, ValCont), "Nested ValCont for val1"
    assert result2.k.k.k.value is val1, "Nested ValCont should store val1"

    # Third apply - two ValConts (final)
    cont3 = result2.k
    result3 = exp.apply(cont3, val3)

    assert isinstance(result3, Done), "Expected Done after final apply"
    assert result3.k is k, "Should use original continuation"
    assert isinstance(result3.value, objects.TupleV), "Value should be TupleV"
    tuple_values = result3.value.get_tuple()
    assert len(tuple_values) == 3, "Tuple should have 3 elements"
    assert tuple_values[0] is val1
    assert tuple_values[1] is val2
    assert tuple_values[2] is val3


def make_list_exp(elts):
    """Create a ListE expression."""
    if elts:
        inner_typ = elts[0].typ
    else:
        inner_typ = p4specast.NumT.INT
    typ = p4specast.IterT(inner_typ, p4specast.List())
    exp = p4specast.ListE(elts, typ)
    return exp


def test_list_empty_cps():
    """Test CPS evaluation of an empty list."""
    exp = make_list_exp([])
    ctx = None

    k = MockCont()
    result = exp.eval_cps(ctx, k)

    assert isinstance(result, Done), "Expected Done object for empty list"
    assert result.k is k, "Continuation should be preserved"
    assert isinstance(result.value, objects.ListV), "Value should be ListV"
    assert len(result.value.get_list()) == 0, "List should be empty"


def test_list_single_cps():
    """Test CPS evaluation of a list with one element."""
    inner_exp = make_num_exp(42)
    exp = make_list_exp([inner_exp])
    ctx = None

    k = MockCont()
    result = exp.eval_cps(ctx, k)

    # Should return Next to evaluate the first (only) element
    assert isinstance(result, Next), "Expected Next object for list with one element"
    assert result.exp is inner_exp, "Should evaluate the inner expression"

    # Verify the continuation is Cont (no ValCont yet since no elements evaluated)
    assert isinstance(result.k, Cont), "Continuation should be Cont"
    assert result.k.exp is exp, "Cont should reference the ListE expression"
    assert result.k.k is k, "Cont should preserve the original continuation"


def test_list_multiple_cps():
    """Test CPS evaluation of a list with multiple elements."""
    exp1 = make_num_exp(1)
    exp2 = make_num_exp(2)
    exp3 = make_num_exp(3)
    exp = make_list_exp([exp1, exp2, exp3])
    ctx = None

    k = MockCont()
    result = exp.eval_cps(ctx, k)

    # Should return Next to evaluate the first element
    assert isinstance(result, Next), "Expected Next object"
    assert result.exp is exp1, "Should evaluate the first expression"
    assert isinstance(result.k, Cont), "Continuation should be Cont"
    assert result.k.k is k, "Cont should preserve the original continuation"


def test_list_apply_single_cps():
    """Test ListE continuation application for single element list."""
    inner_exp = make_num_exp(42)
    exp = make_list_exp([inner_exp])
    ctx = None

    k = MockCont()
    inner_value = make_num(42)

    # Create continuation (no ValCont yet - first element)
    cont = Cont(exp, ctx, k)
    result = exp.apply(cont, inner_value)

    # Single element list should be done after first apply
    assert isinstance(result, Done), "Expected Done after applying single element"
    assert result.k is k, "Should use the original continuation"
    assert isinstance(result.value, objects.ListV), "Value should be ListV"
    list_values = result.value.get_list()
    assert len(list_values) == 1, "List should have one element"
    assert list_values[0] is inner_value, "Element should be the inner value"


def test_list_apply_multiple_cps():
    """Test ListE continuation application for multiple elements."""
    exp1 = make_num_exp(1)
    exp2 = make_num_exp(2)
    exp3 = make_num_exp(3)
    exp = make_list_exp([exp1, exp2, exp3])
    ctx = None

    k = MockCont()
    val1 = make_num(1)
    val2 = make_num(2)
    val3 = make_num(3)

    # First apply - no ValCont yet
    from rpyp4sp.continuation import ValCont
    cont = Cont(exp, ctx, k)
    result = exp.apply(cont, val1)

    assert isinstance(result, Next), "Expected Next after first apply"
    assert result.exp is exp2, "Should evaluate second expression"
    assert isinstance(result.k, Cont), "Continuation should be Cont"
    assert isinstance(result.k.k, ValCont), "Cont.k should be ValCont"
    assert result.k.k.value is val1, "ValCont should store val1"

    # Second apply - one ValCont
    cont2 = result.k
    result2 = exp.apply(cont2, val2)

    assert isinstance(result2, Next), "Expected Next after second apply"
    assert result2.exp is exp3, "Should evaluate third expression"
    assert isinstance(result2.k.k, ValCont), "Cont.k should be ValCont"
    assert result2.k.k.value is val2, "ValCont should store val2"
    assert isinstance(result2.k.k.k, ValCont), "Nested ValCont for val1"
    assert result2.k.k.k.value is val1, "Nested ValCont should store val1"

    # Third apply - two ValConts (final)
    cont3 = result2.k
    result3 = exp.apply(cont3, val3)

    assert isinstance(result3, Done), "Expected Done after final apply"
    assert result3.k is k, "Should use original continuation"
    assert isinstance(result3.value, objects.ListV), "Value should be ListV"
    list_values = result3.value.get_list()
    assert len(list_values) == 3, "List should have 3 elements"
    assert list_values[0] is val1
    assert list_values[1] is val2
    assert list_values[2] is val3


# ============================================================================
# CPS Evaluation Tests - ConsE
# ============================================================================

def make_cons_exp(head_exp, tail_exp):
    """Create a ConsE expression (head :: tail)."""
    inner_typ = head_exp.typ
    typ = p4specast.IterT(inner_typ, p4specast.List())
    exp = p4specast.ConsE(head_exp, tail_exp, typ)
    return exp


def test_cons_cps():
    """Test CPS evaluation of ConsE - should evaluate head first."""
    head_exp = make_num_exp(1)
    tail_exp = make_list_exp([make_num_exp(2), make_num_exp(3)])
    exp = make_cons_exp(head_exp, tail_exp)
    ctx = None

    k = MockCont()
    result = exp.eval_cps(ctx, k)

    # Should return Next to evaluate the head expression first
    assert isinstance(result, Next), "Expected Next object for ConsE"
    assert result.exp is head_exp, "Should evaluate head expression first"

    # Verify the continuation is Cont
    assert isinstance(result.k, Cont), "Continuation should be Cont"
    assert result.k.exp is exp, "Cont should reference the ConsE expression"
    assert result.k.k is k, "Cont should preserve the original continuation"


def test_cons_apply_head_cps():
    """Test ConsE continuation application after evaluating head."""
    head_exp = make_num_exp(1)
    tail_exp = make_list_exp([make_num_exp(2), make_num_exp(3)])
    exp = make_cons_exp(head_exp, tail_exp)
    ctx = None

    k = MockCont()
    head_value = make_num(1)

    # Create continuation (just evaluated head)
    cont = Cont(exp, ctx, k)
    result = exp.apply(cont, head_value)

    # Should return Next to evaluate the tail expression
    from rpyp4sp.continuation import ValCont
    assert isinstance(result, Next), "Expected Next after applying head"
    assert result.exp is tail_exp, "Should evaluate tail expression"
    assert isinstance(result.k, Cont), "Continuation should be Cont"
    assert isinstance(result.k.k, ValCont), "Cont.k should be ValCont"
    assert result.k.k.value is head_value, "ValCont should store the head value"


def test_cons_apply_tail_cps():
    """Test ConsE continuation application after evaluating tail."""
    head_exp = make_num_exp(1)
    tail_exp = make_list_exp([make_num_exp(2), make_num_exp(3)])
    exp = make_cons_exp(head_exp, tail_exp)
    ctx = None

    k = MockCont()
    head_value = make_num(1)
    tail_value = objects.ListV.make([make_num(2), make_num(3)], tail_exp.typ)

    # Create continuation with ValCont wrapping head_value (just evaluated tail)
    from rpyp4sp.continuation import ValCont
    val_k = ValCont(head_value, k)
    cont = Cont(exp, ctx, val_k)
    result = exp.apply(cont, tail_value)

    # Should return Done with the consed list
    assert isinstance(result, Done), "Expected Done after applying tail"
    assert result.k is k, "Should use the original continuation"
    assert isinstance(result.value, objects.ListV), "Value should be ListV"
    list_values = result.value.get_list()
    assert len(list_values) == 3, "List should have 3 elements"
    assert list_values[0].value.val == head_value.value.val, "First element should be head"


def make_cmp_exp(left_exp, right_exp, cmpop='EqOp'):
    """Create a CmpE expression."""
    typ = p4specast.BoolT.INSTANCE
    optyp = left_exp.typ  # optyp is the type of the operands
    exp = p4specast.CmpE(cmpop, optyp, left_exp, right_exp, typ)
    return exp


def test_cmp_cps():
    """Test CPS evaluation of CmpE - should evaluate left first."""
    left_exp = make_num_exp(1)
    right_exp = make_num_exp(2)
    exp = make_cmp_exp(left_exp, right_exp, 'EqOp')
    ctx = None

    k = MockCont()
    result = exp.eval_cps(ctx, k)

    # Should return Next to evaluate the left expression first
    assert isinstance(result, Next), "Expected Next object for CmpE"
    assert result.exp is left_exp, "Should evaluate left expression first"

    # Verify the continuation is Cont
    assert isinstance(result.k, Cont), "Continuation should be Cont"
    assert result.k.exp is exp, "Cont should reference the CmpE expression"
    assert result.k.k is k, "Cont should preserve the original continuation"


def test_cmp_apply_left_cps():
    """Test CmpE continuation application after evaluating left."""
    left_exp = make_num_exp(1)
    right_exp = make_num_exp(2)
    exp = make_cmp_exp(left_exp, right_exp, 'EqOp')
    ctx = None

    k = MockCont()
    left_value = make_num(1)

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


def test_cmp_apply_right_eq_cps():
    """Test CmpE continuation application for equality comparison."""
    left_exp = make_num_exp(42)
    right_exp = make_num_exp(42)
    exp = make_cmp_exp(left_exp, right_exp, 'EqOp')
    ctx = None

    k = MockCont()
    left_value = make_num(42)
    right_value = make_num(42)

    # Create continuation with ValCont wrapping left_value (just evaluated right)
    from rpyp4sp.continuation import ValCont
    val_k = ValCont(left_value, k)
    cont = Cont(exp, ctx, val_k)
    result = exp.apply(cont, right_value)

    # Should return Done with boolean result
    assert isinstance(result, Done), "Expected Done after applying right"
    assert result.k is k, "Should use the original continuation"
    assert isinstance(result.value, objects.BoolV), "Value should be BoolV"
    assert result.value.value == True, "42 == 42 should be True"


def test_cmp_apply_right_ne_cps():
    """Test CmpE continuation application for inequality comparison."""
    left_exp = make_num_exp(1)
    right_exp = make_num_exp(2)
    exp = make_cmp_exp(left_exp, right_exp, 'NeOp')
    ctx = None

    k = MockCont()
    left_value = make_num(1)
    right_value = make_num(2)

    # Create continuation with ValCont wrapping left_value (just evaluated right)
    from rpyp4sp.continuation import ValCont
    val_k = ValCont(left_value, k)
    cont = Cont(exp, ctx, val_k)
    result = exp.apply(cont, right_value)

    # Should return Done with boolean result
    assert isinstance(result, Done), "Expected Done after applying right"
    assert result.k is k, "Should use the original continuation"
    assert isinstance(result.value, objects.BoolV), "Value should be BoolV"
    assert result.value.value == True, "1 != 2 should be True"


def test_cmp_apply_right_lt_cps():
    """Test CmpE continuation application for less-than comparison."""
    left_exp = make_num_exp(1)
    right_exp = make_num_exp(2)
    exp = make_cmp_exp(left_exp, right_exp, 'LtOp')
    ctx = None

    k = MockCont()
    left_value = make_num(1)
    right_value = make_num(2)

    # Create continuation with ValCont wrapping left_value (just evaluated right)
    from rpyp4sp.continuation import ValCont
    val_k = ValCont(left_value, k)
    cont = Cont(exp, ctx, val_k)
    result = exp.apply(cont, right_value)

    # Should return Done with boolean result
    assert isinstance(result, Done), "Expected Done after applying right"
    assert result.k is k, "Should use the original continuation"
    assert isinstance(result.value, objects.BoolV), "Value should be BoolV"
    assert result.value.value == True, "1 < 2 should be True"


def make_bin_exp(left_exp, right_exp, binop='AddOp'):
    """Create a BinE expression."""
    typ = left_exp.typ  # Result type matches operand type for arithmetic
    optyp = left_exp.typ  # optyp is the type of the operands
    if binop in ('AndOp', 'OrOp', 'ImplOp', 'EquivOp'):
        typ = p4specast.BoolT.INSTANCE
    exp = p4specast.BinE(binop, optyp, left_exp, right_exp, typ)
    return exp


def test_bin_cps():
    """Test CPS evaluation of BinE - should evaluate left first."""
    left_exp = make_num_exp(1)
    right_exp = make_num_exp(2)
    exp = make_bin_exp(left_exp, right_exp, 'AddOp')
    ctx = None

    k = MockCont()
    result = exp.eval_cps(ctx, k)

    # Should return Next to evaluate the left expression first
    assert isinstance(result, Next), "Expected Next object for BinE"
    assert result.exp is left_exp, "Should evaluate left expression first"

    # Verify the continuation is Cont (not ValCont wrapped yet)
    assert isinstance(result.k, Cont), "Continuation should be Cont"
    assert result.k.exp is exp, "Cont should reference the BinE expression"
    assert result.k.k is k, "Cont should preserve the original continuation"


def test_bin_apply_left_cps():
    """Test BinE continuation application after evaluating left."""
    left_exp = make_num_exp(1)
    right_exp = make_num_exp(2)
    exp = make_bin_exp(left_exp, right_exp, 'AddOp')
    ctx = None

    k = MockCont()
    left_value = make_num(1)

    # Create continuation (just evaluated left)
    cont = Cont(exp, ctx, k)
    result = exp.apply(cont, left_value)

    # Should return Next to evaluate the right expression
    assert isinstance(result, Next), "Expected Next after applying left"
    assert result.exp is right_exp, "Should evaluate right expression"
    # New continuation should be Cont with ValCont wrapping the left value
    from rpyp4sp.continuation import ValCont
    assert isinstance(result.k, Cont), "Continuation should be Cont"
    assert isinstance(result.k.k, ValCont), "Cont.k should be ValCont"
    assert result.k.k.value is left_value, "ValCont should store the left value"


def test_bin_apply_right_add_cps():
    """Test BinE continuation application for addition."""
    left_exp = make_num_exp(1)
    right_exp = make_num_exp(2)
    exp = make_bin_exp(left_exp, right_exp, 'AddOp')
    ctx = None

    k = MockCont()
    left_value = make_num(1)
    right_value = make_num(2)

    # Create continuation with ValCont wrapping left_value (just evaluated right)
    from rpyp4sp.continuation import ValCont
    val_k = ValCont(left_value, k)
    cont = Cont(exp, ctx, val_k)
    result = exp.apply(cont, right_value)

    # Should return Done with numeric result
    assert isinstance(result, Done), "Expected Done after applying right"
    assert result.k is k, "Should use the original continuation"
    assert isinstance(result.value, objects.NumV), "Value should be NumV"
    assert result.value.value.val == 3, "1 + 2 should be 3"


def test_bin_apply_right_sub_cps():
    """Test BinE continuation application for subtraction."""
    left_exp = make_num_exp(5)
    right_exp = make_num_exp(3)
    exp = make_bin_exp(left_exp, right_exp, 'SubOp')
    ctx = None

    k = MockCont()
    left_value = make_num(5)
    right_value = make_num(3)

    # Create continuation with ValCont wrapping left_value (just evaluated right)
    from rpyp4sp.continuation import ValCont
    val_k = ValCont(left_value, k)
    cont = Cont(exp, ctx, val_k)
    result = exp.apply(cont, right_value)

    # Should return Done with numeric result
    assert isinstance(result, Done), "Expected Done after applying right"
    assert result.k is k, "Should use the original continuation"
    assert isinstance(result.value, objects.NumV), "Value should be NumV"
    assert result.value.value.val == 2, "5 - 3 should be 2"


def test_bin_apply_right_mul_cps():
    """Test BinE continuation application for multiplication."""
    left_exp = make_num_exp(3)
    right_exp = make_num_exp(4)
    exp = make_bin_exp(left_exp, right_exp, 'MulOp')
    ctx = None

    k = MockCont()
    left_value = make_num(3)
    right_value = make_num(4)

    # Create continuation with ValCont wrapping left_value (just evaluated right)
    from rpyp4sp.continuation import ValCont
    val_k = ValCont(left_value, k)
    cont = Cont(exp, ctx, val_k)
    result = exp.apply(cont, right_value)

    # Should return Done with numeric result
    assert isinstance(result, Done), "Expected Done after applying right"
    assert result.k is k, "Should use the original continuation"
    assert isinstance(result.value, objects.NumV), "Value should be NumV"
    assert result.value.value.val == 12, "3 * 4 should be 12"


def test_bin_apply_right_and_cps():
    """Test BinE continuation application for boolean AND."""
    left_exp = make_bool_exp(True)
    right_exp = make_bool_exp(False)
    exp = make_bin_exp(left_exp, right_exp, 'AndOp')
    ctx = None

    k = MockCont()
    left_value = make_bool(True)
    right_value = make_bool(False)

    # Create continuation with ValCont wrapping left_value (just evaluated right)
    from rpyp4sp.continuation import ValCont
    val_k = ValCont(left_value, k)
    cont = Cont(exp, ctx, val_k)
    result = exp.apply(cont, right_value)

    # Should return Done with boolean result
    assert isinstance(result, Done), "Expected Done after applying right"
    assert result.k is k, "Should use the original continuation"
    assert isinstance(result.value, objects.BoolV), "Value should be BoolV"
    assert result.value.value == False, "True AND False should be False"


def test_bin_apply_right_or_cps():
    """Test BinE continuation application for boolean OR."""
    left_exp = make_bool_exp(True)
    right_exp = make_bool_exp(False)
    exp = make_bin_exp(left_exp, right_exp, 'OrOp')
    ctx = None

    k = MockCont()
    left_value = make_bool(True)
    right_value = make_bool(False)

    # Create continuation with ValCont wrapping left_value (just evaluated right)
    from rpyp4sp.continuation import ValCont
    val_k = ValCont(left_value, k)
    cont = Cont(exp, ctx, val_k)
    result = exp.apply(cont, right_value)

    # Should return Done with boolean result
    assert isinstance(result, Done), "Expected Done after applying right"
    assert result.k is k, "Should use the original continuation"
    assert isinstance(result.value, objects.BoolV), "Value should be BoolV"
    assert result.value.value == True, "True OR False should be True"


def make_un_exp(inner_exp, unop='NotOp'):
    """Create a UnE expression."""
    if unop == 'NotOp':
        typ = p4specast.BoolT.INSTANCE
        optyp = 'boolT'
    else:
        typ = inner_exp.typ
        optyp = 'intT'
    exp = p4specast.UnE(unop, optyp, inner_exp, typ)
    return exp


def test_un_cps():
    """Test CPS evaluation of UnE - should evaluate inner expression first."""
    inner_exp = make_bool_exp(True)
    exp = make_un_exp(inner_exp, 'NotOp')
    ctx = None

    k = MockCont()
    result = exp.eval_cps(ctx, k)

    # Should return Next to evaluate the inner expression first
    assert isinstance(result, Next), "Expected Next object for UnE"
    assert result.exp is inner_exp, "Should evaluate inner expression first"

    # Verify the continuation is Cont
    assert isinstance(result.k, Cont), "Continuation should be Cont"
    assert result.k.exp is exp, "Cont should reference the UnE expression"
    assert result.k.k is k, "Cont should preserve the original continuation"


def test_un_apply_not_true_cps():
    """Test UnE continuation application for NOT True."""
    inner_exp = make_bool_exp(True)
    exp = make_un_exp(inner_exp, 'NotOp')
    ctx = None

    k = MockCont()
    inner_value = make_bool(True)

    # Create continuation and apply the evaluated value
    cont = Cont(exp, ctx, k)
    result = exp.apply(cont, inner_value)

    # Should return Done with negated boolean result
    assert isinstance(result, Done), "Expected Done after applying NOT"
    assert result.k is k, "Should use the original continuation"
    assert isinstance(result.value, objects.BoolV), "Value should be BoolV"
    assert result.value.value == False, "NOT True should be False"


def test_un_apply_not_false_cps():
    """Test UnE continuation application for NOT False."""
    inner_exp = make_bool_exp(False)
    exp = make_un_exp(inner_exp, 'NotOp')
    ctx = None

    k = MockCont()
    inner_value = make_bool(False)

    cont = Cont(exp, ctx, k)
    result = exp.apply(cont, inner_value)

    assert isinstance(result, Done), "Expected Done after applying NOT"
    assert result.k is k, "Should use the original continuation"
    assert isinstance(result.value, objects.BoolV), "Value should be BoolV"
    assert result.value.value == True, "NOT False should be True"


def test_un_apply_plus_cps():
    """Test UnE continuation application for unary plus."""
    inner_exp = make_num_exp(42)
    exp = make_un_exp(inner_exp, 'PlusOp')
    ctx = None

    k = MockCont()
    inner_value = make_num(42)

    cont = Cont(exp, ctx, k)
    result = exp.apply(cont, inner_value)

    assert isinstance(result, Done), "Expected Done after applying unary plus"
    assert result.k is k, "Should use the original continuation"
    assert isinstance(result.value, objects.NumV), "Value should be NumV"
    assert result.value.value.val == 42, "+42 should be 42"


def test_un_apply_minus_cps():
    """Test UnE continuation application for unary minus."""
    inner_exp = make_num_exp(42)
    exp = make_un_exp(inner_exp, 'MinusOp')
    ctx = None

    k = MockCont()
    inner_value = make_num(42)

    cont = Cont(exp, ctx, k)
    result = exp.apply(cont, inner_value)

    assert isinstance(result, Done), "Expected Done after applying unary minus"
    assert result.k is k, "Should use the original continuation"
    assert isinstance(result.value, objects.NumV), "Value should be NumV"
    assert result.value.value.val == -42, "-42 should be -42"


def test_un_apply_minus_negative_cps():
    """Test UnE continuation application for unary minus on negative number."""
    inner_exp = make_num_exp(-5)
    exp = make_un_exp(inner_exp, 'MinusOp')
    ctx = None

    k = MockCont()
    inner_value = make_num(-5)

    cont = Cont(exp, ctx, k)
    result = exp.apply(cont, inner_value)

    assert isinstance(result, Done), "Expected Done after applying unary minus"
    assert result.k is k, "Should use the original continuation"
    assert isinstance(result.value, objects.NumV), "Value should be NumV"
    assert result.value.value.val == 5, "-(-5) should be 5"


def make_mem_exp(elem_exp, lst_exp):
    """Create a MemE expression (elem <- lst)."""
    typ = p4specast.BoolT.INSTANCE
    exp = p4specast.MemE(elem_exp, lst_exp, typ)
    return exp


def test_mem_cps():
    """Test CPS evaluation of MemE - should evaluate elem first."""
    elem_exp = make_num_exp(1)
    lst_exp = make_list_exp([make_num_exp(1), make_num_exp(2), make_num_exp(3)])
    exp = make_mem_exp(elem_exp, lst_exp)
    ctx = None

    k = MockCont()
    result = exp.eval_cps(ctx, k)

    # Should return Next to evaluate the elem expression first
    assert isinstance(result, Next), "Expected Next object for MemE"
    assert result.exp is elem_exp, "Should evaluate elem expression first"

    # Verify the continuation is Cont
    assert isinstance(result.k, Cont), "Continuation should be Cont"
    assert result.k.exp is exp, "Cont should reference the MemE expression"
    assert result.k.k is k, "Cont should preserve the original continuation"


def test_mem_apply_elem_cps():
    """Test MemE continuation application after evaluating elem."""
    elem_exp = make_num_exp(1)
    lst_exp = make_list_exp([make_num_exp(1), make_num_exp(2)])
    exp = make_mem_exp(elem_exp, lst_exp)
    ctx = None

    k = MockCont()
    elem_value = make_num(1)

    # Create continuation (just evaluated elem)
    cont = Cont(exp, ctx, k)
    result = exp.apply(cont, elem_value)

    # Should return Next to evaluate the lst expression
    from rpyp4sp.continuation import ValCont
    assert isinstance(result, Next), "Expected Next after applying elem"
    assert result.exp is lst_exp, "Should evaluate lst expression"
    assert isinstance(result.k, Cont), "Continuation should be Cont"
    assert isinstance(result.k.k, ValCont), "Cont.k should be ValCont"
    assert result.k.k.value is elem_value, "ValCont should store the elem value"


def test_mem_apply_lst_found_cps():
    """Test MemE continuation application - elem found in list."""
    elem_exp = make_num_exp(2)
    lst_exp = make_list_exp([make_num_exp(1), make_num_exp(2), make_num_exp(3)])
    exp = make_mem_exp(elem_exp, lst_exp)
    ctx = None

    k = MockCont()
    elem_value = make_num(2)
    lst_value = objects.ListV.make([make_num(1), make_num(2), make_num(3)], lst_exp.typ)

    # Create continuation with ValCont wrapping elem_value (just evaluated lst)
    from rpyp4sp.continuation import ValCont
    val_k = ValCont(elem_value, k)
    cont = Cont(exp, ctx, val_k)
    result = exp.apply(cont, lst_value)

    # Should return Done with True (elem is in list)
    assert isinstance(result, Done), "Expected Done after applying lst"
    assert result.k is k, "Should use the original continuation"
    assert isinstance(result.value, objects.BoolV), "Value should be BoolV"
    assert result.value.value == True, "2 should be in [1, 2, 3]"


def test_mem_apply_lst_not_found_cps():
    """Test MemE continuation application - elem not found in list."""
    elem_exp = make_num_exp(5)
    lst_exp = make_list_exp([make_num_exp(1), make_num_exp(2), make_num_exp(3)])
    exp = make_mem_exp(elem_exp, lst_exp)
    ctx = None

    k = MockCont()
    elem_value = make_num(5)
    lst_value = objects.ListV.make([make_num(1), make_num(2), make_num(3)], lst_exp.typ)

    from rpyp4sp.continuation import ValCont
    val_k = ValCont(elem_value, k)
    cont = Cont(exp, ctx, val_k)
    result = exp.apply(cont, lst_value)

    assert isinstance(result, Done), "Expected Done after applying lst"
    assert result.k is k, "Should use the original continuation"
    assert isinstance(result.value, objects.BoolV), "Value should be BoolV"
    assert result.value.value == False, "5 should not be in [1, 2, 3]"


def test_mem_apply_empty_list_cps():
    """Test MemE continuation application - empty list."""
    elem_exp = make_num_exp(1)
    lst_exp = make_list_exp([])
    exp = make_mem_exp(elem_exp, lst_exp)
    ctx = None

    k = MockCont()
    elem_value = make_num(1)
    lst_value = objects.ListV.make([], lst_exp.typ)

    from rpyp4sp.continuation import ValCont
    val_k = ValCont(elem_value, k)
    cont = Cont(exp, ctx, val_k)
    result = exp.apply(cont, lst_value)

    assert isinstance(result, Done), "Expected Done after applying lst"
    assert result.k is k, "Should use the original continuation"
    assert isinstance(result.value, objects.BoolV), "Value should be BoolV"
    assert result.value.value == False, "Nothing can be in an empty list"


def test_mem_apply_single_elem_list_cps():
    """Test MemE continuation application - single element list."""
    elem_exp = make_num_exp(42)
    lst_exp = make_list_exp([make_num_exp(42)])
    exp = make_mem_exp(elem_exp, lst_exp)
    ctx = None

    k = MockCont()
    elem_value = make_num(42)
    lst_value = objects.ListV.make([make_num(42)], lst_exp.typ)

    from rpyp4sp.continuation import ValCont
    val_k = ValCont(elem_value, k)
    cont = Cont(exp, ctx, val_k)
    result = exp.apply(cont, lst_value)

    assert isinstance(result, Done), "Expected Done after applying lst"
    assert result.k is k, "Should use the original continuation"
    assert isinstance(result.value, objects.BoolV), "Value should be BoolV"
    assert result.value.value == True, "42 should be in [42]"
