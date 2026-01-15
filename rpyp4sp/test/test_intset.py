import pytest
from hypothesis import given, strategies as st
from rpyp4sp.intset import ImmutableIntSet, MAXELEMENT


def test_empty_set():
    s = ImmutableIntSet()
    assert s.is_empty()
    assert 0 not in s
    assert 1000 not in s
    assert MAXELEMENT not in s


def test_add_single_element():
    s = ImmutableIntSet()
    s2 = s.add(42)

    assert s.is_empty()
    assert 42 not in s

    assert not s2.is_empty()
    assert 42 in s2
    assert 41 not in s2
    assert 43 not in s2


def test_add_existing_element():
    s = ImmutableIntSet().add(42)
    s2 = s.add(42)  # adding same element again

    assert s2 is s  # should return same object
    assert 42 in s2


def test_add_multiple_elements():
    s = ImmutableIntSet()
    s2 = s.add(0).add(100).add(MAXELEMENT)

    assert 0 in s2
    assert 100 in s2
    assert MAXELEMENT in s2
    assert 1 not in s2
    assert 99 not in s2
    assert MAXELEMENT - 1 not in s2


def test_remove():
    s = ImmutableIntSet().add(10).add(20).add(30)
    s2 = s.remove(20)

    assert 10 in s
    assert 20 in s
    assert 30 in s

    assert 10 in s2
    assert 20 not in s2
    assert 30 in s2


def test_union():
    s1 = ImmutableIntSet().add(1).add(2).add(3)
    s2 = ImmutableIntSet().add(3).add(4).add(5)
    s3 = s1.union(s2)

    assert 1 in s3
    assert 2 in s3
    assert 3 in s3
    assert 4 in s3
    assert 5 in s3
    assert 0 not in s3
    assert 6 not in s3


def test_union_with_empty():
    s = ImmutableIntSet().add(1).add(2).add(3)
    empty = ImmutableIntSet()

    # Union with empty should return same object
    result1 = s.union(empty)
    assert result1 is s

    # Empty union with non-empty should return same object
    result2 = empty.union(s)
    assert result2 is s


def test_intersection():
    s1 = ImmutableIntSet().add(1).add(2).add(3).add(4)
    s2 = ImmutableIntSet().add(3).add(4).add(5).add(6)
    s3 = s1.intersection(s2)

    assert 3 in s3
    assert 4 in s3
    assert 1 not in s3
    assert 2 not in s3
    assert 5 not in s3
    assert 6 not in s3


def test_intersection_with_empty():
    s = ImmutableIntSet().add(1).add(2).add(3)
    empty = ImmutableIntSet()

    # Intersection with empty should return the EMPTY singleton
    result1 = s.intersection(empty)
    assert result1 is ImmutableIntSet.EMPTY

    # Empty intersection with non-empty should return the EMPTY singleton
    result2 = empty.intersection(s)
    assert result2 is ImmutableIntSet.EMPTY


def test_difference():
    s1 = ImmutableIntSet().add(1).add(2).add(3).add(4)
    s2 = ImmutableIntSet().add(3).add(4).add(5).add(6)
    s3 = s1.difference(s2)

    assert 1 in s3
    assert 2 in s3
    assert 3 not in s3
    assert 4 not in s3
    assert 5 not in s3
    assert 6 not in s3


def test_difference_with_empty():
    s = ImmutableIntSet().add(1).add(2).add(3)
    empty = ImmutableIntSet()

    # Difference with empty should return same object
    result1 = s.difference(empty)
    assert result1 is s

    # Empty difference with non-empty should return the EMPTY singleton
    result2 = empty.difference(s)
    assert result2 is ImmutableIntSet.EMPTY


def test_equality():
    s1 = ImmutableIntSet().add(1).add(2).add(3)
    s2 = ImmutableIntSet().add(3).add(2).add(1)
    s3 = ImmutableIntSet().add(1).add(2)

    assert s1 == s2
    assert s1 != s3
    assert s2 != s3


def test_to_list():
    s = ImmutableIntSet().add(5).add(1).add(10)
    lst = s.to_list()

    assert sorted(lst) == [1, 5, 10]


def test_from_list():
    s = ImmutableIntSet.from_list([1, 5, 10, 5])  # duplicate should be ignored

    assert 1 in s
    assert 5 in s
    assert 10 in s
    assert 2 not in s
    assert len(s.to_list()) == 3
    assert len(s) == 3


def test_len():
    empty = ImmutableIntSet()
    assert len(empty) == 0

    s1 = empty.add(42)
    assert len(s1) == 1

    s2 = s1.add(100).add(200)
    assert len(s2) == 3

    s3 = s2.remove(100)
    assert len(s3) == 2


def test_boundary_values():
    s = ImmutableIntSet().add(0).add(MAXELEMENT)

    assert 0 in s
    assert MAXELEMENT in s
    assert 1 not in s
    assert MAXELEMENT - 1 not in s


def test_large_set():
    s = ImmutableIntSet()
    for i in range(0, MAXELEMENT + 1, 100):  # 0, 100, 200, ..., MAXELEMENT
        s = s.add(i)

    for i in range(0, MAXELEMENT + 1, 100):
        assert i in s

    assert 50 not in s
    assert 150 not in s


def test_empty_intersection():
    s1 = ImmutableIntSet().add(1).add(2)
    s2 = ImmutableIntSet().add(3).add(4)
    s3 = s1.intersection(s2)

    assert s3.is_empty()


def test_empty_difference():
    s1 = ImmutableIntSet().add(1).add(2)
    s2 = ImmutableIntSet().add(1).add(2).add(3)
    s3 = s1.difference(s2)

    assert s3.is_empty()


def test_assert_bounds():
    s = ImmutableIntSet()

    with pytest.raises(AssertionError):
        s.add(-1)

    with pytest.raises(AssertionError):
        s.add(MAXELEMENT + 1)

    with pytest.raises(AssertionError):
        -1 in s

    with pytest.raises(AssertionError):
        MAXELEMENT + 1 in s


# Property-based tests using hypothesis

@given(st.integers(0, MAXELEMENT))
def test_add_contains_property(n):
    s = ImmutableIntSet()
    s2 = s.add(n)
    assert n in s2
    assert n not in s


@given(st.lists(st.integers(0, MAXELEMENT)))
def test_from_list_to_list_roundtrip(items):
    s = ImmutableIntSet.from_list(items)
    result = s.to_list()
    expected = sorted(set(items))
    assert result == expected


@given(st.sets(st.integers(0, MAXELEMENT)), st.sets(st.integers(0, MAXELEMENT)))
def test_union_properties(set1, set2):
    s1 = ImmutableIntSet.from_list(list(set1))
    s2 = ImmutableIntSet.from_list(list(set2))
    s3 = s1.union(s2)

    # Union is commutative
    s4 = s2.union(s1)
    assert s3 == s4

    # All elements from both sets are in union
    for item in set1:
        assert item in s3
    for item in set2:
        assert item in s3

    # Union result matches set union
    expected = sorted(set1 | set2)
    assert s3.to_list() == expected


@given(st.sets(st.integers(0, MAXELEMENT)), st.sets(st.integers(0, MAXELEMENT)))
def test_intersection_properties(set1, set2):
    s1 = ImmutableIntSet.from_list(list(set1))
    s2 = ImmutableIntSet.from_list(list(set2))
    s3 = s1.intersection(s2)

    # Intersection is commutative
    s4 = s2.intersection(s1)
    assert s3 == s4

    # Intersection result matches set intersection
    expected = sorted(set1 & set2)
    assert s3.to_list() == expected


@given(st.sets(st.integers(0, MAXELEMENT)), st.sets(st.integers(0, MAXELEMENT)))
def test_difference_properties(set1, set2):
    s1 = ImmutableIntSet.from_list(list(set1))
    s2 = ImmutableIntSet.from_list(list(set2))
    s3 = s1.difference(s2)

    # Difference result matches set difference
    expected = sorted(set1 - set2)
    assert s3.to_list() == expected

    # Elements in difference are in original but not in other
    for item in s3.to_list():
        assert item in s1
        assert item not in s2


@given(st.sets(st.integers(0, MAXELEMENT)))
def test_immutability_property(items):
    s1 = ImmutableIntSet.from_list(list(items))
    original_list = s1.to_list()

    # Operations return new sets, don't modify original
    if items:
        item = list(items)[0]
        s2 = s1.remove(item)
        assert s1.to_list() == original_list  # unchanged
        assert item not in s2

    s3 = s1.add(1500)  # add something not likely to be in items
    assert s1.to_list() == original_list  # unchanged


@given(st.sets(st.integers(0, MAXELEMENT)))
def test_equality_property(items):
    s1 = ImmutableIntSet.from_list(list(items))
    s2 = ImmutableIntSet.from_list(list(items))

    # Same elements should be equal
    assert s1 == s2

    # Self equality
    assert s1 == s1


@given(st.sets(st.integers(0, MAXELEMENT)))
def test_set_algebra_properties(items):
    s = ImmutableIntSet.from_list(list(items))
    empty = ImmutableIntSet()

    # Union with empty
    assert s.union(empty) == s
    assert empty.union(s) == s

    # Intersection with empty
    assert s.intersection(empty).is_empty()
    assert empty.intersection(s).is_empty()

    # Difference with empty
    assert s.difference(empty) == s
    assert empty.difference(s).is_empty()

    # Self operations
    assert s.union(s) == s
    assert s.intersection(s) == s
    assert s.difference(s).is_empty()