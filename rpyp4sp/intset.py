from rpython.rlib.rbigint import rbigint
from rpython.rlib import jit
from rpython.rlib.rarithmetic import r_ulonglong


MAXELEMENT = 10000


class ImmutableIntSet(object):
    _immutable_fields_ = ['_bits']

    def __init__(self, bits=None):
        if bits is None:
            self._bits = rbigint.fromint(0)
        else:
            self._bits = bits

    def add(self, n):
        assert 0 <= n <= MAXELEMENT
        if n in self:
            return self
        mask = rbigint.fromint(1).lshift(n)
        new_bits = self._bits.or_(mask)
        return ImmutableIntSet(new_bits)

    def remove(self, n):
        assert 0 <= n <= MAXELEMENT
        mask = rbigint.fromint(1).lshift(n)
        inverted_mask = mask.invert()
        new_bits = self._bits.and_(inverted_mask)
        return ImmutableIntSet(new_bits)

    @jit.elidable
    def __contains__(self, n):
        assert 0 <= n <= MAXELEMENT
        # Use abs_rshift_and_mask to extract the bit at position n
        # This shifts right by n and masks with 1 to get just that bit
        bit = self._bits.abs_rshift_and_mask(r_ulonglong(n), 1)
        return bit != 0

    @jit.elidable
    def union(self, other):
        assert isinstance(other, ImmutableIntSet)
        new_bits = self._bits.or_(other._bits)
        return ImmutableIntSet(new_bits)

    @jit.elidable
    def intersection(self, other):
        assert isinstance(other, ImmutableIntSet)
        new_bits = self._bits.and_(other._bits)
        return ImmutableIntSet(new_bits)

    @jit.elidable
    def difference(self, other):
        assert isinstance(other, ImmutableIntSet)
        inverted_other = other._bits.invert()
        new_bits = self._bits.and_(inverted_other)
        return ImmutableIntSet(new_bits)

    @jit.elidable
    def is_empty(self):
        return self._bits.int_eq(0)

    @jit.elidable
    def __eq__(self, other):
        if not isinstance(other, ImmutableIntSet):
            return False
        return self._bits.eq(other._bits)

    @jit.elidable
    def __ne__(self, other):
        return not self.__eq__(other)

    @jit.elidable
    def __len__(self):
        return self._bits.bit_count()

    @jit.elidable
    def to_list(self):
        result = []
        bits = self._bits
        i = 0
        while not bits.int_eq(0) and i <= MAXELEMENT:
            if not bits.int_and_(1).int_eq(0):
                result.append(i)
            bits = bits.rshift(1)
            i += 1
        return result

    @staticmethod
    @jit.elidable
    def from_list(items):
        result = ImmutableIntSet()
        for item in items:
            result = result.add(item)
        return result
