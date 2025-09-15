import pytest
import sys

from rpyp4sp.integers import Integer, SmallInteger, BigInteger, MININT
try:
    from hypothesis import given, strategies, assume, example, settings
except ImportError:
    pytest.skip("missing hypothesis")

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

def test_mod_basic():
    assert SmallInteger(7).mod(SmallInteger(3)).tolong() == 1
    assert SmallInteger(8).mod(SmallInteger(3)).tolong() == 2
    assert SmallInteger(9).mod(SmallInteger(3)).tolong() == 0

    assert SmallInteger(-7).mod(SmallInteger(3)).tolong() == 2
    assert SmallInteger(7).mod(SmallInteger(-3)).tolong() == -2
    assert SmallInteger(-7).mod(SmallInteger(-3)).tolong() == -1

    big_num = BigInteger(rbigint.fromlong(123456789012345))
    small_num = SmallInteger(1000)
    assert big_num.mod(small_num).tolong() == 123456789012345 % 1000

    with pytest.raises(ZeroDivisionError):
        SmallInteger(5).mod(SmallInteger(0))
    with pytest.raises(ZeroDivisionError):
        BigInteger(rbigint.fromlong(5)).mod(SmallInteger(0))

@given(wrapped_ints, wrapped_ints)
@example(SmallInteger(7), SmallInteger(-3))
@example(SmallInteger(-7), SmallInteger(3))
@example(BigInteger(rbigint.fromlong(123456789012345)), SmallInteger(1000))
@example(SmallInteger(MININT), SmallInteger(-1))
@example(SmallInteger(-sys.maxint-1), SmallInteger(-1))
@example(SmallInteger(sys.maxint), SmallInteger(-1))
@example(SmallInteger(MININT), SmallInteger(1))
@example(SmallInteger(MININT), SmallInteger(sys.maxint))
def test_mod_hypothesis(a, b):
    v1 = a.tobigint().tolong()
    v2 = b.tobigint().tolong()
    # Skip division by zero
    assume(v2 != 0)
    result = a.mod(b).tolong()
    expected = v1 % v2
    assert result == expected

