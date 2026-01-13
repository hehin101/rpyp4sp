import os
from rpyp4sp import objects, rpyjson


def basename(p):
    i = p.rfind('/') + 1
    assert i >= 0
    return p[i:]


def weighted_random_choice(items, weights, rng):
    """Select a random item based on weights.

    Args:
        items: List of items to choose from
        weights: List of weights (same length as items)
        rng: Random number generator with randint method

    Returns:
        Selected item from the list

    Raises:
        AssertionError: If items and weights have different lengths or weights are invalid
    """
    assert len(items) == len(weights), "Items and weights must have same length"
    assert len(items) > 0, "Cannot choose from empty list"

    # Calculate total weight
    total_weight = 0
    for weight in weights:
        assert weight >= 0, "Weights must be non-negative"
        total_weight += weight

    assert total_weight > 0, "Total weight must be positive"

    # Generate random number in range [0, total_weight)
    target = rng.randint(0, total_weight - 1)

    # Find the item corresponding to this weight
    current_weight = 0
    for i, weight in enumerate(weights):
        current_weight += weight
        if target < current_weight:
            return items[i]

    # Should never reach here, but return last item as fallback
    return items[-1]


class EmptyCorpusError(Exception):
    """Raised when trying to select from an empty corpus."""
    pass


class TestCase(object):
    """Represents a single test case in the fuzzing corpus."""

    def __init__(self, value, coverage_hash, generation, filename):
        self.value = value  # BaseV object
        self.coverage_hash = coverage_hash  # str
        self.generation = generation  # int
        self.filename = filename  # str
        self.descendants_produced = 0  # int - count of new test cases produced from this one

    @staticmethod
    def from_file(filename, corpus_dir):
        """Load a TestCase from a corpus file.

        Args:
            filename: Name of the file (e.g., "test_cov1234_gen0.json")
            corpus_dir: Directory containing the corpus files

        Returns:
            TestCase object or None if file cannot be loaded
        """
        from rpyp4sp import objects, rpyjson

        # Parse filename to extract coverage hash and generation
        # Expected format: test_cov{coverage_hash}_gen{generation}.json
        if not (filename.startswith('test_cov') and filename.endswith('.json') and '_gen' in filename):
            return None  # Skip malformed filenames

        # Extract coverage hash: between 'test_cov' and '_gen'
        start_pos = len('test_cov')
        gen_pos = filename.find('_gen')
        if gen_pos == -1 or gen_pos <= start_pos:
            return None

        coverage_hash = filename[start_pos:gen_pos]

        # Extract generation: between '_gen' and '.json'
        gen_start = gen_pos + len('_gen')
        json_pos = filename.find('.json')
        if json_pos == -1 or json_pos <= gen_start:
            return None

        gen_str = filename[gen_start:json_pos]
        try:
            generation = int(gen_str)
        except ValueError:
            return None  # Skip if generation is not a valid integer

        # Validate coverage hash format
        if not coverage_hash or '_' in coverage_hash:
            return None  # Skip invalid coverage hash

        try:
            # Load and parse JSON
            filepath = os.path.join(corpus_dir, filename)
            with open(filepath, 'r') as f:
                json_content = f.read()

            json_parsed = rpyjson.loads(json_content)
            value = objects.BaseV.fromjson(json_parsed)

            return TestCase(value, coverage_hash, generation, filename)

        except (IOError, ValueError, KeyError) as e:
            # Skip corrupted files but don't crash
            print("Warning: Could not load %s: %s" % (filename, str(e)))
            return None


class CorpusStats(object):
    """Statistics about the fuzzing corpus."""

    def __init__(self, total_cases=0, unique_coverage=0, max_generation=0,
                 seeds=0, mutations=0):
        self.total_cases = total_cases
        self.unique_coverage = unique_coverage
        self.max_generation = max_generation
        self.seeds = seeds
        self.mutations = mutations


class FuzzCorpus(object):
    """Manages a corpus of test cases for greybox fuzzing.

    Test cases are stored as JSON files with coverage hashes encoded in filenames:
    - Format: test_cov{hash_hex}_gen{generation}.json
    - Example: test_cov1a2b3c4d_gen0.json (seed), test_covabcdef01_gen3.json (mutated)
    """

    def __init__(self, corpus_dir):
        self.corpus_dir = corpus_dir
        self.test_cases = []  # List of TestCase objects
        self.coverage_seen = {}  # Dict mapping coverage_hash (str) -> count (int)

        # Create corpus directory if it doesn't exist (assume non-recursive)
        if not os.path.exists(corpus_dir):
            os.mkdir(corpus_dir)

    def add_test_case(self, value, coverage_hash, generation=0, parent_filename=None):
        """Add a new test case to the corpus.

        Args:
            value: BaseV object to store
            coverage_hash: str coverage hash (printable ASCII, no underscores)
            generation: Generation number (0 for seeds, >0 for mutations)
            parent_filename: Filename of parent test case (for mutations)

        Returns:
            str: Filename of saved test case, or None if not saved (duplicate coverage)
        """
        # Assert coverage_hash constraints for filename safety
        assert isinstance(coverage_hash, str), "coverage_hash must be a string"
        assert len(coverage_hash) > 0, "coverage_hash cannot be empty"
        assert '_' not in coverage_hash, "coverage_hash cannot contain underscores"

        # Check that all characters are printable ASCII
        for c in coverage_hash:
            assert 32 <= ord(c) <= 126, "coverage_hash must be printable ASCII"

        # Skip if we've already seen this coverage (only save first occurrence)
        if coverage_hash in self.coverage_seen:
            self.coverage_seen[coverage_hash] += 1
            return None

        # Use coverage hash directly in filename
        filename = "test_cov%s_gen%d.json" % (coverage_hash, generation)
        filepath = os.path.join(self.corpus_dir, filename)

        # Serialize value to JSON
        json_result = value.tojson()
        json_content = rpyjson.dumps(json_result)

        # Write to file
        with open(filepath, 'w') as f:
            f.write(json_content)

        # Add to memory structures
        test_case = TestCase(value, coverage_hash, generation, filename)
        self.test_cases.append(test_case)
        self.coverage_seen[coverage_hash] = 1  # First time seeing this coverage

        return filename


    def load_corpus(self):
        """Load all test cases from the corpus directory."""
        self.test_cases = []
        self.coverage_seen = {}

        # List all files in corpus directory and filter for test cases
        try:
            all_files = os.listdir(self.corpus_dir)
        except OSError:
            # Directory doesn't exist or can't be read
            return

        for filename in all_files:
            test_case = TestCase.from_file(filename, self.corpus_dir)
            if test_case is not None:
                self.test_cases.append(test_case)
                self.coverage_seen[test_case.coverage_hash] = 1  # Set count to 1 for loaded cases

    def select_for_mutation(self, rng):
        """Select a test case for mutation.

        Args:
            rng: Random number generator

        Returns:
            TestCase: Selected test case object

        Raises:
            EmptyCorpusError: If the corpus is empty
        """
        if not self.test_cases:
            raise EmptyCorpusError("Cannot select from empty corpus")

        # Simple random selection for now
        # TODO: Implement smarter selection (e.g., favor recent discoveries)
        index = rng.randint(0, len(self.test_cases) - 1)
        return self.test_cases[index]

    def select_for_mutation_weighted(self, rng):
        """Select a test case for mutation using coverage-based weighting.

        Args:
            rng: Random number generator

        Returns:
            TestCase: Selected test case object

        Raises:
            EmptyCorpusError: If the corpus is empty
        """
        if not self.test_cases:
            raise EmptyCorpusError("Cannot select from empty corpus")

        # Calculate weights based on recency and rarity
        weights = []
        max_generation = 0
        for test_case in self.test_cases:
            if test_case.generation > max_generation:
                max_generation = test_case.generation

        for test_case in self.test_cases:
            # Recency bonus: newer generations get higher weight
            recency_weight = 1.0 + (test_case.generation / max(max_generation, 1.0))

            # Rarity bonus: less frequent coverage gets higher weight
            frequency = self.coverage_seen.get(test_case.coverage_hash, 1)
            rarity_weight = 1.0 / frequency

            # Productivity bonus: test cases that produced more descendants get higher weight
            productivity_weight = 1.0 + test_case.descendants_produced

            # Combined weight
            total_weight = recency_weight * rarity_weight * productivity_weight
            weights.append(int(total_weight * 1000))  # Scale and convert to int for randint

        return weighted_random_choice(self.test_cases, weights, rng)

    def get_stats(self):
        """Get corpus statistics.

        Returns:
            CorpusStats: Statistics about the corpus
        """
        if not self.test_cases:
            return CorpusStats()

        generations = [test_case.generation for test_case in self.test_cases]
        seeds = 0
        max_gen = 0
        for gen in generations:
            if gen == 0:
                seeds += 1
            if gen > max_gen:
                max_gen = gen

        return CorpusStats(
            total_cases=len(self.test_cases),
            unique_coverage=len(self.coverage_seen),
            max_generation=max_gen,
            seeds=seeds,
            mutations=len(self.test_cases) - seeds
        )
