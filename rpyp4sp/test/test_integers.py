import pytest
import sys

from rpyp4sp.integers import Integer, SmallInteger, BigInteger, MININT
from hypothesis import given, strategies, assume, example, settings

from rpython.rlib.rbigint import rbigint


def make_int(data):
    if data.draw(strategies.booleans()):
        # big ints
        return BigInteger(rbigint.fromlong(data.draw(strategies.integers())))
    else:
        # small ints
        return SmallInteger(data.draw(ints))

ints = strategies.integers(-sys.maxint-1, sys.maxint)
wrapped_ints = strategies.builds(
        make_int,
        strategies.data())

@given(wrapped_ints, wrapped_ints)
def test_op_int_hypothesis(a, b):
    v1 = a.tobigint().tolong()
    v2 = b.tobigint().tolong()
    assert a.add(b).tolong() == v1 + v2
    assert a.sub(b).tolong() == v1 - v2
    assert a.mul(b).tolong() == v1 * v2

    assert a.eq(b) == (v1 == v2)
    assert a.lt(b) == (v1 < v2)
    assert a.gt(b) == (v1 > v2)
    assert a.le(b) == (v1 <= v2)
    assert a.ge(b) == (v1 >= v2)

@given(wrapped_ints, ints)
def test_int_add_sub_hypothesis(a, b):
    v1 = a.tobigint().tolong()
    v2 = b
    assert a.int_add(b).tolong() == v1 + v2
    assert a.int_sub(b).tolong() == v1 - v2

