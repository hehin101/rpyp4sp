import random
import unittest
from rpyp4sp.objects import BoolV, NumV, TextV, TupleV, StructV, StructMap, CaseV, ListV, OptV
from rpyp4sp.mutatevalues import mutate_BoolV, mutate_NumV, mutate_TextV, mutate_TupleV, mutate_StructV, mutate_CaseV, mutate_ListV, mutate_OptV
from rpyp4sp.mutatevalues import generate_BoolV, generate_NumV, generate_TextV, generate_OptV, find_subvalues, mutate_subvalue_with_path, mutate
from rpyp4sp.mutatevalues import generate_value
from rpyp4sp.test.test_interp import make_context
from rpyp4sp import p4specast, integers


class MockRng(object):
    """Mock random number generator that returns values from a predefined list."""

    def __init__(self, values):
        self.values = values
        self.index = 0

    def randint(self, min_val, max_val):
        if self.index >= len(self.values):
            raise IndexError("MockRng ran out of values")
        val = self.values[self.index]
        self.index += 1
        # Ensure the value is in the expected range
        return min_val + (val % (max_val - min_val + 1))


class TestBoolVMutation(object):

    def test_basic_mutation(self):
        rng = random.Random(42)

        # Test mutating True to False
        true_val = BoolV.TRUE
        mutated = mutate_BoolV(true_val, rng)

        assert isinstance(mutated, BoolV)
        assert mutated.value is False
        assert mutated.get_typ() == true_val.get_typ()

        # Test mutating False to True
        false_val = BoolV.FALSE
        mutated = mutate_BoolV(false_val, rng)

        assert isinstance(mutated, BoolV)
        assert mutated.value is True
        assert mutated.get_typ() == false_val.get_typ()


class TestNumVMutation(object):

    def test_add_subtract_strategy(self):
        # Test add/subtract strategy (strategy 0)
        rng = MockRng([0, 15])  # strategy=0, delta=5 (since -10 + (15 % 21) = 5)

        original = NumV.make(integers.Integer.fromint(10), p4specast.IntT.INSTANCE)
        mutated = mutate_NumV(original, rng)

        assert isinstance(mutated, NumV)
        assert mutated.value.toint() == 15  # 10 + 5
        assert mutated.get_what() is p4specast.IntT.INSTANCE

    def test_boundary_values_strategy(self):
        # Test boundary values strategy (strategy 1)
        rng = MockRng([1, 0])  # strategy=1, boundary_choice=0 (zero)

        original = NumV.make(integers.Integer.fromint(42), p4specast.IntT.INSTANCE)
        mutated = mutate_NumV(original, rng)

        assert mutated.value.toint() == 0

    def test_bit_flip_strategy(self):
        # Test bit flip strategy (strategy 2)
        rng = MockRng([2, 0])  # strategy=2, bit_pos=0 (flip LSB)

        original = NumV.make(integers.Integer.fromint(10), p4specast.IntT.INSTANCE)  # 1010 in binary
        mutated = mutate_NumV(original, rng)

        assert mutated.value.toint() == 11  # 1011 in binary (LSB flipped)

    def test_new_value_nat_strategy(self):
        # Test new value generation for Nat
        rng = MockRng([3, 42])  # strategy=3, new_int=42

        original = NumV.make(integers.Integer.fromint(100), p4specast.NatT.INSTANCE)
        mutated = mutate_NumV(original, rng)

        assert mutated.value.toint() == 42
        assert mutated.get_what() is p4specast.NatT.INSTANCE

    def test_nat_stays_positive(self):
        # Test that Nat values stay non-negative even with negative operations
        rng = MockRng([1, 2])  # strategy=1, boundary_choice=2 (-1)

        original = NumV.make(integers.Integer.fromint(5), p4specast.NatT.INSTANCE)
        mutated = mutate_NumV(original, rng)

        # Should be converted to positive
        assert mutated.value.toint() == 1  # abs(-1)
        assert mutated.get_what() is p4specast.NatT.INSTANCE


class TestTextVMutation(object):

    def test_empty_string_mutation(self):
        # Test empty string gets a character added
        rng = MockRng([33])  # ASCII 'A' (32 + (33 % 95) = 32 + 33 = 65)

        original = TextV("")
        mutated = mutate_TextV(original, rng)

        assert isinstance(mutated, TextV)
        assert len(mutated.value) == 1
        assert mutated.value == "A"

    def test_insert_char_strategy(self):
        # Test insert strategy (strategy 0)
        rng = MockRng([0, 1, 33])  # strategy=0, pos=1, char='A'

        original = TextV("hello")
        mutated = mutate_TextV(original, rng)

        assert mutated.value == "hAello"

    def test_delete_char_strategy(self):
        # Test delete strategy (strategy 1)
        rng = MockRng([1, 1])  # strategy=1, pos=1

        original = TextV("hello")
        mutated = mutate_TextV(original, rng)

        assert mutated.value == "hllo"

    def test_replace_char_strategy(self):
        # Test replace strategy (strategy 2)
        rng = MockRng([2, 1, 33])  # strategy=2, pos=1, char='A'

        original = TextV("hello")
        mutated = mutate_TextV(original, rng)

        assert mutated.value == "hAllo"

    def test_insert_special_strategy(self):
        # Test insert special character strategy (strategy 3)
        rng = MockRng([3, 1, 0])  # strategy=3, pos=1, special_char='"'

        original = TextV("hello")
        mutated = mutate_TextV(original, rng)

        assert mutated.value == 'h"ello'

    def test_flip_case_strategy(self):
        # Test case flip strategy (strategy 4)
        rng = MockRng([4, 1])  # strategy=4, pos=1 ('e' -> 'E')

        original = TextV("hello")
        mutated = mutate_TextV(original, rng)

        assert mutated.value == "hEllo"

    def test_single_char_delete(self):
        # Test deleting from single character string
        rng = MockRng([1])  # strategy=1 (delete)

        original = TextV("x")
        mutated = mutate_TextV(original, rng)

        assert mutated.value == ""


class TestTupleVMutation(object):

    def test_empty_tuple_unchanged(self):
        # Empty tuple should return unchanged
        rng = MockRng([])

        original = TupleV.make0()
        mutated = mutate_TupleV(original, rng)

        assert mutated is original

    def test_single_element_mutation(self):
        # Single element tuple - mutate that element
        rng = MockRng([0])  # index=0 (only option), then BoolV will flip

        elements = [BoolV.TRUE]
        original = TupleV.make(elements)
        mutated = mutate_TupleV(original, rng)

        assert isinstance(mutated, TupleV)
        assert mutated._get_size_list() == 1
        assert isinstance(mutated._get_list(0), BoolV)
        assert mutated._get_list(0).value is False

    def test_multi_element_mutation(self):
        # Test mutating second element of a tuple
        rng = MockRng([1, 0, 15])  # index=1, NumV strategy=0 (add/subtract), delta=5

        elements = [
            BoolV.TRUE,
            NumV.make(integers.Integer.fromint(42), p4specast.IntT.INSTANCE),
            TextV("hello")
        ]
        original = TupleV.make(elements)
        mutated = mutate_TupleV(original, rng)

        assert isinstance(mutated, TupleV)
        assert mutated._get_size_list() == 3

        # First and third elements should be unchanged
        assert mutated._get_list(0) is elements[0]
        assert mutated._get_list(2) is elements[2]

        # Second element should be mutated (NumV)
        mutated_num = mutated._get_list(1)
        assert isinstance(mutated_num, NumV)
        assert mutated_num.value.toint() == 47  # 42 + 5

    def test_preserves_other_elements(self):
        # Test that only the selected element changes
        rng = MockRng([0])  # index=0, mutate first element (BoolV)

        bool_val = BoolV.FALSE
        text_val = TextV("unchanged")
        elements = [bool_val, text_val]
        original = TupleV.make(elements)
        mutated = mutate_TupleV(original, rng)

        assert mutated._get_size_list() == 2
        # First element should be mutated
        assert mutated._get_list(0).value is True  # False -> True
        # Second element should be the same object
        assert mutated._get_list(1) is text_val


class TestStructVMutation(object):

    def test_empty_struct_unchanged(self):
        # Empty struct should return unchanged
        rng = MockRng([])

        original = StructV.make0(StructMap.EMPTY)
        mutated = mutate_StructV(original, rng)

        assert mutated is original

    def test_single_field_mutation(self):
        # Single field struct - mutate that field
        rng = MockRng([0])  # index=0 (only option), then BoolV will flip

        struct_map = StructMap.EMPTY.add_field("flag")
        field_values = [BoolV.TRUE]
        original = StructV.make(field_values, struct_map)
        mutated = mutate_StructV(original, rng)

        assert isinstance(mutated, StructV)
        assert mutated._get_size_list() == 1
        assert isinstance(mutated._get_list(0), BoolV)
        assert mutated._get_list(0).value is False
        assert mutated.map is struct_map  # Map should be preserved

    def test_multi_field_mutation(self):
        # Test mutating second field of a struct
        rng = MockRng([1, 0, 15])  # index=1, NumV strategy=0, delta=5

        struct_map = StructMap.EMPTY.add_field("name").add_field("age").add_field("active")
        field_values = [
            TextV("Alice"),
            NumV.make(integers.Integer.fromint(25), p4specast.IntT.INSTANCE),
            BoolV.TRUE
        ]
        original = StructV.make(field_values, struct_map)
        mutated = mutate_StructV(original, rng)

        assert isinstance(mutated, StructV)
        assert mutated._get_size_list() == 3

        # First and third fields should be unchanged
        assert mutated._get_list(0) is field_values[0]
        assert mutated._get_list(2) is field_values[2]

        # Second field should be mutated (NumV)
        mutated_age = mutated._get_list(1)
        assert isinstance(mutated_age, NumV)
        assert mutated_age.value.toint() == 30  # 25 + 5
        assert mutated.map is struct_map  # Map should be preserved

    def test_preserves_struct_map(self):
        # Test that the struct map is preserved
        rng = MockRng([0, 0, 1, 33])  # index=0, TextV strategy=0 (insert), pos=1, char='A'

        struct_map = StructMap.EMPTY.add_field("message").add_field("count")
        field_values = [TextV("hello"), NumV.make(integers.Integer.fromint(42), p4specast.IntT.INSTANCE)]
        original = StructV.make(field_values, struct_map)
        mutated = mutate_StructV(original, rng)

        assert mutated._get_size_list() == 2
        assert mutated.map is struct_map
        # First field should be mutated (TextV will change)
        # assert mutated._get_list(0).value == "hAello"  # "hello" with 'A' inserted at pos 1
        assert mutated._get_list(0).value == "hello"  # string mutation is disabled
        # Second field should be unchanged
        assert mutated._get_list(1) is field_values[1]


class TestCaseVMutation(object):

    def test_empty_case_unchanged(self):
        # Empty case should return unchanged
        rng = MockRng([])

        # Create a mixop for empty case
        mixop = p4specast.MixOp([])
        original = CaseV.make0(mixop)
        mutated = mutate_CaseV(original, rng)

        assert mutated is original

    def test_single_value_mutation(self):
        # Single value case - mutate that value
        rng = MockRng([0])  # index=0 (only option), then BoolV will flip

        # Create a simple mixop and case
        phrases = [p4specast.AtomT("flag"), None]
        mixop = p4specast.MixOp(phrases)
        values = [BoolV.TRUE]
        original = CaseV.make(values, mixop)
        mutated = mutate_CaseV(original, rng)

        assert isinstance(mutated, CaseV)
        assert mutated._get_size_list() == 1
        assert isinstance(mutated._get_list(0), BoolV)
        assert mutated._get_list(0).value is False
        assert mutated.mixop is mixop  # MixOp should be preserved

    def test_multi_value_mutation(self):
        # Test mutating second value of a case
        rng = MockRng([1, 0, 15])  # index=1, NumV strategy=0, delta=5

        # Create mixop for a case with multiple values
        phrases = [
            p4specast.AtomT("name"), None,
            p4specast.AtomT("age"), None,
            p4specast.AtomT("active"), None,
        ]
        mixop = p4specast.MixOp(phrases)
        values = [
            TextV("Alice"),
            NumV.make(integers.Integer.fromint(25), p4specast.IntT.INSTANCE),
            BoolV.TRUE
        ]
        original = CaseV.make(values, mixop)
        mutated = mutate_CaseV(original, rng)

        assert isinstance(mutated, CaseV)
        assert mutated._get_size_list() == 3

        # First and third values should be unchanged
        assert mutated._get_list(0) is values[0]
        assert mutated._get_list(2) is values[2]

        # Second value should be mutated (NumV)
        mutated_age = mutated._get_list(1)
        assert isinstance(mutated_age, NumV)
        assert mutated_age.value.toint() == 30  # 25 + 5
        assert mutated.mixop is mixop  # MixOp should be preserved

    def test_preserves_mixop(self):
        # Test that the mixop is preserved
        rng = MockRng([0, 0, 1, 33])  # index=0, TextV strategy=0 (insert), pos=1, char='A'

        phrases = [p4specast.AtomT("message"), None, p4specast.AtomT("count"), None]
        mixop = p4specast.MixOp(phrases)
        values = [TextV("hello"), NumV.make(integers.Integer.fromint(42), p4specast.IntT.INSTANCE)]
        original = CaseV.make(values, mixop)
        mutated = mutate_CaseV(original, rng)

        assert mutated._get_size_list() == 2
        assert mutated.mixop is mixop
        # First value should be mutated (TextV will change)
        # assert mutated._get_list(0).value == "hAello"  # "hello" with 'A' inserted at pos 1
        assert mutated._get_list(0).value == "hello"  # string mutation is disabled
        # Second value should be unchanged
        assert mutated._get_list(1) is values[1]


class TestListVMutation(object):

    def test_empty_list_unchanged(self):
        # Empty list should return unchanged
        rng = MockRng([])
        typ = p4specast.TextT.INSTANCE.list_of()
        original = ListV.make0(typ)
        mutated = mutate_ListV(original, rng)

        assert mutated is original

    def test_mutate_element_strategy(self):
        # Strategy 0: Mutate existing element
        rng = MockRng([0, 0])  # strategy=0, then BoolV will flip

        elements = [BoolV.TRUE, BoolV.FALSE]
        typ = p4specast.BoolT.INSTANCE.list_of()
        original = ListV.make(elements, typ)
        mutated = mutate_ListV(original, rng)

        assert isinstance(mutated, ListV)
        assert mutated._get_size_list() == 2  # Same length
        assert mutated._get_list(0).value is False  # First element mutated
        assert mutated._get_list(1) is elements[1]  # Second unchanged

    def test_insert_duplicate_strategy(self):
        # Strategy 1: Insert duplicate element
        rng = MockRng([1, 1, 1])  # strategy=1, source_index=1, insert_pos=1

        elements = [TextV("a"), TextV("b")]
        typ = p4specast.TextT.INSTANCE.list_of()
        original = ListV.make(elements, typ)
        mutated = mutate_ListV(original, rng)

        assert mutated._get_size_list() == 3  # Length increased
        assert mutated._get_list(0).value == "a"
        assert mutated._get_list(1).value == "b"  # Duplicate of index 1
        assert mutated._get_list(2).value == "b"

    def test_remove_element_strategy(self):
        # Strategy 2: Remove element
        rng = MockRng([2, 0])  # strategy=2, remove_index=0

        typ = p4specast.TextT.INSTANCE.list_of()
        elements = [TextV("a"), TextV("b"), TextV("c")]
        original = ListV.make(elements, typ)
        mutated = mutate_ListV(original, rng)

        assert mutated._get_size_list() == 2  # Length decreased
        assert mutated._get_list(0).value == "b"  # First element removed
        assert mutated._get_list(1).value == "c"

    def test_remove_single_element_makes_empty(self):
        # Strategy 2 on single element should make empty
        rng = MockRng([2])  # strategy=2

        typ = p4specast.TextT.INSTANCE.list_of()
        elements = [TextV("only")]
        original = ListV.make(elements, typ)
        mutated = mutate_ListV(original, rng)

        assert mutated._get_size_list() == 0  # Empty list

    def test_swap_elements_strategy(self):
        # Strategy 3: Swap two elements
        rng = MockRng([3, 0, 2])  # strategy=3, idx1=0, idx2=2

        elements = [TextV("a"), TextV("b"), TextV("c")]
        typ = p4specast.TextT.INSTANCE.list_of()
        original = ListV.make(elements, typ)
        mutated = mutate_ListV(original, rng)

        assert mutated._get_size_list() == 3  # Same length
        assert mutated._get_list(0).value == "c"  # Swapped
        assert mutated._get_list(1).value == "b"  # Unchanged
        assert mutated._get_list(2).value == "a"  # Swapped

    def test_swap_same_index_adjusts(self):
        # Strategy 3 with same indices should adjust second index
        rng = MockRng([3, 1, 1])  # strategy=3, idx1=1, idx2=1 (will become 2)

        elements = [TextV("a"), TextV("b"), TextV("c")]
        typ = p4specast.TextT.INSTANCE.list_of()
        original = ListV.make(elements, typ)
        mutated = mutate_ListV(original, rng)

        assert mutated._get_size_list() == 3
        assert mutated._get_list(0).value == "a"  # Unchanged
        assert mutated._get_list(1).value == "c"  # Swapped with index 2
        assert mutated._get_list(2).value == "b"  # Swapped with index 1

    def test_swap_single_element_falls_back_to_mutate(self):
        # Strategy 3 on single element should fall back to mutation
        rng = MockRng([3, 0])  # strategy=3, then BoolV will flip

        elements = [BoolV.TRUE]
        typ = p4specast.BoolT.INSTANCE.list_of()
        original = ListV.make(elements, typ)
        mutated = mutate_ListV(original, rng)

        assert mutated._get_size_list() == 1  # Same length
        assert mutated._get_list(0).value is False  # Element mutated

    def test_clear_list_strategy(self):
        # Strategy 4: Clear list
        rng = MockRng([4])  # strategy=4

        typ = p4specast.TextT.INSTANCE.list_of()
        elements = [TextV("a"), TextV("b"), TextV("c")]
        original = ListV.make(elements, typ)
        mutated = mutate_ListV(original, rng)

        assert mutated._get_size_list() == 0  # Empty list


class TestOptVMutation(object):

    def test_none_value_unchanged(self):
        # OptV with None should return unchanged
        rng = MockRng([])

        typ = p4specast.BoolT.INSTANCE.opt_of()
        original = typ.make_opt_value(None)
        mutated = mutate_OptV(original, rng)

        assert mutated is original

    def test_mutate_contained_value_strategy(self):
        # Strategy 0: Mutate the contained value
        rng = MockRng([0])  # strategy=0, then BoolV will flip

        typ = p4specast.IterT(p4specast.BoolT.INSTANCE, p4specast.Opt.INSTANCE)

        inner_value = BoolV.TRUE
        original = typ.make_opt_value(inner_value)
        mutated = mutate_OptV(original, rng)

        assert isinstance(mutated, OptV)
        assert mutated.get_opt_value() is not None
        assert isinstance(mutated.get_opt_value(), BoolV)
        assert mutated.get_opt_value().value is False  # BoolV was flipped
        assert mutated.get_typ() == original.get_typ()

    def test_make_none_strategy(self):
        # Strategy 1: Make it None
        rng = MockRng([1])  # strategy=1

        inner_value = TextV("hello")
        typ = p4specast.TextT.INSTANCE.opt_of()
        original = typ.make_opt_value(inner_value)
        mutated = mutate_OptV(original, rng)

        assert isinstance(mutated, OptV)
        assert mutated.get_opt_value() is None
        assert mutated.get_typ() == original.get_typ()


# ____________________________________________________________
# Tests for fresh value generation


class TestGenerateBoolV(object):

    def test_generate_true(self):
        # Test generating True
        rng = MockRng([1])  # randint(0, 1) returns 1, so 1 == 1 is True

        bool_type = p4specast.BoolT.INSTANCE
        generated = generate_BoolV(bool_type, rng)

        assert isinstance(generated, BoolV)
        assert generated.value is True
        assert generated.get_typ() is bool_type

    def test_generate_false(self):
        # Test generating False
        rng = MockRng([0])  # randint(0, 1) returns 0, so 0 == 1 is False

        bool_type = p4specast.BoolT.INSTANCE
        generated = generate_BoolV(bool_type, rng)

        assert isinstance(generated, BoolV)
        assert generated.value is False
        assert generated.get_typ() is bool_type

    def test_random_distribution(self):
        # Test with real random to verify both values can be generated
        rng = random.Random(42)
        bool_type = p4specast.BoolT.INSTANCE

        values = set()
        for _ in range(100):
            generated = generate_BoolV(bool_type, rng)
            values.add(generated.value)

        # Should have generated both True and False
        assert True in values
        assert False in values


class TestGenerateNumV(object):

    def test_generate_nat(self):
        # Test generating natural number
        rng = MockRng([42])  # Will generate 42

        num_type = p4specast.NumT.NAT
        generated = generate_NumV(num_type, rng)

        assert isinstance(generated, NumV)
        assert generated.value.toint() == 42
        assert generated.get_what() is p4specast.NatT.INSTANCE
        assert generated.get_typ() is num_type

    def test_generate_int(self):
        # Test generating integer (can be negative)
        rng = MockRng([42])  # -500 + (42 % 1001) = -500 + 42 = -458

        num_type = p4specast.NumT.INT
        generated = generate_NumV(num_type, rng)

        assert isinstance(generated, NumV)
        assert generated.value.toint() == -458
        assert generated.get_what() is p4specast.IntT.INSTANCE
        assert generated.get_typ() is num_type

    def test_nat_range(self):
        # Test that Nat values are in expected range
        rng = random.Random(42)
        num_type = p4specast.NumT.NAT

        for _ in range(50):
            generated = generate_NumV(num_type, rng)
            value = generated.value.toint()
            assert 0 <= value <= 1000

    def test_int_range(self):
        # Test that Int values are in expected range
        rng = random.Random(42)
        num_type = p4specast.NumT.INT

        for _ in range(50):
            generated = generate_NumV(num_type, rng)
            value = generated.value.toint()
            assert -500 <= value <= 500


class TestGenerateTextV(object):

    @unittest.skip("string mutation is disabled")
    def test_generate_empty_string(self):
        # Test strategy 0: empty string
        rng = MockRng([0])  # strategy=0

        text_type = p4specast.TextT.INSTANCE
        generated = generate_TextV(text_type, rng)

        assert isinstance(generated, TextV)
        assert generated.value == ""
        assert generated.get_typ() is text_type

    @unittest.skip("string mutation is disabled")
    def test_generate_random_string(self):
        # Test strategy 1: random string
        # randint(1, 10) with val=2 gives: 1 + (2 % 10) = 3 (length=3)
        # then 3 calls to randint(32, 126): val=33->A, val=34->B, val=35->C
        rng = MockRng([1, 2, 33, 34, 35])  # strategy=1, length=3, chars=A,B,C

        text_type = p4specast.TextT.INSTANCE
        generated = generate_TextV(text_type, rng)

        assert isinstance(generated, TextV)
        assert len(generated.value) == 3
        assert generated.value == "ABC"
        assert generated.get_typ() is text_type

    def test_generate_common_string(self):
        # Test strategy 2: common test strings
        rng = MockRng([2, 0])  # strategy=2, index=0 ("hello")

        text_type = p4specast.TextT.INSTANCE
        generated = generate_TextV(text_type, rng)

        assert isinstance(generated, TextV)
        # assert generated.value == "hello"
        assert generated.value == "test"  # string mutation is disabled -> no strategy selection
        assert generated.get_typ() is text_type

    @unittest.skip("string mutation is disabled")
    def test_generate_special_char_only(self):
        # Test strategy 3: special character only
        rng = MockRng([3, 0, 0])  # strategy=3, special_char='"', choice=0 (char only)

        text_type = p4specast.TextT.INSTANCE
        generated = generate_TextV(text_type, rng)

        assert isinstance(generated, TextV)
        assert generated.value == '"'
        assert generated.get_typ() is text_type

    @unittest.skip("string mutation is disabled")
    def test_generate_special_char_with_prefix(self):
        # Test strategy 3: special character with prefix
        rng = MockRng([3, 0, 1, 0])  # strategy=3, special_char='"', choice=1, prefix='a'

        text_type = p4specast.TextT.INSTANCE
        generated = generate_TextV(text_type, rng)

        assert isinstance(generated, TextV)
        assert generated.value == 'a"'
        assert generated.get_typ() is text_type

    @unittest.skip("string mutation is disabled")
    def test_random_distribution(self):
        # Test with real random to verify various strategies work
        rng = random.Random(42)
        text_type = p4specast.TextT.INSTANCE

        lengths = set()
        has_empty = False
        has_special = False

        for _ in range(100):
            generated = generate_TextV(text_type, rng)
            text = generated.value
            lengths.add(len(text))

            if text == "":
                has_empty = True
            if any(c in text for c in ['"', "'", "\\", "\n", "\t", "\r"]):
                has_special = True

        # Should generate various lengths including empty
        assert has_empty
        assert len(lengths) > 1
        assert has_special


class TestGenerateOptV(object):

    def test_generate_none(self):
        # Test generating None (choice=0)
        rng = MockRng([0])  # randint(0, 1) returns 0, so generate None

        # Create an OptT for BoolT
        inner_type = p4specast.BoolT.INSTANCE
        opt_type = inner_type.opt_of()
        generated = generate_OptV(opt_type, rng)

        assert isinstance(generated, OptV)
        assert generated.get_opt_value() is None
        assert generated.get_typ() is opt_type

    def test_generate_some_bool(self):
        # Test generating Some(BoolV) (choice=1, then BoolV=True)
        rng = MockRng([1, 1])  # choice=1 (generate value), then BoolV=True

        inner_type = p4specast.BoolT.INSTANCE
        opt_type = inner_type.opt_of()
        generated = generate_OptV(opt_type, rng)

        assert isinstance(generated, OptV)
        assert generated.get_opt_value() is not None
        assert isinstance(generated.get_opt_value(), BoolV)
        assert generated.get_opt_value().value is True
        assert generated.get_typ() is opt_type

    def test_generate_some_num(self):
        # Test generating Some(NumV) (choice=1, then NumV=42)
        rng = MockRng([1, 42])  # choice=1 (generate value), then NumV=42

        inner_type = p4specast.NumT(p4specast.NatT.INSTANCE)
        opt_type = inner_type.opt_of()
        generated = generate_OptV(opt_type, rng)

        assert isinstance(generated, OptV)
        assert generated.get_opt_value() is not None
        assert isinstance(generated.get_opt_value(), NumV)
        assert generated.get_opt_value().value.toint() == 42
        assert generated.get_typ() is opt_type

    @unittest.skip("string mutation is disabled")
    def test_generate_some_text(self):
        # Test generating Some(TextV) (choice=1, then TextV="")
        rng = MockRng([1, 0])  # choice=1 (generate value), then TextV strategy=0 (empty)

        inner_type = p4specast.TextT.INSTANCE
        opt_type = inner_type.opt_of()
        generated = generate_OptV(opt_type, rng)

        assert isinstance(generated, OptV)
        assert generated.get_opt_value() is not None
        assert isinstance(generated.get_opt_value(), TextV)
        assert generated.get_opt_value().value == ""
        assert generated.get_typ() is opt_type

    def test_random_distribution(self):
        # Test with real random to verify both None and Some values can be generated
        rng = random.Random(42)
        inner_type = p4specast.BoolT.INSTANCE
        opt_type = inner_type.opt_of()

        has_none = False
        has_some = False

        for _ in range(100):
            generated = generate_OptV(opt_type, rng)
            if generated.get_opt_value() is None:
                has_none = True
            else:
                has_some = True

        # Should have generated both None and Some values
        assert has_none
        assert has_some


# ____________________________________________________________
# Tests for deep mutation helpers


class TestFindSubvalues(object):

    def test_simple_value(self):
        # Test with simple values that have no subvalues
        bool_val = BoolV.TRUE
        subvalues = find_subvalues(bool_val)

        assert len(subvalues) == 1
        assert subvalues[0] == (bool_val, [])

        num_val = NumV.make(integers.Integer.fromint(42), p4specast.IntT.INSTANCE)
        subvalues = find_subvalues(num_val)

        assert len(subvalues) == 1
        assert subvalues[0] == (num_val, [])

        text_val = TextV("hello")
        subvalues = find_subvalues(text_val)

        assert len(subvalues) == 1
        assert subvalues[0] == (text_val, [])

    def test_empty_containers(self):
        # Test with empty containers
        empty_tuple = TupleV.make0(None)
        subvalues = find_subvalues(empty_tuple)

        assert len(subvalues) == 1
        assert subvalues[0] == (empty_tuple, [])

        typ = p4specast.TextT.INSTANCE.list_of()
        empty_list = ListV.make0(typ)
        subvalues = find_subvalues(empty_list)

        assert len(subvalues) == 1
        assert subvalues[0] == (empty_list, [])

    def test_opt_none(self):
        # Test OptV with None
        typ = p4specast.BoolT.INSTANCE.opt_of()
        opt_none = typ.make_opt_value(None)
        subvalues = find_subvalues(opt_none)

        assert len(subvalues) == 1
        assert subvalues[0] == (opt_none, [])

    def test_opt_some(self):
        # Test OptV with a value
        inner_bool = BoolV.TRUE
        typ = p4specast.BoolT.INSTANCE.opt_of()
        opt_some = typ.make_opt_value(inner_bool)
        subvalues = find_subvalues(opt_some)

        assert len(subvalues) == 2
        assert subvalues[0] == (opt_some, [])
        assert subvalues[1] == (inner_bool, [0])

    def test_tuple_flat(self):
        # Test flat tuple
        bool_val = BoolV.TRUE
        num_val = NumV.make(integers.Integer.fromint(42), p4specast.IntT.INSTANCE)
        text_val = TextV("hello")

        tuple_val = TupleV.make([bool_val, num_val, text_val])
        subvalues = find_subvalues(tuple_val)

        assert len(subvalues) == 4
        assert subvalues[0] == (tuple_val, [])
        assert subvalues[1] == (bool_val, [0])
        assert subvalues[2] == (num_val, [1])
        assert subvalues[3] == (text_val, [2])

    def test_list_flat(self):
        # Test flat list
        bool_val = BoolV.TRUE
        bool_val2 = BoolV.FALSE

        typ = p4specast.BoolT.INSTANCE.list_of()
        list_val = ListV.make([bool_val, bool_val2], typ)
        subvalues = find_subvalues(list_val)

        assert len(subvalues) == 3
        assert subvalues[0] == (list_val, [])
        assert subvalues[1] == (bool_val, [0])
        assert subvalues[2] == (bool_val2, [1])

    def test_struct_flat(self):
        # Test flat struct
        bool_val = BoolV.TRUE
        num_val = NumV.make(integers.Integer.fromint(42), p4specast.IntT.INSTANCE)

        struct_map = StructMap.EMPTY.add_field("flag").add_field("count")
        struct_val = StructV.make([bool_val, num_val], struct_map)
        subvalues = find_subvalues(struct_val)

        assert len(subvalues) == 3
        assert subvalues[0] == (struct_val, [])
        assert subvalues[1] == (bool_val, [0])
        assert subvalues[2] == (num_val, [1])

    def test_nested_tuple_in_tuple(self):
        # Test nested structure: tuple containing tuple
        inner_bool = BoolV.TRUE
        inner_text = TextV("inner")
        inner_tuple = TupleV.make([inner_bool, inner_text])

        outer_num = NumV.make(integers.Integer.fromint(42), p4specast.IntT.INSTANCE)
        outer_tuple = TupleV.make([inner_tuple, outer_num])

        subvalues = find_subvalues(outer_tuple)

        # Should be breadth-first: outer_tuple, inner_tuple, outer_num, inner_bool, inner_text
        assert len(subvalues) == 5
        assert subvalues[0] == (outer_tuple, [])
        assert subvalues[1] == (inner_tuple, [0])
        assert subvalues[2] == (outer_num, [1])
        assert subvalues[3] == (inner_bool, [0, 0])
        assert subvalues[4] == (inner_text, [0, 1])

    def test_nested_opt_in_list(self):
        # Test nested structure: list containing OptV
        inner_bool = BoolV.FALSE
        typ = p4specast.BoolT.INSTANCE.opt_of()
        opt_val = typ.make_opt_value(inner_bool)
        text_val = TextV("hello")

        list_val = ListV.make([opt_val, text_val], None)
        subvalues = find_subvalues(list_val)

        # Should be breadth-first: list_val, opt_val, text_val, inner_bool
        assert len(subvalues) == 4
        assert subvalues[0] == (list_val, [])
        assert subvalues[1] == (opt_val, [0])
        assert subvalues[2] == (text_val, [1])
        assert subvalues[3] == (inner_bool, [0, 0])

    def test_deeply_nested(self):
        # Test deeply nested structure to verify breadth-first order
        # Structure: tuple([list([bool, opt(text)]), num])
        inner_bool = BoolV.TRUE
        inner_text = TextV("deep")
        typ = p4specast.TextT.INSTANCE.opt_of()
        inner_opt = typ.make_opt_value(inner_text)
        inner_list = ListV.make([inner_bool, inner_opt], None)

        outer_num = NumV.make(integers.Integer.fromint(99), p4specast.IntT.INSTANCE)
        outer_tuple = TupleV.make([inner_list, outer_num])

        subvalues = find_subvalues(outer_tuple)

        # Breadth-first: outer_tuple, inner_list, outer_num, inner_bool, inner_opt, inner_text
        assert len(subvalues) == 6
        assert subvalues[0] == (outer_tuple, [])
        assert subvalues[1] == (inner_list, [0])
        assert subvalues[2] == (outer_num, [1])
        assert subvalues[3] == (inner_bool, [0, 0])
        assert subvalues[4] == (inner_opt, [0, 1])
        assert subvalues[5] == (inner_text, [0, 1, 0])


class TestMutateSubvalueWithPath(object):

    def test_empty_path_mutates_root(self):
        # Empty path should mutate the root value itself
        rng = MockRng([0])

        bool_val = BoolV.TRUE
        mutated = mutate_subvalue_with_path(bool_val, [], rng)

        assert isinstance(mutated, BoolV)
        assert mutated.value is False  # BoolV flips

    def test_single_index_tuple(self):
        # Test mutating a single element in a tuple
        rng = MockRng([0])  # BoolV will flip

        bool_val = BoolV.TRUE
        text_val = TextV("hello")
        tuple_val = TupleV.make([bool_val, text_val])

        # Mutate the first element (index 0)
        mutated = mutate_subvalue_with_path(tuple_val, [0], rng)

        assert isinstance(mutated, TupleV)
        assert mutated._get_size_list() == 2
        # First element should be mutated
        assert mutated._get_list(0).value is False  # True -> False
        # Second element should be unchanged (same object)
        assert mutated._get_list(1) is text_val

    def test_single_index_list(self):
        # Test mutating a single element in a list
        rng = MockRng([0, 0, 1, 33])  # mutate=0, TextV strategy=0 (insert), pos=1, char='A'

        text1 = TextV("hello")
        text2 = TextV("world")
        list_val = ListV.make([text1, text2], None)

        # Mutate the first element (index 0)
        mutated = mutate_subvalue_with_path(list_val, [0], rng)

        assert isinstance(mutated, ListV)
        assert mutated._get_size_list() == 2
        # First element should be mutated
        # assert mutated._get_list(0).value == "hAello"  # "hello" with 'A' inserted
        assert mutated._get_list(0).value == "hello"  # string mutation is disabled
        # Second element should be unchanged
        assert mutated._get_list(1) is text2

    def test_single_index_struct(self):
        # Test mutating a field in a struct
        rng = MockRng([0, 0, 15])  # NumV strategy=0 (add/subtract), delta=5

        name_val = TextV("Alice")
        age_val = NumV.make(integers.Integer.fromint(25), p4specast.IntT.INSTANCE)

        struct_map = StructMap.EMPTY.add_field("name").add_field("age")
        struct_val = StructV.make([name_val, age_val], struct_map)

        # Mutate the second field (index 1)
        mutated = mutate_subvalue_with_path(struct_val, [1], rng)

        assert isinstance(mutated, StructV)
        assert mutated._get_size_list() == 2
        # First field should be unchanged
        assert mutated._get_list(0) is name_val
        # Second field should be mutated
        assert mutated._get_list(1).value.toint() == 30  # 25 + 5
        assert mutated.map is struct_map  # Map preserved

    def test_single_index_opt(self):
        # Test mutating the value inside an OptV
        rng = MockRng([0])  # mutate=0, BoolV will flip

        inner_bool = BoolV.TRUE
        typ = p4specast.BoolT.INSTANCE.opt_of()
        opt_val = typ.make_opt_value(inner_bool)

        # Mutate the contained value (index 0)
        mutated = mutate_subvalue_with_path(opt_val, [0], rng)

        assert isinstance(mutated, OptV)
        assert mutated.get_opt_value() is not None
        assert isinstance(mutated.get_opt_value(), BoolV)
        assert mutated.get_opt_value().value is False  # True -> False

    def test_nested_path(self):
        # Test mutating with a multi-level path
        rng = MockRng([0])  # BoolV will flip

        # Structure: tuple([list([bool, text]), num])
        inner_bool = BoolV.TRUE
        inner_text = TextV("nested")
        inner_list = ListV.make([inner_bool, inner_text], None)

        outer_num = NumV.make(integers.Integer.fromint(42), p4specast.IntT.INSTANCE)
        outer_tuple = TupleV.make([inner_list, outer_num])

        # Mutate the bool inside the list inside the tuple: path [0, 0]
        mutated = mutate_subvalue_with_path(outer_tuple, [0, 0], rng)

        assert isinstance(mutated, TupleV)
        assert mutated._get_size_list() == 2

        # Second element (num) should be unchanged
        assert mutated._get_list(1) is outer_num

        # First element should be a new list
        mutated_list = mutated._get_list(0)
        assert isinstance(mutated_list, ListV)
        assert mutated_list._get_size_list() == 2

        # First element of the list should be mutated bool
        assert mutated_list._get_list(0).value is False  # True -> False
        # Second element of the list should be unchanged
        assert mutated_list._get_list(1) is inner_text

    def test_deep_nested_path(self):
        # Test deeply nested path: tuple([list([bool, opt(text)]), num])
        rng = MockRng([0, 0, 1, 33])  # mutate=0, TextV strategy=0 (insert), pos=1, char='A'

        inner_text = TextV("deep")
        typ = p4specast.TextT.INSTANCE.opt_of()
        inner_opt = typ.make_opt_value(inner_text)
        inner_bool = BoolV.TRUE
        inner_list = ListV.make([inner_bool, inner_opt], None)

        outer_num = NumV.make(integers.Integer.fromint(99), p4specast.IntT.INSTANCE)
        outer_tuple = TupleV.make([inner_list, outer_num])

        # Mutate the text inside opt inside list inside tuple: path [0, 1, 0]
        mutated = mutate_subvalue_with_path(outer_tuple, [0, 1, 0], rng)

        # Navigate down to verify the mutation
        mutated_list = mutated._get_list(0)
        mutated_opt = mutated_list._get_list(1)
        mutated_text = mutated_opt.get_opt_value()

        # assert mutated_text.value == "dAeep"  # "deep" with 'A' inserted at pos 1
        assert mutated_text.value == "deep"  # string mutation is disabled

        # Verify unchanged parts
        assert mutated._get_list(1) is outer_num  # outer num unchanged
        assert mutated_list._get_list(0) is inner_bool  # inner bool unchanged

    def test_invalid_path_index_out_of_bounds(self):
        # Test error handling for invalid paths
        rng = MockRng([])

        tuple_val = TupleV.make([BoolV.TRUE])

        # Index 1 is out of bounds for single-element tuple
        try:
            mutate_subvalue_with_path(tuple_val, [1], rng)
            assert False, "Should have raised IndexError"
        except IndexError as e:
            assert "out of bounds" in str(e)

    def test_invalid_path_into_leaf(self):
        # Test error when trying to follow path into leaf value
        rng = MockRng([])

        bool_val = BoolV.TRUE

        # Can't follow path [0] into a BoolV
        try:
            mutate_subvalue_with_path(bool_val, [0], rng)
            assert False, "Should have raised IndexError"
        except IndexError as e:
            assert "leaf value" in str(e)

    def test_invalid_path_into_none_opt(self):
        # Test error when trying to follow path into None OptV
        rng = MockRng([])

        typ = p4specast.BoolT.INSTANCE.opt_of()
        opt_none = typ.make_opt_value(None)

        # Can't follow path [0] into None OptV
        try:
            mutate_subvalue_with_path(opt_none, [0], rng)
            assert False, "Should have raised IndexError"
        except IndexError as e:
            assert "None OptV" in str(e)


class TestMutate(object):

    def test_simple_value_mutation(self):
        # Test mutation of simple leaf values
        rng = MockRng([0, 0])  # mutate=0, select index 0 (the only subvalue), then BoolV will flip

        bool_val = BoolV.TRUE
        mutated = mutate(bool_val, rng)

        assert isinstance(mutated, BoolV)
        assert mutated.value is False  # True -> False

    def test_tuple_random_selection(self):
        # Test that different elements can be selected in a tuple
        # Create tuple with [BoolV.TRUE, TextV("hello"), NumV(42)]
        bool_val = BoolV.TRUE
        text_val = TextV("hello")
        num_val = NumV.make(integers.Integer.fromint(42), p4specast.IntT.INSTANCE)
        tuple_val = TupleV.make([bool_val, text_val, num_val])

        # Test selecting index 0 (the tuple itself) -> will call mutate_value which mutates first element
        rng = MockRng([0, 0, 0])  # select index 0 (tuple), mutate=0, then mutate first element
        mutated = mutate(tuple_val, rng)
        # First element should be mutated
        assert mutated._get_list(0).value is False
        assert mutated._get_list(1) is text_val
        assert mutated._get_list(2) is num_val

        # Test selecting index 1 (first element directly)
        rng = MockRng([1, 0])  # select index 1 (bool_val directly), mutate=0
        mutated = mutate(tuple_val, rng)
        assert mutated._get_list(0).value is False  # BoolV flipped
        assert mutated._get_list(1) is text_val
        assert mutated._get_list(2) is num_val

    def test_nested_structure_fair_selection(self):
        # Test that deeply nested values can be selected
        # Structure: tuple([bool, list([text, opt(num)])])
        deep_num = NumV.make(integers.Integer.fromint(99), p4specast.IntT.INSTANCE)
        deep_opt = OptV(deep_num)
        typ = deep_num.get_typ().opt_of()
        deep_opt = typ.make_opt_value(deep_num)
        inner_text = TextV("nested")
        inner_list = ListV.make([inner_text, deep_opt], None)

        outer_bool = BoolV.TRUE
        outer_tuple = TupleV.make([outer_bool, inner_list])

        # Find all subvalues to understand the structure
        subvalues = find_subvalues(outer_tuple)
        # Should be: tuple, bool, list, text, opt, num
        assert len(subvalues) == 6

        # Test selecting the deeply nested number (index 5)
        rng = MockRng([5, 0, 0, 15])  # select deep_num, mutate=0, then NumV strategy=0, delta=5
        mutated = mutate(outer_tuple, rng)

        # Navigate to the deeply nested value
        mutated_list = mutated._get_list(1)
        mutated_opt = mutated_list._get_list(1)
        mutated_num = mutated_opt.get_opt_value()

        assert mutated_num.value.toint() == 104  # 99 + 5

        # Verify other parts unchanged
        assert mutated._get_list(0) is outer_bool
        assert mutated_list._get_list(0) is inner_text

    def test_distribution_across_depths(self):
        # Test that mutation can reach all depths with real randomness
        # Use a simpler structure that won't have structure-changing mutations
        # Structure: tuple([bool, opt(bool)])
        inner_bool = BoolV.FALSE
        typ = p4specast.BoolT.INSTANCE.opt_of()
        inner_opt = typ.make_opt_value(inner_bool)
        outer_bool = BoolV.TRUE
        outer_tuple = TupleV.make([outer_bool, inner_opt], p4specast.TupleT([outer_bool.get_typ(), inner_opt.get_typ()]))

        rng = random.Random(42)
        ctx = make_context()
        mutation_locations = set()

        # Track which values get mutated over many iterations
        for _ in range(100):
            original_outer = outer_tuple._get_list(0).value
            original_inner = outer_tuple._get_list(1).get_opt_value().value

            mutated = mutate(outer_tuple, rng, ctx)

            new_outer = mutated._get_list(0).value
            new_inner = mutated._get_list(1).get_opt_value().value if mutated._get_list(1).get_opt_value() is not None else None

            # Determine what changed
            if original_outer != new_outer:
                mutation_locations.add("outer_bool")
            if new_inner is not None and original_inner != new_inner:
                mutation_locations.add("inner_bool")
            if mutated._get_list(1).get_opt_value() is None and original_inner is not None:
                mutation_locations.add("opt_to_none")

        # Should have mutated values at different locations
        assert len(mutation_locations) >= 2, "Should mutate values at different depths: %s" % mutation_locations

    def test_empty_containers(self):
        # Test mutation of empty containers
        empty_tuple = TupleV.make0()
        rng = MockRng([0, 0])  # Select the only subvalue (the container itself)
        mutated = mutate(empty_tuple, rng)
        # Empty tuple should remain unchanged when mutated
        assert mutated is empty_tuple

        typ = p4specast.BoolT.INSTANCE.list_of()
        empty_list = ListV.make0(typ)
        rng = MockRng([0, 0])  # Fresh MockRng for second test
        mutated = mutate(empty_list, rng)
        assert mutated is empty_list

    def test_opt_none_selection(self):
        # Test mutation when OptV contains None
        rng = MockRng([0, 0])  # Select the only subvalue (the OptV itself)

        typ = p4specast.BoolT.INSTANCE.opt_of()
        opt_none = typ.make_opt_value(None)
        mutated = mutate(opt_none, rng)

        # OptV with None should remain unchanged when mutated
        assert mutated is opt_none

    def test_generate_program(self):
        typ = p4specast.VarT(p4specast.Id('declaration', p4specast.NO_REGION), [])
        ctx = make_context()
        rng = MockRng([0, 0, 0, 0, 0, 0, 0, 0, 0])
        value = generate_value(typ, rng, ctx)
        # assert value.tostring() == "(ConstD (BoolT) '' (BoolE false))"
        assert value.tostring() == "(ConstD (BoolT) 'hello' (BoolE false))"  # string mutation is diabled

        typ = p4specast.VarT(p4specast.Id('declaration', p4specast.NO_REGION), [])
        ctx = make_context()
        for i in range(100):
            # "don't crash": smoke test
            value = generate_value(typ, random.Random(), ctx)
