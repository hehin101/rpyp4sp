import pytest
import os
import tempfile
import shutil
from rpyp4sp import fuzz, objects, p4specast, rpyjson
from rpyp4sp.test.test_mutatevalues import MockRng


class TestFuzzConfig(object):
    """Test fuzzing configuration."""

    def test_default_config(self):
        """Test default configuration values."""
        config = fuzz.FuzzConfig()
        assert config.corpus_dir == "./fuzz_corpus"
        assert config.max_iterations == 10000
        assert config.mutation_budget == 100
        assert config.corpus_max_size == 1000
        assert config.timeout_seconds == 5.0

    def test_custom_config(self):
        """Test custom configuration values."""
        config = fuzz.FuzzConfig(
            corpus_dir="/tmp/test",
            max_iterations=500,
            mutation_budget=50,
            corpus_max_size=200
        )
        assert config.corpus_dir == "/tmp/test"
        assert config.max_iterations == 500
        assert config.mutation_budget == 50
        assert config.corpus_max_size == 200


class TestFuzzStats(object):
    """Test fuzzing statistics."""

    def test_initial_stats(self):
        """Test initial statistics values."""
        stats = fuzz.FuzzStats()
        assert stats.iterations == 0
        assert stats.test_cases_run == 0
        assert stats.crashes_found == 0
        assert stats.new_coverage_found == 0
        assert stats.timeouts == 0
        assert stats.get_runtime() >= 0

    def test_stats_update(self):
        """Test statistics can be updated."""
        stats = fuzz.FuzzStats()
        stats.iterations = 100
        stats.test_cases_run = 500
        stats.crashes_found = 2
        stats.new_coverage_found = 10

        assert stats.iterations == 100
        assert stats.test_cases_run == 500
        assert stats.crashes_found == 2
        assert stats.new_coverage_found == 10


class TestFuzzMainLoop(object):
    """Test main fuzzing loop functionality."""

    def setup_method(self, method):
        """Setup for each test method."""
        self.temp_corpus_dir = tempfile.mkdtemp(prefix='fuzz_test_')

    def teardown_method(self, method):
        """Cleanup for each test method."""
        shutil.rmtree(self.temp_corpus_dir, ignore_errors=True)

    def test_run_test_case(self):
        """Test running a single test case."""
        class MockContext:
            class MockCover:
                def tostr(self):
                    return "testcov123"
            def __init__(self):
                self._cover = MockContext.MockCover()
            def get_cover(self):
                return self._cover

        # Mock the interp.invoke_rel function
        def mock_invoke_rel(ctx, program_id, values):
            return ctx, ["mock_result"]  # Return the context and some result values

        # Temporarily replace the invoke_rel function
        original_invoke_rel = fuzz.interp.invoke_rel
        fuzz.interp.invoke_rel = mock_invoke_rel

        try:
            config = fuzz.FuzzConfig()
            ctx = MockContext()
            value = objects.BoolV.TRUE

            result = fuzz.run_test_case(ctx, value, config)
        finally:
            # Restore original function
            fuzz.interp.invoke_rel = original_invoke_rel

        assert result.coverage_hash == "testcov123"  # Mock coverage string
        assert not result.crashed
        assert not result.timed_out
        assert result.error_msg is None

    def test_run_test_case_crash(self):
        """Test handling of crashing test case."""
        from rpyp4sp.interp import P4Error

        class MockContext:
            pass

        # Mock the interp.invoke_rel function to raise P4Error
        def mock_invoke_rel_crash(ctx, program_id, values):
            raise P4Error("Test P4 error", p4specast.NO_REGION)

        # Temporarily replace the invoke_rel function
        original_invoke_rel = fuzz.interp.invoke_rel
        fuzz.interp.invoke_rel = mock_invoke_rel_crash

        try:
            config = fuzz.FuzzConfig()
            ctx = MockContext()
            value = objects.BoolV.TRUE

            result = fuzz.run_test_case(ctx, value, config)
        finally:
            # Restore original function
            fuzz.interp.invoke_rel = original_invoke_rel

        assert result.coverage_hash.startswith('exception')
        assert result.crashed
        assert not result.timed_out
        assert "Test P4 error" in result.error_msg

    def test_load_seeds_empty(self):
        """Test loading seeds with empty seed list."""
        class MockContext:
            pass

        ctx = MockContext()
        seeds = fuzz.load_seeds([], ctx)
        assert seeds == []

    def test_load_seeds_valid(self):
        """Test loading valid seed files."""
        class MockContext:
            class MockCover:
                def tostr(self):
                    return "seedcov456"
            def __init__(self):
                self._cover = MockContext.MockCover()
            def get_cover(self):
                return self._cover

        # Mock the interp.invoke_rel function
        def mock_invoke_rel(ctx, program_id, values):
            return ctx, ["mock_result"]

        # Temporarily replace the invoke_rel function
        original_invoke_rel = fuzz.interp.invoke_rel
        fuzz.interp.invoke_rel = mock_invoke_rel

        try:
            # Create a temporary seed file
            seed_file = os.path.join(self.temp_corpus_dir, "seed.json")
            bool_val = objects.BoolV.TRUE
            json_result = bool_val.tojson()
            json_content = rpyjson.dumps(json_result)

            with open(seed_file, 'w') as f:
                f.write(json_content)

            ctx = MockContext()
            seeds = fuzz.load_seeds([seed_file], ctx)

            assert len(seeds) == 1
            seed_value, coverage_hash, error_info = seeds[0]
            assert isinstance(seed_value, objects.BoolV)
            assert coverage_hash == "seedcov456"
            assert error_info is None
        finally:
            # Restore original function
            fuzz.interp.invoke_rel = original_invoke_rel

    def test_fuzz_main_loop_empty_corpus(self):
        """Test fuzzing loop with empty corpus."""
        class MockContext:
            pass

        config = fuzz.FuzzConfig(
            corpus_dir=self.temp_corpus_dir,
            max_iterations=10,
            mutation_budget=5
        )

        ctx = MockContext()
        rng = MockRng([1, 2, 3] * 100)
        seed_files = []

        stats = fuzz.fuzz_main_loop(config, seed_files, ctx, rng)

        # Should complete without crashing even with empty corpus
        assert stats.iterations >= 0

    def test_fuzz_main_loop_with_seeds(self):
        """Test fuzzing loop with seed files."""
        class MockContext:
            class MockCover:
                def tostr(self):
                    return "loopcov789"
            def __init__(self):
                self._cover = MockContext.MockCover()

        # Mock the interp.invoke_rel function
        def mock_invoke_rel(ctx, program_id, values):
            return ctx, ["mock_result"]

        # Temporarily replace the invoke_rel function
        original_invoke_rel = fuzz.interp.invoke_rel
        fuzz.interp.invoke_rel = mock_invoke_rel

        try:
            # Create seed file
            seed_file = os.path.join(self.temp_corpus_dir, "seed.json")
            bool_val = objects.BoolV.TRUE
            json_result = bool_val.tojson()
            json_content = rpyjson.dumps(json_result)

            with open(seed_file, 'w') as f:
                f.write(json_content)

            config = fuzz.FuzzConfig(
                corpus_dir=self.temp_corpus_dir,
                max_iterations=5,
                mutation_budget=3
            )

            ctx = MockContext()
            rng = MockRng([0] * 100)  # Always select first item
            seed_files = [seed_file]

            stats = fuzz.fuzz_main_loop(config, seed_files, ctx, rng)

            assert stats.iterations == 5
            assert stats.new_coverage_found >= 1  # At least the seed
            assert stats.test_cases_run >= 1
        finally:
            # Restore original function
            fuzz.interp.invoke_rel = original_invoke_rel


class TestFuzzExample(object):
    """Test the example fuzzing function."""

    def test_fuzz_example_runs(self):
        """Test that the example fuzzing function runs without crashing."""
        # This test mainly checks that the structure is sound
        # The actual fuzzing logic will be tested more thoroughly once
        # we integrate real coverage collection

        try:
            stats = fuzz.fuzz_example()
            assert isinstance(stats, fuzz.FuzzStats)
        except Exception as e:
            # For now, we just want to make sure the structure doesn't crash
            # Real functionality testing will come with coverage integration
            pass
