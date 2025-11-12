import sys
from rpyp4sp.error import P4BuiltinError
from rpython.rlib.rbigint import rbigint, _divrem as bigint_divrem, ONERBIGINT, \
        _divrem1 as bigint_divrem1, intsign, int_in_valid_range
from rpython.rlib.rarithmetic import r_uint, intmask, string_to_int, ovfcheck, \
        r_ulonglong
from rpython.rlib.objectmodel import always_inline, specialize, \
        we_are_translated
from rpython.rlib.rstring import (
    ParseStringError, ParseStringOverflowError)
from rpython.rlib import jit

MININT = -sys.maxint-1


class Integer(object):
    _attrs_ = []

    @staticmethod
    def fromint(val):
        return SmallInteger(val)

    @staticmethod
    def frombigint(rval):
        return BigInteger(rval)

    @staticmethod
    def fromstr(val):
        value = 0
        try:
            return SmallInteger(string_to_int(val, 10))
        except ParseStringOverflowError as e:
            e.parser.rewind()
            return BigInteger(rbigint._from_numberstring_parser(e.parser))

    def tolong(self): # only for tests:
        return self.tobigint().tolong()

    def compare(self, other):
        if self.eq(other):
            return 0
        elif self.lt(other):
            return -1
        else:
            return 1

    def neg(self):
        return Integer.fromint(0).sub(self)

    def mod(self, other):
        raise NotImplementedError("abstract method")

    def div(self, other):
        raise NotImplementedError("abstract method")

    def and_(self, other):
        raise NotImplementedError("abstract method")

    def or_(self, other):
        raise NotImplementedError("abstract method")

    def xor(self, other):
        raise NotImplementedError("abstract method")

    def invert(self):
        raise NotImplementedError("abstract method")


class SmallInteger(Integer):
    _immutable_fields_ = ['val']

    def __init__(self, val):
        if not we_are_translated():
            assert MININT <= val <= sys.maxint
        self.val = val

    def __repr__(self):
        return "<SmallInteger %s>" % (self.val, )

    def str(self):
        return str(self.val)

    def hex(self):
        return hex(self.val)

    def toint(self):
        return self.val

    def tobigint(self):
        return rbigint.fromint(self.val)

    def eq(self, other):
        if isinstance(other, SmallInteger):
            return self.val == other.val
        return other.eq(self)

    def lt(self, other):
        if isinstance(other, SmallInteger):
            return self.val < other.val
        assert isinstance(other, BigInteger)
        return other.rval.int_gt(self.val)

    def le(self, other):
        if isinstance(other, SmallInteger):
            return self.val <= other.val
        assert isinstance(other, BigInteger)
        return other.rval.int_ge(self.val)

    def gt(self, other):
        if isinstance(other, SmallInteger):
            return self.val > other.val
        assert isinstance(other, BigInteger)
        return other.rval.int_lt(self.val)

    def ge(self, other):
        if isinstance(other, SmallInteger):
            return self.val >= other.val
        assert isinstance(other, BigInteger)
        return other.rval.int_le(self.val)

    def int_eq(self, iother):
        return self.val == iother

    def int_lt(self, iother):
        return self.val < iother

    def int_le(self, iother):
        return self.val <= iother.val

    def int_gt(self, iother):
        return self.val > iother

    def int_ge(self, iother):
        return self.val >= iother

    def abs(self):
        if self.val == MININT:
            return BigInteger(rbigint.fromint(self.val).abs())
        return SmallInteger(abs(self.val))

    def add(self, other):
        return other.int_add(self.val)

    def int_add(self, other):
        return SmallInteger.add_i_i(self.val, other)

    def bigint_add(self, big_rval):
        return BigInteger(big_rval.int_add(self.val))

    def int_sub(self, other):
        return SmallInteger.sub_i_i(self.val, other)

    def int_mul(self, other):
        return SmallInteger.mul_i_i(self.val, other)

    def sub(self, other):
        return other.int_rsub(self.val)

    def int_rsub(self, val):
        return SmallInteger.sub_i_i(val, self.val)

    def bigint_rsub(self, big_rval):
        return BigInteger(big_rval.int_sub(self.val))

    def mul(self, other):
        return other.int_mul(self.val)

    def bigint_mul(self, big_rval):
        val = self.val
        if not val:
            return SmallInteger(0)
        if val == 1:
            return BigInteger(big_rval)
        if val & (val - 1) == 0:
            # power of two, replace by lshift
            shift = BigInteger._shift_amount(val)
            return BigInteger(big_rval.lshift(shift))
        return BigInteger(big_rval.int_mul(val))

    def rshift(self, i):
        if i < 0:
            raise P4BuiltinError("negative shift amount")
        return SmallInteger(self.val >> i)

    def lshift(self, i):
        if i < 0:
            raise P4BuiltinError("negative shift amount")
        return self.lshift_i_i(self.val, i)

    def mod(self, other):
        return other.int_rmod(self.val)

    def int_rmod(self, val):
        return SmallInteger.mod_i_i(val, self.val)

    def bigint_rmod(self, big_rval):
        if self.val == 0:
            raise ZeroDivisionError("integer division or modulo by zero")
        return SmallInteger(big_rval.int_mod_int_result(self.val))

    def div(self, other):
        return other.int_rdiv(self.val)

    def int_rdiv(self, val):
        if self.val == 0:
            raise ZeroDivisionError("integer division by zero")
        if val == MININT and self.val == -1:
            return BigInteger(rbigint.fromint(val).abs())
        return SmallInteger.div_i_i(val, self.val)

    def bigint_rdiv(self, big_rval):
        if self.val == 0:
            raise ZeroDivisionError("integer division by zero")
        return BigInteger(big_rval.int_div(self.val))

    def and_(self, other):
        return other.int_and(self.val)

    def int_and(self, other):
        return SmallInteger(self.val & other)

    def bigint_and(self, big_rval):
        return BigInteger(big_rval.int_and_(self.val))

    def or_(self, other):
        return other.int_or(self.val)

    def int_or(self, other):
        return SmallInteger(self.val | other)

    def bigint_or(self, big_rval):
        return BigInteger(big_rval.int_or_(self.val))

    def xor(self, other):
        return other.int_xor(self.val)

    def int_xor(self, other):
        return SmallInteger(self.val ^ other)

    def bigint_xor(self, big_rval):
        return BigInteger(big_rval.int_xor(self.val))

    def invert(self):
        return SmallInteger(~self.val)

    @staticmethod
    def lshift_i_i(a, i):
        if not a:
            return SmallInteger(0)
        if i < 64:
            try:
                return SmallInteger(ovfcheck(a << i))
            except OverflowError:
                pass
        return BigInteger(rbigint.fromint(a).lshift(i))

    @staticmethod
    def add_i_i(a, b):
        try:
            return SmallInteger(ovfcheck(a + b))
        except OverflowError:
            return BigInteger(rbigint.fromint(a).int_add(b))

    @staticmethod
    def sub_i_i(a, b):
        try:
            return SmallInteger(ovfcheck(a - b))
        except OverflowError:
            return BigInteger(rbigint.fromint(b).int_sub(a).neg())

    @staticmethod
    def mul_i_i(a, b):
        try:
            return SmallInteger(ovfcheck(a * b))
        except OverflowError:
            return BigInteger(rbigint.fromint(a).int_mul(b))

    @staticmethod
    def mod_i_i(a, b):
        if b == 0:
            raise ZeroDivisionError("integer division or modulo by zero")
        result = a % b
        return SmallInteger(result)

    @staticmethod
    def div_i_i(a, b):
        if b == 0:
            raise ZeroDivisionError("integer division by zero")
        try:
            result = ovfcheck(a // b)
        except OverflowError:
            assert 0, 'unreachable'
        return SmallInteger(result)

    def pack(self):
        return (self.val, None)


class BigInteger(Integer):
    _immutable_fields_ = ['rval']

    def __init__(self, rval):
        self.rval = rval

    def __repr__(self):
        return "<BigInteger %s>" % (self.rval.str(), )

    def str(self):
        return self.rval.str()

    def hex(self):
        return self.rval.hex()

    def toint(self):
        return self.rval.toint()

    def tobigint(self):
        return self.rval

    def eq(self, other):
        if isinstance(other, SmallInteger):
            return self.rval.int_eq(other.val)
        assert isinstance(other, BigInteger)
        return self.rval.eq(other.rval)

    def int_eq(self, other):
        return self.rval.int_eq(other)

    def lt(self, other):
        if isinstance(other, SmallInteger):
            return self.rval.int_lt(other.val)
        assert isinstance(other, BigInteger)
        return self.rval.lt(other.rval)

    def le(self, other):
        if isinstance(other, SmallInteger):
            return self.rval.int_le(other.val)
        assert isinstance(other, BigInteger)
        return self.rval.le(other.rval)

    def gt(self, other):
        if isinstance(other, SmallInteger):
            return self.rval.int_gt(other.val)
        assert isinstance(other, BigInteger)
        return self.rval.gt(other.rval)

    def ge(self, other):
        if isinstance(other, SmallInteger):
            return self.rval.int_ge(other.val)
        assert isinstance(other, BigInteger)
        return self.rval.ge(other.rval)

    def int_eq(self, iother):
        return self.rval.int_eq(iother)

    def int_lt(self, iother):
        return self.rval.int_lt(iother)

    def int_le(self, iother):
        return self.rval.int_le(iother)

    def int_gt(self, iother):
        return self.rval.int_gt(iother)

    def int_ge(self, iother):
        return self.rval.int_ge(iother)

    def abs(self):
        return BigInteger(self.rval.abs())

    def add(self, other):
        return other.bigint_add(self.rval)

    def int_add(self, other):
        return BigInteger(self.rval.int_add(other))

    def bigint_add(self, big_rval):
        return BigInteger(big_rval.add(self.rval))

    def int_sub(self, other):
        return BigInteger(self.rval.int_sub(other))

    def int_mul(self, other):
        return BigInteger(self.rval.int_mul(other))

    def sub(self, other):
        return other.bigint_rsub(self.rval)

    def int_rsub(self, val):
        return BigInteger(rbigint.fromint(val).sub(self.rval))

    def bigint_rsub(self, big_rval):
        return BigInteger(big_rval.sub(self.rval))

    def mul(self, other):
        return other.bigint_mul(self.rval)

    def bigint_mul(self, big_rval):
        return BigInteger(big_rval.mul(self.rval))

    @staticmethod
    @jit.elidable
    def _shift_amount(poweroftwo):
        assert poweroftwo & (poweroftwo - 1) == 0
        shift = 0
        while 1 << shift != poweroftwo:
            shift += 1
        return shift

    def rshift(self, i):
        if i < 0:
            raise P4BuiltinError("negative shift amount")
        # XXX should we check whether it fits in a SmallInteger now?
        return BigInteger(self.rval.rshift(i))

    def lshift(self, i):
        if i < 0:
            raise P4BuiltinError("negative shift amount")
        return BigInteger(self.rval.lshift(i))

    def mod(self, other):
        return other.bigint_rmod(self.rval)

    def int_rmod(self, val):
        if self.rval.int_eq(0):
            raise ZeroDivisionError("integer division or modulo by zero")
        return BigInteger(rbigint.fromint(val).mod(self.rval))

    def bigint_rmod(self, big_rval):
        if self.rval.int_eq(0):
            raise ZeroDivisionError("integer division or modulo by zero")
        return BigInteger(big_rval.mod(self.rval))

    def div(self, other):
        return other.bigint_rdiv(self.rval)

    def int_rdiv(self, val):
        if self.rval.int_eq(0):
            raise ZeroDivisionError("integer division by zero")
        return BigInteger(rbigint.fromint(val).div(self.rval))

    def bigint_rdiv(self, big_rval):
        if self.rval.int_eq(0):
            raise ZeroDivisionError("integer division by zero")
        return BigInteger(big_rval.div(self.rval))

    def and_(self, other):
        return other.bigint_and(self.rval)

    def int_and(self, other):
        return BigInteger(self.rval.int_and_(other))

    def bigint_and(self, big_rval):
        return BigInteger(big_rval.and_(self.rval))

    def or_(self, other):
        return other.bigint_or(self.rval)

    def int_or(self, other):
        return BigInteger(self.rval.int_or_(other))

    def bigint_or(self, big_rval):
        return BigInteger(big_rval.or_(self.rval))

    def xor(self, other):
        return other.bigint_xor(self.rval)

    def int_xor(self, other):
        return BigInteger(self.rval.int_xor(other))

    def bigint_xor(self, big_rval):
        return BigInteger(big_rval.xor(self.rval))

    def invert(self):
        return BigInteger(self.rval.invert())
