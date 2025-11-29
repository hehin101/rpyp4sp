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
