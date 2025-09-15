import sys
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

    def abs(self):
        if self.val == MININT:
            return BigInteger(rbigint.fromint(self.val).abs())
        return SmallInteger(abs(self.val))

    def add(self, other):
        if isinstance(other, SmallInteger):
            return SmallInteger.add_i_i(self.val, other.val)
        else:
            assert isinstance(other, BigInteger)
            return BigInteger(other.rval.int_add(self.val))

    def int_add(self, other):
        return SmallInteger.add_i_i(self.val, other)

    def int_sub(self, other):
        return SmallInteger.sub_i_i(self.val, other)

    def int_mul(self, other):
        return SmallInteger.mul_i_i(self.val, other)

    def sub(self, other):
        if isinstance(other, SmallInteger):
            return SmallInteger.sub_i_i(self.val, other.val)
        return BigInteger((other.tobigint().int_sub(self.val)).neg()) # XXX can do better

    def mul(self, other):
        if isinstance(other, SmallInteger):
            try:
                return SmallInteger(ovfcheck(self.val * other.val))
            except OverflowError:
                return BigInteger(self.tobigint().int_mul(other.val))
        else:
            assert isinstance(other, BigInteger)
            return other.mul(self)

    def rshift(self, i):
        assert i >= 0
        return SmallInteger(self.val >> i)

    def lshift(self, i):
        assert i >= 0
        return self.lshift_i_i(self.val, i)

    def mod(self, other):
        if isinstance(other, SmallInteger):
            return SmallInteger.mod_i_i(self.val, other.val)
        else:
            assert isinstance(other, BigInteger)
            return BigInteger(self.tobigint().mod(other.rval))

    def and_(self, other):
        if isinstance(other, SmallInteger):
            return SmallInteger(self.val & other.val)
        else:
            assert isinstance(other, BigInteger)
            return BigInteger(self.tobigint().and_(other.rval))

    def or_(self, other):
        if isinstance(other, SmallInteger):
            return SmallInteger(self.val | other.val)
        else:
            assert isinstance(other, BigInteger)
            return BigInteger(self.tobigint().or_(other.rval))

    def xor(self, other):
        if isinstance(other, SmallInteger):
            return SmallInteger(self.val ^ other.val)
        else:
            assert isinstance(other, BigInteger)
            return BigInteger(self.tobigint().xor(other.rval))

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

    def abs(self):
        return BigInteger(self.rval.abs())

    def add(self, other):
        if isinstance(other, SmallInteger):
            return BigInteger(self.rval.int_add(other.val))
        assert isinstance(other, BigInteger)
        return BigInteger(self.rval.add(other.rval))

    def int_add(self, other):
        return BigInteger(self.rval.int_add(other))

    def int_sub(self, other):
        return BigInteger(self.rval.int_sub(other))

    def int_mul(self, other):
        return BigInteger(self.rval.int_mul(other))

    def sub(self, other):
        if isinstance(other, SmallInteger):
            return BigInteger(self.rval.int_sub(other.val))
        assert isinstance(other, BigInteger)
        return BigInteger(self.rval.sub(other.rval))

    def mul(self, other):
        if isinstance(other, SmallInteger):
            val = other.val
            if not val:
                return SmallInteger(0)
            if val == 1:
                return self
            if val & (val - 1) == 0:
                # power of two, replace by lshift
                shift = self._shift_amount(val)
                return self.lshift(shift)
            return BigInteger(self.rval.int_mul(other.val))
        assert isinstance(other, BigInteger)
        return BigInteger(self.rval.mul(other.rval))

    @staticmethod
    @jit.elidable
    def _shift_amount(poweroftwo):
        assert poweroftwo & (poweroftwo - 1) == 0
        shift = 0
        while 1 << shift != poweroftwo:
            shift += 1
        return shift

    def rshift(self, i):
        assert i >= 0
        # XXX should we check whether it fits in a SmallInteger now?
        return BigInteger(self.rval.rshift(i))

    def lshift(self, i):
        return BigInteger(self.rval.lshift(i))

    def mod(self, other):
        if isinstance(other, SmallInteger):
            if other.val == 0:
                raise ZeroDivisionError("integer division or modulo by zero")
            return SmallInteger(self.rval.int_mod_int_result(other.val))
        assert isinstance(other, BigInteger)
        if other.eq(SmallInteger(0)):
            raise ZeroDivisionError("integer division or modulo by zero")
        return BigInteger(self.rval.mod(other.rval))

    def and_(self, other):
        if isinstance(other, SmallInteger):
            return BigInteger(self.rval.int_and_(other.val))
        else:
            assert isinstance(other, BigInteger)
            return BigInteger(self.rval.and_(other.rval))

    def or_(self, other):
        if isinstance(other, SmallInteger):
            return BigInteger(self.rval.int_or_(other.val))
        else:
            assert isinstance(other, BigInteger)
            return BigInteger(self.rval.or_(other.rval))

    def xor(self, other):
        if isinstance(other, SmallInteger):
            return BigInteger(self.rval.int_xor(other.val))
        else:
            assert isinstance(other, BigInteger)
            return BigInteger(self.rval.xor(other.rval))

    def invert(self):
        return BigInteger(self.rval.invert())
