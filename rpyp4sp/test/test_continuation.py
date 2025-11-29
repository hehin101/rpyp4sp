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


# ============================================================================
# CPS Evaluation Tests - Literals (Simplest Cases)
# ============================================================================

class MockCont(object):
    def __init__(self):
        self.result = None
    def resume(self, value):
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
