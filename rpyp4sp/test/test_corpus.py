import pytest
import os
import tempfile
import shutil
from rpyp4sp import objects, p4specast, corpus
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
        bool_val = objects.BoolV(True, typ=p4specast.BoolT.INSTANCE, vid=42)
        
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
        
        bool_val1 = objects.BoolV(True, typ=p4specast.BoolT.INSTANCE, vid=42)
        bool_val2 = objects.BoolV(False, typ=p4specast.BoolT.INSTANCE, vid=43)
        
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
        bool_val1 = objects.BoolV(True, typ=p4specast.BoolT.INSTANCE, vid=42)
        bool_val2 = objects.BoolV(False, typ=p4specast.BoolT.INSTANCE, vid=43)
        
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
        loaded_values = [val for val, _, _, _ in fresh_corpus.test_cases]
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
        bool_val = objects.BoolV(True, typ=p4specast.BoolT.INSTANCE, vid=42)
        hash_val = "deadbeef"
        test_corpus.add_test_case(bool_val, coverage_hash=hash_val, generation=0)
        
        result = test_corpus.select_for_mutation(rng)
        selected_val, coverage_hash, generation, filename = result
        assert isinstance(selected_val, objects.BoolV)
        assert coverage_hash == hash_val
        assert generation == 0
        assert filename == "test_covdeadbeef_gen0.json"
    
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
        bool_val = objects.BoolV(True, typ=p4specast.BoolT.INSTANCE, vid=42)
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
        bool_val = objects.BoolV(True, typ=p4specast.BoolT.INSTANCE, vid=42)
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
        seed_val = objects.BoolV(True, typ=p4specast.BoolT.INSTANCE, vid=1)
        filename1 = test_corpus.add_test_case(seed_val, coverage_hash="0064", generation=0)  # was 100
        assert "gen0" in filename1
        
        # Add mutation (generation 3)  
        mut_val = objects.BoolV(False, typ=p4specast.BoolT.INSTANCE, vid=2)
        filename2 = test_corpus.add_test_case(mut_val, coverage_hash="00c8", generation=3)  # was 200
        assert "gen3" in filename2
        
        # Verify they load correctly
        fresh_corpus = corpus.FuzzCorpus(self.temp_corpus_dir)
        fresh_corpus.load_corpus()
        
        generations = [gen for _, _, gen, _ in fresh_corpus.test_cases]
        assert 0 in generations
        assert 3 in generations
    
    def test_corpus_minimization_sorting(self):
        """Test that corpus minimization correctly sorts by generation."""
        test_corpus = corpus.FuzzCorpus(self.temp_corpus_dir)
        
        # Add test cases with different generations (out of order)
        bool_val = objects.BoolV(True, typ=p4specast.BoolT.INSTANCE, vid=1)
        test_corpus.add_test_case(bool_val, coverage_hash="gen1", generation=1)  # Gen 1
        test_corpus.add_test_case(bool_val, coverage_hash="gen5", generation=5)  # Gen 5  
        test_corpus.add_test_case(bool_val, coverage_hash="gen0", generation=0)  # Gen 0 (seed)
        test_corpus.add_test_case(bool_val, coverage_hash="gen3", generation=3)  # Gen 3
        test_corpus.add_test_case(bool_val, coverage_hash="gen2", generation=2)  # Gen 2
        
        # Minimize to keep only 3 cases (should keep highest generations)
        test_corpus.minimize_corpus(target_size=3)
        
        # Check that we kept the 3 highest generations (5, 3, 2)
        assert len(test_corpus.test_cases) == 3
        generations = [gen for _, _, gen, _ in test_corpus.test_cases]
        assert 5 in generations
        assert 3 in generations  
        assert 2 in generations
        # Should not keep gen 1 or 0
        assert 1 not in generations
        assert 0 not in generations