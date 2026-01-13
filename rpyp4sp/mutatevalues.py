import random
import sys
from rpyp4sp.objects import BoolV, NumV, TextV, TupleV, StructV, CaseV, ListV, OptV
from rpyp4sp import p4specast, integers


def mutate_BoolV(value, rng):
    """Mutate a BoolV by flipping its boolean value."""
    assert isinstance(value, BoolV)
    # Simple mutation: flip the boolean value
    return BoolV.make(not value.value, value.get_typ())


def mutate_NumV(value, rng):
    """Mutate a NumV using various strategies."""
    assert isinstance(value, NumV)

    # Choose mutation strategy
    strategy = rng.randint(0, 3)

    if strategy == 0:
        # Add/subtract small random values
        delta = rng.randint(-10, 10)
        new_val = value.value.add(integers.Integer.fromint(delta))
    elif strategy == 1:
        # Boundary values
        boundary_choice = rng.randint(0, 4)
        if boundary_choice == 0:
            new_val = integers.Integer.fromint(0)
        elif boundary_choice == 1:
            new_val = integers.Integer.fromint(1)
        elif boundary_choice == 2:
            new_val = integers.Integer.fromint(-1)
        elif boundary_choice == 3:
            # Max small value
            new_val = integers.Integer.fromint(2**16 - 1)
        else:
            # Min small value
            new_val = integers.Integer.fromint(-(2**16))
    elif strategy == 2:
        # Random bit flip
        bit_pos = rng.randint(0, 31)  # Flip a bit in lower 32 bits
        original_int = value.value.toint()
        flipped = original_int ^ (1 << bit_pos)
        new_val = integers.Integer.fromint(flipped)
    else:
        # Generate completely new value
        if isinstance(value.get_what(), p4specast.NatT):
            # Natural numbers: 0 to reasonable upper bound
            new_int = rng.randint(0, 2**20)
        else:
            # Integers: reasonable range around zero
            new_int = rng.randint(-(2**19), 2**19)
        new_val = integers.Integer.fromint(new_int)

    # For Nat type, ensure non-negative
    if isinstance(value.get_what(), p4specast.NatT) and new_val.toint() < 0:
        new_val = new_val.abs()

    return NumV.make(new_val, value.get_what(), value.get_typ())


def mutate_TextV(value, rng):
    """Mutate a TextV using character-level mutations."""
    assert isinstance(value, TextV)

    text = value.value
    if not text:
        # Empty string - add a random character
        new_text = chr(rng.randint(32, 126))  # Printable ASCII
    else:
        # Choose mutation strategy
        strategy = rng.randint(0, 4)

        if strategy == 0:
            # Insert random character at random position
            pos = rng.randint(0, len(text))
            char = chr(rng.randint(32, 126))
            assert pos >= 0
            new_text = text[:pos] + char + text[pos:]
        elif strategy == 1:
            # Delete random character
            if len(text) == 1:
                new_text = ""
            else:
                pos = rng.randint(0, len(text) - 1)
                assert pos >= 0
                new_text = text[:pos] + text[pos + 1:]
        elif strategy == 2:
            # Replace random character
            pos = rng.randint(0, len(text) - 1)
            char = chr(rng.randint(32, 126))
            assert pos >= 0
            new_text = text[:pos] + char + text[pos + 1:]
        elif strategy == 3:
            # Insert special character
            pos = rng.randint(0, len(text))
            special_chars = ['"', "'", "\\", "\n", "\t", "\r", "\0"]
            char = special_chars[rng.randint(0, len(special_chars) - 1)]
            assert pos >= 0
            new_text = text[:pos] + char + text[pos:]
        else:
            # Flip case of random character (if alphabetic)
            pos = rng.randint(0, len(text) - 1)
            char = text[pos]
            if char.islower():
                new_char = char.upper()
            elif char.isupper():
                new_char = char.lower()
            else:
                # Not alphabetic, replace with random char
                new_char = chr(rng.randint(32, 126))
            assert pos >= 0
            new_text = text[:pos] + new_char + text[pos + 1:]

    return TextV(new_text, value.get_typ())


def mutate_value(value, rng):
    """Dispatch to the appropriate mutation function based on value type."""
    if isinstance(value, BoolV):
        return mutate_BoolV(value, rng)
    elif isinstance(value, NumV):
        return mutate_NumV(value, rng)
    # elif isinstance(value, TextV):
    #     return mutate_TextV(value, rng)
    elif isinstance(value, TupleV):
        return mutate_TupleV(value, rng)
    elif isinstance(value, StructV):
        return mutate_StructV(value, rng)
    elif isinstance(value, CaseV):
        return mutate_CaseV(value, rng)
    elif isinstance(value, ListV):
        return mutate_ListV(value, rng)
    elif isinstance(value, OptV):
        return mutate_OptV(value, rng)
    else:
        # For unknown types, return unchanged
        return value


def _mutate_list_element(elements, rng):
    """Helper function to mutate one element in a list."""
    if not elements:
        return elements

    # Pick random element to mutate
    index = rng.randint(0, len(elements) - 1)

    # Mutate the selected element
    mutated_element = mutate_value(elements[index], rng)

    # Build new list with mutated element
    new_elements = []
    for i in range(len(elements)):
        if i == index:
            new_elements.append(mutated_element)
        else:
            new_elements.append(elements[i])

    return new_elements[:]


def mutate_TupleV(value, rng):
    """Mutate a TupleV by mutating one of its elements."""
    assert isinstance(value, TupleV)

    elements = value._get_full_list()
    mutated_elements = _mutate_list_element(elements, rng)
    if mutated_elements is elements:
        return value  # Empty tuple unchanged

    return TupleV.make(mutated_elements, value.get_typ())


def mutate_StructV(value, rng):
    """Mutate a StructV by mutating one of its field values."""
    assert isinstance(value, StructV)

    field_values = value._get_full_list()
    mutated_field_values = _mutate_list_element(field_values, rng)
    if mutated_field_values is field_values:
        return value  # Empty struct unchanged

    return StructV.make(mutated_field_values, value.map, value.get_typ())


def mutate_CaseV(value, rng):
    """Mutate a CaseV by mutating one of its values."""
    assert isinstance(value, CaseV)

    values = value._get_full_list()
    mutated_values = _mutate_list_element(values, rng)
    if mutated_values is values:
        return value  # Empty case unchanged

    return CaseV.make(mutated_values, value.mixop, value.get_typ())


def mutate_ListV(value, rng):
    """Mutate a ListV using various strategies that can change length."""
    assert isinstance(value, ListV)

    elements = value._get_full_list()

    if not elements:
        # Empty list - nothing to mutate or duplicate
        return value

    # Choose mutation strategy
    strategy = rng.randint(0, 4)

    if strategy == 0:
        # Mutate existing element (preserve length)
        mutated_elements = _mutate_list_element(elements, rng)
        return ListV.make(mutated_elements, value.get_typ())
    elif strategy == 1:
        # Insert duplicate element at random position
        source_index = rng.randint(0, len(elements) - 1)
        insert_pos = rng.randint(0, len(elements))
        duplicate = elements[source_index]
        assert insert_pos >= 0
        new_elements = elements[:insert_pos] + [duplicate] + elements[insert_pos:]
        return ListV.make(new_elements, value.get_typ())
    elif strategy == 2:
        # Remove random element
        if len(elements) == 1:
            # Single element - make empty
            return ListV.make([], value.get_typ())
        else:
            remove_index = rng.randint(0, len(elements) - 1)
            assert remove_index >= 0
            new_elements = elements[:remove_index] + elements[remove_index + 1:]
            return ListV.make(new_elements, value.get_typ())
    elif strategy == 3:
        # Swap two elements (if list has at least 2 elements)
        if len(elements) < 2:
            # Not enough elements to swap, just mutate instead
            mutated_elements = _mutate_list_element(elements, rng)
            return ListV.make(mutated_elements, value.get_typ())
        else:
            idx1 = rng.randint(0, len(elements) - 1)
            idx2 = rng.randint(0, len(elements) - 1)
            # Ensure different indices
            if idx1 == idx2:
                idx2 = (idx1 + 1) % len(elements)

            new_elements = elements[:]
            new_elements[idx1], new_elements[idx2] = new_elements[idx2], new_elements[idx1]
            return ListV.make(new_elements, value.get_typ())
    else:
        # Clear list (make empty)
        return ListV.make([], value.get_typ())


def mutate_OptV(value, rng):
    """Mutate an OptV by making it None or mutating its contained value."""
    assert isinstance(value, OptV)
    inner_value = value.get_opt_value()

    if inner_value is None:
        # Already None - nothing to mutate
        return value

    # Choose strategy: mutate contained value or make None
    strategy = rng.randint(0, 1)

    if strategy == 0:
        # Mutate the contained value
        mutated_inner = mutate_value(inner_value, rng)
    else:
        # Make it None
        mutated_inner = None
    return value.get_typ().make_opt_value(mutated_inner)


# ____________________________________________________________
# Fresh value generation from types

def generate_BoolV(typ, rng, storetyp=None):
    """Generate a fresh BoolV from a BoolT type."""
    assert isinstance(typ, p4specast.BoolT)
    if storetyp is None: storetyp = typ
    value = rng.randint(0, 1) == 1
    return BoolV.make(value, storetyp)


def generate_NumV(typ, rng, storetyp=None):
    """Generate a fresh NumV from a NumT type."""
    assert isinstance(typ, p4specast.NumT)
    if storetyp is None: storetyp = typ

    if isinstance(typ.typ, p4specast.NatT):
        # Natural numbers: generate 0 to reasonable upper bound
        value_int = rng.randint(0, 1000)
    else:
        # Integers: generate reasonable range around zero
        value_int = rng.randint(-500, 500)

    value = integers.Integer.fromint(value_int)
    return NumV.make(value, typ.typ, storetyp)


def generate_TextV(typ, rng, storetyp=None):
    """Generate a fresh TextV from a TextT type."""
    assert isinstance(typ, p4specast.TextT)
    if storetyp is None: storetyp = typ

    # Choose string generation strategy
    strategy = 2 # rng.randint(0, 3)

    if strategy == 0:
        # Empty string
        text = ""
    elif strategy == 1:
        # Short random string
        length = rng.randint(1, 10)
        chars = []
        for _ in range(length):
            chars.append(chr(rng.randint(32, 126)))  # Printable ASCII
        text = "".join(chars)
    elif strategy == 2:
        # Common test strings
        test_strings = ["hello", "world", "test", "abc", "123", "foo", "bar"]
        text = test_strings[rng.randint(0, len(test_strings) - 1)]
    else:
        # String with special characters
        special_chars = ['\"', "'", "\\", "\n", "\t", "\r"]
        char = special_chars[rng.randint(0, len(special_chars) - 1)]
        if rng.randint(0, 1) == 0:
            text = char
        else:
            # Mix with normal text
            prefix = chr(rng.randint(97, 122))  # lowercase letter
            text = prefix + char

    return TextV(text, storetyp)


def generate_OptV(typ, rng, ctx=None, maxdepth=10, storetyp=None):
    """Generate a fresh OptV from an OptT type (IterT with Opt.INSTANCE)."""
    assert isinstance(typ, p4specast.IterT) and typ.iter is p4specast.Opt.INSTANCE
    if storetyp is None: storetyp = typ

    # Choose whether to generate None or a value
    if maxdepth <= 0 or rng.randint(0, 1) == 0:
        # Generate None
        inner_value = None
        return typ.make_opt_value(None)
    else:
        # Generate a value of the inner type
        inner_value = generate_value(typ.typ, rng, ctx, maxdepth)
        assert isinstance(storetyp, p4specast.IterT) and storetyp.iter is p4specast.Opt.INSTANCE
        return storetyp.make_opt_value(inner_value)

def generate_CaseV(typ, rng, ctx, maxdepth=10, storetyp=None):
    if storetyp is None: storetyp = typ
    case = typ.cases[rng.randint(0, len(typ.cases) - 1)]
    values = []
    for typ in case.typs:
        values.append(generate_value(typ, rng, ctx, maxdepth))
    return CaseV.make(values, case.mixop, storetyp)

def generate_ListV(typ, rng, ctx=None, maxdepth=10, storetyp=None):
    if storetyp is None: storetyp = typ
    if maxdepth <= 0:
        content = []
    else:
        length = rng.randint(0, 10)
        content = [generate_value(typ.typ, rng, ctx, maxdepth) for _ in range(length)]
    return ListV.make(content, storetyp)

def generate_TupleV(typ, rng, ctx=None, maxdepth=10, storetyp=None):
    """Generate a fresh TupleV from a TupleT type."""
    if storetyp is None: storetyp = typ
    assert isinstance(typ, p4specast.TupleT)

    # Generate values for each element type
    content = [None] * len(typ.elts)
    for i, element_typ in enumerate(typ.elts):
        content[i] = generate_value(element_typ, rng, ctx, maxdepth)

    return TupleV.make(content, storetyp)

def generate_value(typ, rng, ctx=None, maxdepth=-sys.maxint, storetyp=None):
    """Dispatch to the appropriate generation function based on type."""
    if maxdepth == -sys.maxint:
        maxdepth = rng.randint(1, 7)
    if isinstance(typ, p4specast.BoolT):
        return generate_BoolV(typ, rng, storetyp)
    elif isinstance(typ, p4specast.NumT):
        return generate_NumV(typ, rng, storetyp)
    elif isinstance(typ, p4specast.TextT):
        return generate_TextV(typ, rng, storetyp)
    elif isinstance(typ, p4specast.IterT) and isinstance(typ.iter, p4specast.Opt):
        return generate_OptV(typ, rng, ctx, maxdepth - 1, storetyp)
    elif isinstance(typ, p4specast.IterT) and isinstance(typ.iter, p4specast.List):
        return generate_ListV(typ, rng, ctx, maxdepth - 1, storetyp)
    elif isinstance(typ, p4specast.VariantT):
        return generate_CaseV(typ, rng, ctx, maxdepth - 1, storetyp)
    elif isinstance(typ, p4specast.PlainT):
        return generate_value(typ.typ, rng, ctx, maxdepth, storetyp)
    elif isinstance(typ, p4specast.TupleT):
        return generate_TupleV(typ, rng, ctx, maxdepth - 1, storetyp)
    elif isinstance(typ, p4specast.VarT):
        _, plaintyp = ctx.find_typdef_local(typ.id)
        res = generate_value(plaintyp, rng, ctx, maxdepth, typ)
        return res
    else:
        # For unknown types, raise an error for now
        raise NotImplementedError("Generation not implemented for type: %s" % typ.__class__.__name__)


# ____________________________________________________________
# Deep mutation helpers

class Queue(object):
    """Two-list queue implementation for RPython compatibility."""

    def __init__(self):
        self.front_list = []  # Items ready to be dequeued (reversed order)
        self.back_list = []   # Items being enqueued (normal order)

    def enqueue(self, item):
        self.back_list.append(item)

    def dequeue(self):
        if self.is_empty():
            raise IndexError("dequeue from empty queue")

        # If front_list is empty, move all items from back_list (reversed)
        if not self.front_list:
            while self.back_list:
                self.front_list.append(self.back_list.pop())

        return self.front_list.pop()

    def is_empty(self):
        return len(self.front_list) == 0 and len(self.back_list) == 0


def find_subvalues(value):
    """
    Find all subvalues in breadth-first order.

    Returns a list of tuples (contained_value, path_to_that_value) where
    path is a list of indices showing how to reach the subvalue from the root.

    The root value itself is included with an empty path [].
    """
    result = []
    queue = Queue()
    queue.enqueue((value, []))  # (value, path)

    while not queue.is_empty():
        current_value, current_path = queue.dequeue()  # BFS: take from front
        result.append((current_value, current_path))

        # Add children to queue for BFS traversal
        if isinstance(current_value, TupleV):
            elements = current_value._get_full_list()
            for i, element in enumerate(elements):
                queue.enqueue((element, current_path + [i]))
        elif isinstance(current_value, StructV):
            field_values = current_value._get_full_list()
            for i, field_value in enumerate(field_values):
                queue.enqueue((field_value, current_path + [i]))
        elif isinstance(current_value, CaseV):
            values = current_value._get_full_list()
            for i, case_value in enumerate(values):
                queue.enqueue((case_value, current_path + [i]))
        elif isinstance(current_value, ListV):
            elements = current_value._get_full_list()
            for i, element in enumerate(elements):
                queue.enqueue((element, current_path + [i]))
        elif isinstance(current_value, OptV):
            if current_value.get_opt_value() is not None:
                queue.enqueue((current_value.get_opt_value(), current_path + [0]))

    return result


def _mutate_element_at_path(elements, index, remaining_path, rng, ctx=None):
    """
    Helper function to mutate an element at a specific index with a path.

    Returns a new list with the element at index mutated according to remaining_path.
    """
    if index < 0 or index >= len(elements):
        raise IndexError("Path index %d out of bounds for container of size %d" % (index, len(elements)))

    new_elements = []
    for i, element in enumerate(elements):
        if i == index:
            new_elements.append(mutate_subvalue_with_path(element, remaining_path, rng, ctx))
        else:
            new_elements.append(element)
    return new_elements[:]


def mutate_subvalue_with_path(value, path, rng, ctx=None):
    """
    Mutate a subvalue at the given path and return a new top-level value.

    Args:
        value: The top-level value to mutate
        path: List of indices leading to the subvalue to mutate
        rng: Random number generator
        ctx: Context for type resolution (optional)

    Returns:
        A new value with the subvalue at the given path mutated
    """
    if not path:
        # Empty path means mutate the value itself
        if rng.randint(0, 3) != 3:
            return mutate_value(value, rng)
        res = generate_value(value.get_typ(), rng, ctx)
        return res


    # Get the first index and recurse for the rest of the path
    index = path[0]
    remaining_path = path[1:]

    if isinstance(value, TupleV):
        elements = value._get_full_list()
        new_elements = _mutate_element_at_path(elements, index, remaining_path, rng, ctx)
        return TupleV.make(new_elements, value.typ)

    elif isinstance(value, StructV):
        field_values = value._get_full_list()
        new_field_values = _mutate_element_at_path(field_values, index, remaining_path, rng, ctx)
        return StructV.make(new_field_values, value.map, value.typ)

    elif isinstance(value, CaseV):
        values = value._get_full_list()
        new_values = _mutate_element_at_path(values, index, remaining_path, rng, ctx)
        return CaseV.make(new_values, value.mixop, value.typ)

    elif isinstance(value, ListV):
        elements = value._get_full_list()
        new_elements = _mutate_element_at_path(elements, index, remaining_path, rng, ctx)
        return ListV.make(new_elements, value.typ)

    elif isinstance(value, OptV):
        if index != 0:
            raise IndexError("Path index %d invalid for OptV (only 0 allowed)" % index)
        if value.get_opt_value() is None:
            raise IndexError("Cannot follow path into None OptV")

        mutated_inner = mutate_subvalue_with_path(value.get_opt_value(), remaining_path, rng, ctx)
        return value.get_typ().make_opt_value(mutated_inner)

    else:
        # Leaf value types (BoolV, NumV, TextV) don't have subvalues
        raise IndexError("Cannot follow path into leaf value of type %s" % value.__class__.__name__)


def mutate(value, rng, ctx=None):
    """
    Top-level mutation function that randomly selects and mutates any subvalue.

    This function solves the lopsided nesting problem by finding all subvalues
    (including the root) and randomly selecting one to mutate, ensuring that
    deeply nested values have an equal chance of being mutated as shallow ones.

    Args:
        value: The value to mutate
        rng: Random number generator
        ctx: Context for type resolution (optional)

    Returns:
        A new value with one randomly selected subvalue mutated
    """
    # Find all subvalues with their paths
    subvalues = find_subvalues(value)

    # Randomly select one subvalue to mutate
    selected_index = rng.randint(0, len(subvalues) - 1)
    selected_value, selected_path = subvalues[selected_index]

    # Mutate the selected subvalue at its path
    return mutate_subvalue_with_path(value, selected_path, rng, ctx)
