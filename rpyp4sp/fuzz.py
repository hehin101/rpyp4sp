"""Greybox fuzzing main loop for P4 interpreter."""
from __future__ import print_function

import os
import sys
import time
from rpython.rlib import objectmodel, rarithmetic
from rpython.rlib.rrandom import Random
from rpyp4sp import objects, mutatevalues, corpus, interp, rpyjson, p4specast, context
from rpyp4sp.interp import P4Error
from rpyp4sp.corpus import EmptyCorpusError


class FuzzRng(Random):
    """RPython-compatible random number generator for fuzzing."""

    def __init__(self, seed=42):
        Random.__init__(self, seed)

    def randint(self, min_val, max_val):
        """Return random integer in range [min_val, max_val]."""
        if max_val == min_val:
            return min_val
        range_size = max_val - min_val + 1
        return min_val + int(rarithmetic.intmask(self.genrand32()) % range_size)


class FuzzConfig(object):
    """Configuration for fuzzing session."""

    def __init__(self, corpus_dir="./fuzz_corpus", max_iterations=10000,
                 mutation_budget=100, corpus_max_size=1000):
        self.corpus_dir = corpus_dir
        self.max_iterations = max_iterations
        self.mutation_budget = mutation_budget  # Max mutations per iteration
        self.corpus_max_size = corpus_max_size
        self.timeout_seconds = 5.0  # Per test case execution timeout


class TestResult(object):
    """Result of running a single test case."""

    def __init__(self, coverage_hash, crashed=False, timed_out=False, error_msg=None):
        self.coverage_hash = coverage_hash
        self.crashed = crashed
        self.timed_out = timed_out
        self.error_msg = error_msg
        self.ctx = None


class FuzzStats(object):
    """Statistics tracking for fuzzing session."""

    def __init__(self):
        self.iterations = 0
        self.test_cases_run = 0
        self.crashes_found = 0
        self.new_coverage_found = 0
        self.timeouts = 0
        self.start_time = time.time()
        self.seen_error_messages = {}  # Dict mapping error message -> count
        self.seen_coverage = {'error hit': {}, 'error miss': {}, 'hit': {}, 'miss': {}}  # kind -> key -> count

    def get_runtime(self):
        return time.time() - self.start_time

    def is_new_error(self, error_msg):
        """Check if this is a new error message and record it."""
        if error_msg in self.seen_error_messages:
            self.seen_error_messages[error_msg] += 1
            return False
        else:
            self.seen_error_messages[error_msg] = 1
            return True

    def if_new_return_total_size(self, pid, kind):
        d = self.seen_coverage[kind]
        if pid in d:
            d[pid] += 1
            return 0
        else:
            d[pid] = 1
            return len(d)


    def print_stats(self):
        runtime = self.get_runtime()
        unique_crashes = len(self.seen_error_messages)
        print("=== Fuzzing Statistics ===")
        print("Runtime: %ss" % runtime)
        print("Iterations: %d" % self.iterations)
        print("Test cases run: %d" % self.test_cases_run)
        print("Rate: %s cases/sec" % (self.test_cases_run / max(runtime, 0.1)))
        print("New coverage: %d" % self.new_coverage_found)
        print("Crashes: %d (%d unique)" % (self.crashes_found, unique_crashes))
        print("Timeouts: %d" % self.timeouts)


def run_test_case(ctx, value, config):
    """Run a single test case and collect coverage results.

    Args:
        ctx: Interpreter context instance
        value: BaseV value to test
        config: FuzzConfig instance

    Returns:
        TestResult: Result object containing coverage, crash status, and error info
    """
    # TODO: Implement timeout handling

    try:
        # Run the interpreter with proper coverage collection
        resctx, values = interp.invoke_rel(ctx, p4specast.Id("Program_ok", p4specast.NO_REGION), [value])

        # Extract coverage from result context
        if resctx is not None:
            coverage_hash = resctx.get_cover().tostr()
        else:
            coverage_hash = 'failed'

        res = TestResult(coverage_hash)
        res.ctx = resctx
        return res


    except P4Error as e:
        # P4 execution error (not necessarily a crash)
        error_msg = str(e.msg)
        coverage_hash = 'exception' + hex(objectmodel.compute_hash(e.msg))[2:]
        if e.ctx:
            coverage_hash += "Z" + e.ctx.get_cover().tostr_hit()
        res = TestResult(coverage_hash, crashed=True, error_msg=error_msg)
        res.ctx = e.ctx
        return res

    except Exception as e:
        # Unexpected crash
        if not objectmodel.we_are_translated():
            import pdb; pdb.xpm()
        error_msg = str(e)
        coverage_hash = 'crash' + hex(objectmodel.compute_hash(error_msg))[2:]
        return TestResult(coverage_hash, crashed=True, error_msg=error_msg)


def load_seeds(seed_files, ctx):
    """Load seed test cases and evaluate them for initial corpus.

    Args:
        seed_files: List of JSON file paths containing BaseV values
        ctx: Interpreter context instance

    Returns:
        list: List of (BaseV, coverage_hash, error_info) tuples for interesting seeds
    """
    seeds = []

    for seed_file in seed_files:
        try:
            print("Loading seed: %s" % corpus.basename(seed_file))

            # Load JSON and parse to BaseV
            with open(seed_file, 'r') as f:
                json_content = f.read()

            json_parsed = rpyjson.loads(json_content)
            seed_value = objects.BaseV.fromjson(json_parsed)

            # Run seed to get coverage
            result = run_test_case(ctx, seed_value, None)

            if result.crashed:
                print("  Seed crashed: %s" % result.error_msg)
            elif result.timed_out:
                print("  Seed timed out")
            else:
                print("  Seed loaded successfully")

            # Add all seeds (even crashing ones) to get diverse coverage
            seeds.append((seed_value, result.coverage_hash, result.error_msg if result.crashed else None))

        except Exception as e:
            if not objectmodel.we_are_translated():
                import pdb;pdb.xpm()
            print("  Failed to load seed %s: %s" % (corpus.basename(seed_file), str(e)))
            continue

    return seeds


def fuzz_main_loop(config, seed_files, ctx, rng, progress_checker=None):
    """Main greybox fuzzing loop.

    Args:
        config: FuzzConfig instance
        seed_files: List of seed file paths
        ctx: Interpreter context instance to test
        rng: Random number generator

    Returns:
        FuzzStats: Final statistics
    """
    print("Starting greybox fuzzing...")
    print("Corpus directory: %s" % config.corpus_dir)
    print("Max iterations: %d" % config.max_iterations)

    # Initialize corpus and statistics
    fuzz_corpus = corpus.FuzzCorpus(config.corpus_dir)
    fuzz_corpus.load_corpus()  # Load any existing corpus
    stats = FuzzStats()

    # Load and evaluate seeds
    if seed_files:
        print("\n=== Loading Seeds ===")
        seeds = load_seeds(seed_files, ctx)

        # Add interesting seeds to corpus
        for seed_value, coverage_hash, error_info in seeds:
            filename = fuzz_corpus.add_test_case(
                seed_value,
                coverage_hash=coverage_hash,
                generation=0  # Seeds are generation 0
            )
            if filename:
                stats.new_coverage_found += 1
                print("Added seed to corpus: %s" % filename)

    print("\n=== Starting Fuzzing Loop ===")
    initial_corpus_size = len(fuzz_corpus.test_cases)
    print("Initial corpus size: %d" % initial_corpus_size)

    # Main fuzzing loop
    try:
        corpus_limit_reached = False
        for iteration in range(config.max_iterations):
            if progress_checker is not None:
                progress_checker(iteration)
            stats.iterations = iteration + 1

            # Periodic status updates
            if iteration % 100 == 0 and iteration > 0:
                print("\nIteration %d/%d" % (iteration, config.max_iterations))
                corpus_stats = fuzz_corpus.get_stats()
                print("Corpus: %d cases, %d unique coverage" % (
                    corpus_stats.total_cases,
                    corpus_stats.unique_coverage
                ))
                stats.print_stats()

            # Select test case for mutation using intelligent selection
            try:
                selected = fuzz_corpus.select_for_mutation_weighted(rng)
                parent_value = selected.value
                parent_coverage = selected.coverage_hash
                parent_generation = selected.generation
                parent_filename = selected.filename
            except EmptyCorpusError:
                print("Empty corpus - cannot continue fuzzing")
                break

            # Perform mutations
            for mutation_attempt in range(config.mutation_budget):
                try:
                    # Mutate the selected value
                    mutated_value = mutatevalues.mutate(parent_value, rng, ctx=ctx)
                    stats.test_cases_run += 1

                    # Run mutated test case
                    result = run_test_case(ctx, mutated_value, config)

                    if result.crashed:
                        stats.crashes_found += 1
                        # Only print if this is a new error message
                        if stats.is_new_error(result.error_msg):
                            print("NEW CRASH at iteration %d: %s" % (iteration, result.error_msg))
                        # Save crashing input
                        crash_filename = fuzz_corpus.add_test_case(
                            mutated_value,
                            coverage_hash=result.coverage_hash,
                            generation=parent_generation + 1
                        )
                        if crash_filename:
                            # Increment parent's descendant count
                            selected.descendants_produced += 1
                            if stats.seen_error_messages[result.error_msg] == 1:
                                print("Saved crash as: %s" % crash_filename)
                        if result.ctx is not None:
                            for pid in result.ctx.get_cover().pidset_hit.to_list():
                                total = stats.if_new_return_total_size(pid, 'error hit')
                                if total:
                                    print("NEW ERROR HIT at iteration %d: %s (total %s)" % (iteration, pid, total))
                                    selected.descendants_produced += 1
                            for pid in result.ctx.get_cover().pidset_miss.to_list():
                                total = stats.if_new_return_total_size(pid, 'error miss')
                                if total:
                                    print("NEW ERROR MISS at iteration %d: %s (total %s)" % (iteration, pid, total))
                                    selected.descendants_produced += 1

                    elif result.timed_out:
                        stats.timeouts += 1

                    else:
                        if result.ctx is not None:
                            for pid in result.ctx.get_cover().pidset_hit.to_list():
                                total = stats.if_new_return_total_size(pid, 'hit')
                                if total:
                                    print("NEW HIT at iteration %d: %s (total %s)" % (iteration, pid, total))
                                    selected.descendants_produced += 1
                            for pid in result.ctx.get_cover().pidset_miss.to_list():
                                total = stats.if_new_return_total_size(pid, 'miss')
                                if total:
                                    print("NEW MISS at iteration %d: %s (total %s)" % (iteration, pid, total))
                                    selected.descendants_produced += 1
                        # Check if this is new interesting coverage
                        saved_filename = fuzz_corpus.add_test_case(
                            mutated_value,
                            coverage_hash=result.coverage_hash,
                            generation=parent_generation + 1
                        )

                        if saved_filename:
                            # Increment parent's descendant count
                            selected.descendants_produced += 1
                            stats.new_coverage_found += 1
                            print("New coverage at iteration %d: %s" % (iteration, saved_filename))

                    # Limit corpus size to prevent unlimited growth
                    if len(fuzz_corpus.test_cases) >= config.corpus_max_size:
                        corpus_limit_reached = True
                        break

                except Exception as e:
                    if not objectmodel.we_are_translated():
                        import pdb; pdb.xpm()
                    # Mutation or execution error - continue to next attempt
                    print("Mutation error at iteration %d: %s" % (iteration, str(e)))
                    continue

            if corpus_limit_reached:
                break

    except KeyboardInterrupt:
        print("\nFuzzing interrupted by user")
    finally:
        # Final statistics
        print("\n=== Fuzzing Complete ===")
        final_corpus_stats = fuzz_corpus.get_stats()
        print("Final corpus: %d cases" % final_corpus_stats.total_cases)
        print("Coverage diversity: %d unique hashes" % final_corpus_stats.unique_coverage)
        stats.print_stats()

    return stats


