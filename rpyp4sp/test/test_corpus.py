import pytest
import os
import tempfile
import shutil
from rpyp4sp import objects, p4specast, corpus, rpyjson
from rpyp4sp.test.test_mutatevalues import MockRng


class TestFuzzCorpus(object):
    """Test corpus management functionality."""

    def setup_method(self, method):
        """Setup for each test method."""
        self.temp_corpus_dir = tempfile.mkdtemp(prefix='corpus_test_')

    def teardown_method(self, method):
        """Cleanup for each test method."""
        shutil.rmtree(self.temp_corpus_dir, ignore_errors=True)

    def test_corpus_creation(self):
        """Test corpus creation and directory setup."""
        test_corpus = corpus.FuzzCorpus(self.temp_corpus_dir)
        assert os.path.exists(self.temp_corpus_dir)
        assert test_corpus.corpus_dir == self.temp_corpus_dir
        assert test_corpus.test_cases == []
        assert len(test_corpus.coverage_seen) == 0

    def test_add_test_case(self):
        """Test adding test cases to corpus."""
        test_corpus = corpus.FuzzCorpus(self.temp_corpus_dir)

        # Create a simple test value
        bool_val = objects.BoolV.TRUE

        # Add test case
        coverage_hash = "12345678"  # String hash (printable ASCII, no underscores)
        filename = test_corpus.add_test_case(bool_val, coverage_hash=coverage_hash, generation=0)

        assert filename == "test_cov12345678_gen0.json"
        assert len(test_corpus.test_cases) == 1
        assert coverage_hash in test_corpus.coverage_seen

        # Check file was created
        filepath = os.path.join(self.temp_corpus_dir, filename)
        assert os.path.exists(filepath)

        # Check file content
        with open(filepath, 'r') as f:
            content = f.read()
        assert '"BoolV"' in content
        assert 'true' in content

    def test_duplicate_coverage_rejected(self):
        """Test that duplicate coverage hashes are rejected."""
        test_corpus = corpus.FuzzCorpus(self.temp_corpus_dir)

        bool_val1 = objects.BoolV.TRUE
        bool_val2 = objects.BoolV.TRUE

        coverage_hash = "aabbccdd"

        # Add first test case
        filename1 = test_corpus.add_test_case(bool_val1, coverage_hash=coverage_hash, generation=0)
        assert filename1 is not None

        # Try to add second test case with same coverage hash
        filename2 = test_corpus.add_test_case(bool_val2, coverage_hash=coverage_hash, generation=1)
        assert filename2 is None  # Should be rejected

        # Only one test case should be in corpus
        assert len(test_corpus.test_cases) == 1

    def test_load_corpus(self):
        """Test loading corpus from disk."""
        test_corpus = corpus.FuzzCorpus(self.temp_corpus_dir)

        # Add several test cases
        bool_val1 = objects.BoolV.TRUE
        bool_val2 = objects.BoolV.FALSE

        hash1 = "1111"
        hash2 = "2222"

        test_corpus.add_test_case(bool_val1, coverage_hash=hash1, generation=0)
        test_corpus.add_test_case(bool_val2, coverage_hash=hash2, generation=1)

        # Create new corpus instance and load from disk
        fresh_corpus = corpus.FuzzCorpus(self.temp_corpus_dir)
        fresh_corpus.load_corpus()

        # Should have loaded both test cases
        assert len(fresh_corpus.test_cases) == 2
        assert hash1 in fresh_corpus.coverage_seen
        assert hash2 in fresh_corpus.coverage_seen

        # Check the loaded values
        loaded_values = [test_case.value for test_case in fresh_corpus.test_cases]
        assert any(isinstance(val, objects.BoolV) and val.value == True for val in loaded_values)
        assert any(isinstance(val, objects.BoolV) and val.value == False for val in loaded_values)

    def test_select_for_mutation(self):
        """Test selecting test cases for mutation."""
        test_corpus = corpus.FuzzCorpus(self.temp_corpus_dir)
        rng = MockRng([0])  # Always select first item

        # Empty corpus should raise exception
        try:
            test_corpus.select_for_mutation(rng)
            assert False, "Should have raised EmptyCorpusError"
        except corpus.EmptyCorpusError:
            pass  # Expected

        # Add test case and select it
        bool_val = objects.BoolV.TRUE
        hash_val = "deadbeef"
        test_corpus.add_test_case(bool_val, coverage_hash=hash_val, generation=0)

        result = test_corpus.select_for_mutation(rng)
        assert isinstance(result.value, objects.BoolV)
        assert result.coverage_hash == hash_val
        assert result.generation == 0
        assert result.filename == "test_covdeadbeef_gen0.json"

    def test_corpus_stats(self):
        """Test corpus statistics."""
        test_corpus = corpus.FuzzCorpus(self.temp_corpus_dir)

        # Empty corpus stats
        stats = test_corpus.get_stats()
        assert stats.total_cases == 0
        assert stats.unique_coverage == 0
        assert stats.seeds == 0
        assert stats.mutations == 0

        # Add some test cases
        bool_val = objects.BoolV.TRUE
        test_corpus.add_test_case(bool_val, coverage_hash="1111", generation=0)  # seed
        test_corpus.add_test_case(bool_val, coverage_hash="2222", generation=1)  # mutation
        test_corpus.add_test_case(bool_val, coverage_hash="3333", generation=2)  # mutation

        stats = test_corpus.get_stats()
        assert stats.total_cases == 3
        assert stats.unique_coverage == 3
        assert stats.max_generation == 2
        assert stats.seeds == 1
        assert stats.mutations == 2

    def test_filename_parsing(self):
        """Test that malformed filenames are handled gracefully."""
        test_corpus = corpus.FuzzCorpus(self.temp_corpus_dir)

        # Create some valid files
        bool_val = objects.BoolV.TRUE
        valid_hash = "12345678"
        test_corpus.add_test_case(bool_val, coverage_hash=valid_hash, generation=0)

        # Create some malformed files
        bad_files = [
            "not_a_test_file.json",
            "test_invalid.json",
            "test_cov_gen.json",
            "test_cov12345.json",
            "random.txt"
        ]

        for bad_file in bad_files:
            filepath = os.path.join(self.temp_corpus_dir, bad_file)
            with open(filepath, 'w') as f:
                f.write('{"dummy": "data"}')

        # Load corpus - should only load valid files
        fresh_corpus = corpus.FuzzCorpus(self.temp_corpus_dir)
        fresh_corpus.load_corpus()

        assert len(fresh_corpus.test_cases) == 1  # Only the valid one
        assert valid_hash in fresh_corpus.coverage_seen

    def test_generation_handling(self):
        """Test that generation numbers work correctly."""
        test_corpus = corpus.FuzzCorpus(self.temp_corpus_dir)

        # Add seed (generation 0)
        seed_val = objects.BoolV.TRUE
        filename1 = test_corpus.add_test_case(seed_val, coverage_hash="0064", generation=0)  # was 100
        assert "gen0" in filename1

        # Add mutation (generation 3)
        mut_val = objects.BoolV.FALSE
        filename2 = test_corpus.add_test_case(mut_val, coverage_hash="00c8", generation=3)  # was 200
        assert "gen3" in filename2

        # Verify they load correctly
        fresh_corpus = corpus.FuzzCorpus(self.temp_corpus_dir)
        fresh_corpus.load_corpus()

        generations = [test_case.generation for test_case in fresh_corpus.test_cases]
        assert 0 in generations
        assert 3 in generations

    def test_testcase_from_file_valid(self):
        """Test TestCase.from_file with valid files."""
        # Create a test case file manually
        bool_val = objects.BoolV.TRUE
        json_result = bool_val.tojson()
        json_content = rpyjson.dumps(json_result)

        filename = "test_cov12345abc_gen3.json"
        filepath = os.path.join(self.temp_corpus_dir, filename)
        with open(filepath, 'w') as f:
            f.write(json_content)

        # Load using from_file
        test_case = corpus.TestCase.from_file(filename, self.temp_corpus_dir)

        assert test_case is not None
        assert test_case.coverage_hash == "12345abc"
        assert test_case.generation == 3
        assert test_case.filename == filename
        assert isinstance(test_case.value, objects.BoolV)
        assert test_case.value.value == True

    def test_testcase_from_file_malformed_filenames(self):
        """Test TestCase.from_file with malformed filenames."""
        # Test various malformed filenames
        malformed_names = [
            "not_a_test_file.json",
            "test_invalid.json",
            "test_cov_gen.json",
            "test_cov12345.json",
            "test_cov12345_gen.json",
            "test_cov12345_genX.json",
            "test_cov12345_gen3.txt",
            "random.txt",
            "test_cov_gen3.json",  # Missing hash
            "test_cov12_34_gen3.json",  # Hash with underscore
        ]

        for bad_filename in malformed_names:
            filepath = os.path.join(self.temp_corpus_dir, bad_filename)
            with open(filepath, 'w') as f:
                f.write('{"dummy": "data"}')

            result = corpus.TestCase.from_file(bad_filename, self.temp_corpus_dir)
            assert result is None, "Should reject malformed filename: %s" % bad_filename

    def test_testcase_from_file_corrupted_json(self):
        """Test TestCase.from_file with corrupted JSON files."""
        filename = "test_cov999_gen0.json"
        filepath = os.path.join(self.temp_corpus_dir, filename)

        # Write invalid JSON
        with open(filepath, 'w') as f:
            f.write('{"invalid": json content}')  # Missing quotes, invalid syntax

        result = corpus.TestCase.from_file(filename, self.temp_corpus_dir)
        assert result is None

    def test_testcase_from_file_missing_file(self):
        """Test TestCase.from_file with non-existent file."""
        result = corpus.TestCase.from_file("test_covdoesnotexist_gen0.json", self.temp_corpus_dir)
        assert result is None

    def test_testcase_from_file_different_generations(self):
        """Test TestCase.from_file with different generation numbers."""
        bool_val = objects.BoolV.FALSE
        json_content = rpyjson.dumps(bool_val.tojson())

        test_cases = [
            ("test_covabc123_gen0.json", 0),  # Seed
            ("test_covabc456_gen1.json", 1),  # First generation
            ("test_covabc789_gen999.json", 999),  # High generation
        ]

        for filename, expected_gen in test_cases:
            filepath = os.path.join(self.temp_corpus_dir, filename)
            with open(filepath, 'w') as f:
                f.write(json_content)

            test_case = corpus.TestCase.from_file(filename, self.temp_corpus_dir)
            assert test_case is not None
            assert test_case.generation == expected_gen

    def test_testcase_from_file_different_coverage_hashes(self):
        """Test TestCase.from_file with different coverage hash formats."""
        bool_val = objects.BoolV.TRUE
        json_content = rpyjson.dumps(bool_val.tojson())

        valid_hashes = [
            "a1b2c3",
            "deadbeef",
            "123456789",
            "mixedCASE123",
            "special!@#$%",  # Special chars are allowed (printable ASCII)
        ]

        for coverage_hash in valid_hashes:
            filename = "test_cov%s_gen0.json" % coverage_hash
            filepath = os.path.join(self.temp_corpus_dir, filename)
            with open(filepath, 'w') as f:
                f.write(json_content)

            test_case = corpus.TestCase.from_file(filename, self.temp_corpus_dir)
            assert test_case is not None
            assert test_case.coverage_hash == coverage_hash

    def test_select_for_mutation_weighted(self):
        """Test weighted selection based on coverage and generation."""
        test_corpus = corpus.FuzzCorpus(self.temp_corpus_dir)

        # Add test cases with different generations and coverage
        bool_val1 = objects.BoolV.TRUE
        bool_val2 = objects.BoolV.FALSE
        bool_val3 = objects.BoolV.TRUE

        # Add cases: older generation, unique coverage
        test_corpus.add_test_case(bool_val1, coverage_hash="old", generation=0)
        # Add cases: newer generation, unique coverage
        test_corpus.add_test_case(bool_val2, coverage_hash="new", generation=2)
        # Add cases: newer generation, same coverage as first (less rare)
        test_corpus.add_test_case(bool_val3, coverage_hash="old", generation=1)

        # After adding 3rd case, "old" coverage has frequency=2, "new" has frequency=1
        # Expected weights (roughly):
        # Case 0: recency=(1+0/2)=1.0, rarity=1/2=0.5 → weight=0.5
        # Case 1: recency=(1+2/2)=2.0, rarity=1/1=1.0 → weight=2.0 (highest)
        # Case 2: recency=(1+1/2)=1.5, rarity=1/2=0.5 → weight=0.75

        # Use MockRng to get deterministic selection
        # With weights scaled by 1000: [500, 2000, 750]
        # Total = 3250, cumulative = [500, 2500, 3250]
        # Target 0-499 → Case 0, Target 500-2499 → Case 1, Target 2500+ → Case 2

        rng = MockRng([0])  # Should select first case (old, gen 0)
        result = test_corpus.select_for_mutation_weighted(rng)
        assert result.coverage_hash == "old"
        assert result.generation == 0

        rng = MockRng([1000])  # Should select second case (new, gen 2) - highest weight
        result = test_corpus.select_for_mutation_weighted(rng)
        assert result.coverage_hash == "new"
        assert result.generation == 2

    def test_weighted_selection_empty_corpus(self):
        """Test weighted selection with empty corpus."""
        test_corpus = corpus.FuzzCorpus(self.temp_corpus_dir)
        rng = MockRng([0])

        try:
            test_corpus.select_for_mutation_weighted(rng)
            assert False, "Should have raised EmptyCorpusError"
        except corpus.EmptyCorpusError:
            pass

    def test_duplicate_coverage_handling(self):
        """Test that duplicate coverage is properly handled."""
        test_corpus = corpus.FuzzCorpus(self.temp_corpus_dir)

        bool_val = objects.BoolV.TRUE

        # Add cases with same coverage hash
        filename1 = test_corpus.add_test_case(bool_val, coverage_hash="common", generation=0)
        filename2 = test_corpus.add_test_case(bool_val, coverage_hash="rare", generation=1)
        filename3 = test_corpus.add_test_case(bool_val, coverage_hash="common", generation=2)

        # First occurrence saved, duplicate not saved
        assert filename1 is not None
        assert filename2 is not None
        assert filename3 is None

        # Check coverage tracking - duplicates increment count
        assert test_corpus.coverage_seen["common"] == 2
        assert test_corpus.coverage_seen["rare"] == 1

        # Only unique coverage cases are stored
        assert len(test_corpus.test_cases) == 2

        # Test corpus loading - only unique coverage saved to disk
        fresh_corpus = corpus.FuzzCorpus(self.temp_corpus_dir)
        fresh_corpus.load_corpus()

        # After loading, each unique coverage hash has count 1
        assert fresh_corpus.coverage_seen["common"] == 1
        assert fresh_corpus.coverage_seen["rare"] == 1

        # Both test cases loaded from disk
        assert len(fresh_corpus.test_cases) == 2


class TestWeightedRandomChoice(object):
    """Test weighted random selection functionality."""

    def test_weighted_choice_basic(self):
        """Test basic weighted random choice."""
        items = ['a', 'b', 'c']
        weights = [1, 2, 3]

        # MockRng(0) should select first bucket (weight 1, target 0)
        rng = MockRng([0])
        result = corpus.weighted_random_choice(items, weights, rng)
        assert result == 'a'

        # MockRng(1) should select second bucket (weight 2, target 1)
        rng = MockRng([1])
        result = corpus.weighted_random_choice(items, weights, rng)
        assert result == 'b'

        # MockRng(3) should select third bucket (weight 3, target 3)
        rng = MockRng([3])
        result = corpus.weighted_random_choice(items, weights, rng)
        assert result == 'c'

        # MockRng(5) should select third bucket (weight 3, target 5 = last)
        rng = MockRng([5])
        result = corpus.weighted_random_choice(items, weights, rng)
        assert result == 'c'

    def test_weighted_choice_equal_weights(self):
        """Test weighted choice with equal weights (should be uniform)."""
        items = ['x', 'y', 'z']
        weights = [1, 1, 1]

        rng = MockRng([0])
        result = corpus.weighted_random_choice(items, weights, rng)
        assert result == 'x'

        rng = MockRng([1])
        result = corpus.weighted_random_choice(items, weights, rng)
        assert result == 'y'

        rng = MockRng([2])
        result = corpus.weighted_random_choice(items, weights, rng)
        assert result == 'z'

    def test_weighted_choice_zero_weights(self):
        """Test weighted choice with some zero weights."""
        items = ['skip', 'pick', 'skip2']
        weights = [0, 5, 0]

        # All targets should select the only non-zero weight item
        for target in [0, 1, 2, 3, 4]:
            rng = MockRng([target])
            result = corpus.weighted_random_choice(items, weights, rng)
            assert result == 'pick'

    def test_weighted_choice_single_item(self):
        """Test weighted choice with single item."""
        items = ['only']
        weights = [42]

        rng = MockRng([0])
        result = corpus.weighted_random_choice(items, weights, rng)
        assert result == 'only'

        rng = MockRng([41])  # Last valid target
        result = corpus.weighted_random_choice(items, weights, rng)
        assert result == 'only'

    def test_weighted_choice_large_weights(self):
        """Test weighted choice with large weight differences."""
        items = ['rare', 'common']
        weights = [1, 1000]

        # Target 0 should select rare item
        rng = MockRng([0])
        result = corpus.weighted_random_choice(items, weights, rng)
        assert result == 'rare'

        # Target 1+ should select common item
        rng = MockRng([1])
        result = corpus.weighted_random_choice(items, weights, rng)
        assert result == 'common'

        rng = MockRng([500])
        result = corpus.weighted_random_choice(items, weights, rng)
        assert result == 'common'

    def test_weighted_choice_edge_cases(self):
        """Test weighted choice error conditions."""
        items = ['a', 'b']
        weights = [1, 2]
        rng = MockRng([0])

        # Mismatched lengths
        try:
            corpus.weighted_random_choice(['a'], [1, 2], rng)
            assert False, "Should raise assertion error"
        except AssertionError:
            pass

        # Empty lists
        try:
            corpus.weighted_random_choice([], [], rng)
            assert False, "Should raise assertion error"
        except AssertionError:
            pass

        # Negative weights
        try:
            corpus.weighted_random_choice(['a'], [-1], rng)
            assert False, "Should raise assertion error"
        except AssertionError:
            pass

        # All zero weights
        try:
            corpus.weighted_random_choice(['a', 'b'], [0, 0], rng)
            assert False, "Should raise assertion error"
        except AssertionError:
            pass
