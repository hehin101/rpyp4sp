from rpython.rlib import jit

from rpyp4sp.intset import ImmutableIntSet

class Coverage(object):
    def __init__(self, pidset_hit, pidset_miss):
        self.pidset_hit = pidset_hit
        self.pidset_miss = pidset_miss

    def cover(self, is_hit, phantom, value):
        # don't record misses so far, ignore values
        return self._cover(is_hit, phantom.pid)

    @jit.elidable
    def _cover(self, is_hit, pid):
        if is_hit:
            if pid in self.pidset_hit:
                return self
            return Coverage(self.pidset_hit.add(pid), self.pidset_miss)
        else:
            if pid in self.pidset_miss:
                return self
            return Coverage(self.pidset_hit, self.pidset_miss.add(pid))
        return self

    @jit.elidable
    def union(self, other):
        pidset_hit = self.pidset_hit.union(other.pidset_hit)
        pidset_miss = self.pidset_miss.union(other.pidset_miss)
        if pidset_hit is self.pidset_hit and pidset_miss is self.pidset_miss:
            return self
        return Coverage(pidset_hit, pidset_miss)

    def __repr__(self):
        return "Coverage(%r, %r)" % (self.pidset_hit, self.pidset_miss)

    def tostr(self):
        return hex(self.pidset_hit._bits.hash())[2:] + hex(self.pidset_miss._bits.hash())[2:]


Coverage.EMPTY = Coverage(ImmutableIntSet.EMPTY, ImmutableIntSet.EMPTY)
