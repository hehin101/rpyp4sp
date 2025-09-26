from rpyp4sp.error import (P4Error, P4NotImplementedError, P4UnknownTypeError,
                          P4EvaluationError, P4TypeSubstitutionError, P4CastError,
                          P4BuiltinError, P4RelationError, P4ContextError, P4ParseError,
                          extract_line, Traceback)
from rpyp4sp.p4specast import Region, Position, NO_REGION

def test_p4error_format_basic():
    error = P4Error("basic error message")
    assert error.format() == "basic error message"

def test_p4error_format_empty():
    error = P4Error("")
    assert error.format() == ""

def test_p4error_format_with_region():
    # Region should not affect the basic format output
    error = P4Error("error with region", region=None)
    assert error.format() == "error with region"

def test_p4notimplementederror_format():
    error = P4NotImplementedError("not implemented feature")
    assert error.format() == "not implemented feature"

def test_p4unknowntypeerror_format():
    error = P4UnknownTypeError("unknown type encountered")
    assert error.format() == "unknown type encountered"

def test_p4evaluationerror_format():
    error = P4EvaluationError("evaluation failed")
    assert error.format() == "evaluation failed"

def test_p4typesubstitutionerror_format():
    error = P4TypeSubstitutionError("substitution error")
    assert error.format() == "substitution error"

def test_p4casterror_format():
    error = P4CastError("cast operation failed")
    assert error.format() == "cast operation failed"

def test_p4builtinerror_format():
    error = P4BuiltinError("builtin function error")
    assert error.format() == "builtin function error"

def test_p4relationerror_format():
    error = P4RelationError("relation not matched")
    assert error.format() == "relation not matched"

def test_p4contexterror_format():
    error = P4ContextError("context operation failed")
    assert error.format() == "context operation failed"

def test_p4parseerror_format():
    error = P4ParseError("parse error occurred")
    assert error.format() == "parse error occurred"

def test_p4error_format_with_special_characters():
    error = P4Error("error with 'quotes' and \"double quotes\" and newlines\nand tabs\t")
    assert error.format() == "error with 'quotes' and \"double quotes\" and newlines\nand tabs\t"

# Tests for P4Error.maybe_add_region method

def test_maybe_add_region_none():
    # Should not add None region
    error = P4Error("test message")
    original_region = error.region
    error.maybe_add_region(None)
    assert error.region == original_region

def test_maybe_add_region_no_information():
    # Should not add region without information (NO_REGION)
    error = P4Error("test message")
    original_region = error.region
    error.maybe_add_region(NO_REGION)
    assert error.region == original_region

def test_maybe_add_region_no_information_empty_positions():
    # Should not add region with empty positions (no information)
    error = P4Error("test message")
    original_region = error.region
    empty_region = Region(Position('', 0, 0), Position('', 0, 0))
    error.maybe_add_region(empty_region)
    assert error.region == original_region

def test_maybe_add_region_valid_to_none():
    # Should add valid region when current region is None
    error = P4Error("test message")
    assert error.region is None

    valid_region = Region.line_span('test.py', 10, 5, 15)
    error.maybe_add_region(valid_region)
    assert error.region == valid_region

def test_maybe_add_region_valid_to_no_region():
    # Should add valid region when current region is NO_REGION (no information)
    error = P4Error("test message", region=NO_REGION)

    valid_region = Region.line_span('test.py', 10, 5, 15)
    error.maybe_add_region(valid_region)
    assert error.region == valid_region

def test_maybe_add_region_valid_to_empty_region():
    # Should add valid region when current region has no information
    error = P4Error("test message", region=Region(Position('', 0, 0), Position('', 0, 0)))

    valid_region = Region.line_span('test.py', 10, 5, 15)
    error.maybe_add_region(valid_region)
    assert error.region == valid_region

def test_maybe_add_region_keep_existing_valid():
    # Should NOT replace existing valid region
    existing_region = Region.line_span('existing.py', 5, 1, 10)
    error = P4Error("test message", region=existing_region)

    new_region = Region.line_span('new.py', 15, 1, 20)
    error.maybe_add_region(new_region)

    # Should keep the original region
    assert error.region == existing_region

def test_maybe_add_region_partial_information_left():
    # Should add region with partial information (left position has info)
    error = P4Error("test message")

    partial_region = Region(Position('test.py', 10, 5), Position('', 0, 0))
    error.maybe_add_region(partial_region)
    assert error.region == partial_region

def test_maybe_add_region_partial_information_right():
    # Should add region with partial information (right position has info)
    error = P4Error("test message")

    partial_region = Region(Position('', 0, 0), Position('test.py', 10, 5))
    error.maybe_add_region(partial_region)
    assert error.region == partial_region

# Tests for extract_line helper function

def test_extract_line_none_region():
    # Should return None for None region
    file_content = {"test.py": "line 1\nline 2\nline 3"}
    result = extract_line(None, file_content)
    assert result is None

def test_extract_line_not_line_span():
    # Should return None for region that is not a line_span
    # Create region with different files (not a line span)
    region = Region(Position('file1.py', 1, 1), Position('file2.py', 1, 5))
    file_content = {"file1.py": "line 1\nline 2", "file2.py": "other line"}
    result = extract_line(region, file_content)
    assert result is None

def test_extract_line_not_line_span_different_lines():
    # Should return None for region spanning different lines
    region = Region(Position('test.py', 1, 1), Position('test.py', 2, 5))
    file_content = {"test.py": "line 1\nline 2\nline 3"}
    result = extract_line(region, file_content)
    assert result is None

def test_extract_line_file_not_found():
    # Should return None when file is not in file_content
    region = Region.line_span('missing.py', 1, 1, 5)
    file_content = {"test.py": "line 1\nline 2\nline 3"}
    result = extract_line(region, file_content)
    assert result is None

def test_extract_line_line_number_too_high():
    # Should return None when line number exceeds file length
    region = Region.line_span('test.py', 10, 1, 5)  # line 10 doesn't exist
    file_content = {"test.py": "line 1\nline 2\nline 3"}
    result = extract_line(region, file_content)
    assert result is None

def test_extract_line_line_number_zero():
    # Should return None for line number 0 (invalid)
    region = Region.line_span('test.py', 0, 1, 5)
    file_content = {"test.py": "line 1\nline 2\nline 3"}
    result = extract_line(region, file_content)
    assert result is None

def test_extract_line_line_number_negative():
    # Should return None for negative line number
    region = Region.line_span('test.py', -1, 1, 5)
    file_content = {"test.py": "line 1\nline 2\nline 3"}
    result = extract_line(region, file_content)
    assert result is None

def test_extract_line_valid_first_line():
    # Should return first line correctly
    region = Region.line_span('test.py', 1, 1, 5)
    file_content = {"test.py": "first line\nsecond line\nthird line"}
    result = extract_line(region, file_content)
    assert result == "first line"

def test_extract_line_valid_middle_line():
    # Should return middle line correctly
    region = Region.line_span('test.py', 2, 1, 5)
    file_content = {"test.py": "first line\nsecond line\nthird line"}
    result = extract_line(region, file_content)
    assert result == "second line"

def test_extract_line_valid_last_line():
    # Should return last line correctly
    region = Region.line_span('test.py', 3, 1, 5)
    file_content = {"test.py": "first line\nsecond line\nthird line"}
    result = extract_line(region, file_content)
    assert result == "third line"

def test_extract_line_single_line_file():
    # Should work with single line file
    region = Region.line_span('single.py', 1, 1, 10)
    file_content = {"single.py": "only line"}
    result = extract_line(region, file_content)
    assert result == "only line"

def test_extract_line_empty_file():
    # Should return None for empty file
    region = Region.line_span('empty.py', 1, 1, 5)
    file_content = {"empty.py": ""}
    result = extract_line(region, file_content)
    assert result is None

def test_extract_line_empty_line():
    # Should return empty string for empty line
    region = Region.line_span('test.py', 2, 1, 1)
    file_content = {"test.py": "line 1\n\nline 3"}
    result = extract_line(region, file_content)
    assert result == ""

def test_extract_line_with_whitespace():
    # Should preserve whitespace in line
    region = Region.line_span('test.py', 1, 1, 10)
    file_content = {"test.py": "  \t  line with spaces  \t  "}
    result = extract_line(region, file_content)
    assert result == "  \t  line with spaces  \t  "

def test_extract_line_multiple_files():
    # Should extract from correct file when multiple files exist
    region = Region.line_span('file2.py', 2, 1, 5)
    file_content = {
        "file1.py": "file1 line1\nfile1 line2",
        "file2.py": "file2 line1\nfile2 line2\nfile2 line3",
        "file3.py": "file3 line1"
    }
    result = extract_line(region, file_content)
    assert result == "file2 line2"

# Tests for Traceback._format_entry method

def test_format_entry_none_region():
    # Should handle None region
    tb = Traceback()
    result = tb._format_entry("test_function", None, {})
    expected = ['  File "<unknown>", line ?, in test_function']
    assert result == expected

def test_format_entry_no_information():
    # Should handle region with no information
    tb = Traceback()
    region = NO_REGION
    result = tb._format_entry("test_function", region, {})
    expected = ['  File "<unknown>", line ?, in test_function']
    assert result == expected

def test_format_entry_partial_information_no_file():
    # Should handle region with partial information (no file)
    tb = Traceback()
    region = Region(Position('', 5, 10), Position('', 5, 15))
    result = tb._format_entry("test_function", region, {})
    expected = ['  File "<unknown>", line 5, in test_function']
    assert result == expected

def test_format_entry_no_source_available():
    # Should format entry when source line is not available
    tb = Traceback()
    region = Region.line_span('missing.py', 10, 1, 5)
    file_content = {"other.py": "some content"}
    result = tb._format_entry("test_function", region, file_content)
    expected = ['  File "missing.py", line 10, in test_function']
    assert result == expected

def test_format_entry_with_source_no_caret():
    # Should format entry with source line but no caret (not line_span)
    tb = Traceback()
    region = Region(Position('test.py', 2, 0), Position('other.py', 3, 5))  # Not line_span
    file_content = {"test.py": "line 1\nline 2\nline 3"}
    result = tb._format_entry("test_function", region, file_content)
    expected = ['  File "test.py", line 2, in test_function']
    assert result == expected

def test_format_entry_with_source_and_single_caret():
    # Should format entry with source line and single character caret
    tb = Traceback()
    region = Region.line_span('test.py', 2, 5, 5)  # Single character at column 5
    file_content = {"test.py": "line 1\ntest line here\nline 3"}
    result = tb._format_entry("test_function", region, file_content)
    expected = [
        '  File "test.py", line 2, in test_function',
        '    test line here',
        '    ----^'
    ]
    # Check the structure (exact spacing might vary)
    assert len(result) == 3
    assert result[0] == '  File "test.py", line 2, in test_function'
    assert result[1] == '    test line here'
    assert '^' in result[2]

def test_format_entry_with_source_and_multi_caret():
    # Should format entry with source line and multi-character caret
    tb = Traceback()
    region = Region.line_span('test.py', 1, 6, 10)  # Characters 6-10
    file_content = {"test.py": "hello world test"}
    result = tb._format_entry("test_function", region, file_content)
    expected_structure = [
        '  File "test.py", line 1, in test_function',
        '    hello world test',
        '    -----^^^^^'  # 5 carets for columns 6-10
    ]

    assert len(result) == 3
    assert result[0] == '  File "test.py", line 1, in test_function'
    assert result[1] == '    hello world test'
    assert '^^^^^' in result[2]  # Should have 5 carets

def test_format_entry_with_whitespace_source():
    # Should handle source lines with whitespace correctly (indentation stripped)
    tb = Traceback()
    region = Region.line_span('test.py', 1, 6, 10)  # Adjusted for stripped indentation
    file_content = {"test.py": "  \t  error here  \t  "}
    result = tb._format_entry("test_function", region, file_content)

    assert len(result) == 3
    assert result[0] == '  File "test.py", line 1, in test_function'
    assert result[1] == '    ' + "error here  \t  "  # Leading whitespace stripped
    assert '^^^^^' in result[2]  # 5 carets for "error"

def test_format_entry_caret_at_start():
    # Should handle caret at start of line (column 1)
    tb = Traceback()
    region = Region.line_span('test.py', 1, 1, 3)
    file_content = {"test.py": "error message"}
    result = tb._format_entry("test_function", region, file_content)

    assert len(result) == 3
    assert result[0] == '  File "test.py", line 1, in test_function'
    assert result[1] == '    error message'
    assert result[2] == '    ^^^'  # Should start immediately, no leading spaces

def test_format_entry_invalid_column_range():
    # Should handle invalid column ranges gracefully (start_col <= 0 or end_col < start_col)
    tb = Traceback()
    region = Region.line_span('test.py', 1, 0, 5)  # Invalid start column
    file_content = {"test.py": "test line"}
    result = tb._format_entry("test_function", region, file_content)

    # Should not include caret line for invalid columns
    assert len(result) == 2
    assert result[0] == '  File "test.py", line 1, in test_function'
    assert result[1] == '    test line'

def test_format_entry_complex_example():
    # Test a more complex realistic example
    tb = Traceback()
    region = Region.line_span('/home/user/project/main.py', 2, 12, 17)  # Line 2, columns 12-17
    file_content = {"/home/user/project/main.py": "def func():\n    result = calculate_something() + process_data()\n    return result"}
    result = tb._format_entry("calculate_something", region, file_content)

    assert len(result) == 3
    assert result[0] == '  File "/home/user/project/main.py", line 2, in calculate_something'
    assert 'result = calculate_something() + process_data()' in result[1]
    assert '^^^^^^' in result[2]  # 6 carets for columns 12-17

# Tests for Traceback.format method


def test_traceback_format_empty():
    # Should return empty list for empty traceback
    tb = Traceback()
    result = tb.format({})
    assert result == []

def test_traceback_format_single_entry():
    # Should format single traceback entry
    tb = Traceback()
    region = Region.line_span('test.py', 1, 1, 5)
    tb.add_frame("main", region)

    file_content = {"test.py": "error here"}
    result = tb.format(file_content)

    expected = [
        "Traceback (most recent call last):",
        '  File "test.py", line 1, in main',
        '    error here',
        '    ^^^^^'
    ]
    assert result == expected

def test_traceback_format_multiple_entries():
    # Should format multiple entries in reverse order
    tb = Traceback()

    # Add frames as exception bubbles up (innermost to outermost)
    region1 = Region.line_span('calc.py', 10, 1, 5)  # Innermost call (error occurs here)
    tb.add_frame("calculate", region1)

    region2 = Region.line_span('utils.py', 5, 1, 6)  # Middle call
    tb.add_frame("helper", region2)

    region3 = Region.line_span('main.py', 1, 1, 4)  # Outermost call
    tb.add_frame("main", region3)

    file_content = {
        "main.py": "main()",
        "utils.py": "def helper():\n\n\n\ncall()",
        "calc.py": "def calc():\n\n\n\n\n\n\n\n\nerror"
    }

    result = tb.format(file_content)

    # Should be in reverse order (most recent call last)
    expected = [
        "Traceback (most recent call last):",
        '  File "main.py", line 1, in main',
        '    main()',   # carets shown - doesn't cover whole line (cols 1-4 of 6)
        '    ^^^^',
        '  File "utils.py", line 5, in helper',
        '    call()',   # carets omitted - covers whole line (cols 1-6 of 6)
        '  File "calc.py", line 10, in calculate',
        '    error'     # carets omitted - covers whole line (cols 1-5 of 5)
    ]
    assert result == expected

def test_traceback_format_with_unknown_regions():
    # Should handle entries with no region information
    tb = Traceback()

    # Entry with no region
    tb.add_frame("unknown_func", None)

    # Entry with valid region
    region = Region.line_span('known.py', 2, 1, 3)
    tb.add_frame("known_func", region)

    file_content = {"known.py": "line1\nok()"}
    result = tb.format(file_content)

    expected = [
        "Traceback (most recent call last):",
        '  File "known.py", line 2, in known_func',
        '    ok()',
        '    ^^^',
        '  File "<unknown>", line ?, in unknown_func'
    ]
    assert result == expected

def test_traceback_format_no_source_available():
    # Should work even when source files are not available
    tb = Traceback()

    region = Region.line_span('missing.py', 10, 1, 5)
    tb.add_frame("missing_func", region)

    file_content = {}  # No source files available
    result = tb.format(file_content)

    expected = [
        "Traceback (most recent call last):",
        '  File "missing.py", line 10, in missing_func'
    ]
    assert result == expected

def test_format_entry_indentation_regularization():
    # Should regularize deeply indented code to start with 4 spaces
    tb = Traceback()
    region = Region.line_span('deep.py', 1, 9, 12)  # Columns 9-12 (4 chars)
    file_content = {"deep.py": "        func()"}  # 8 spaces of indentation

    result = tb._format_entry("nested_func", region, file_content)

    expected = [
        '  File "deep.py", line 1, in nested_func',
        '    func()',  # Regularized to 4 spaces
        '    ^^^^'    # Adjusted caret position (columns 9-12 -> 1-4 after stripping 8 spaces)
    ]
    assert result == expected


def test_format_entry_no_indentation():
    # Should work with code that has no indentation
    tb = Traceback()
    region = Region.line_span('root.py', 1, 1, 5)
    file_content = {"root.py": "print()"}

    result = tb._format_entry("root_func", region, file_content)

    expected = [
        '  File "root.py", line 1, in root_func',
        '    print()',  # Still gets 4 spaces prefix
        '    ^^^^^'     # Original caret position preserved
    ]
    assert result == expected

def test_format_entry_whole_line_caret_omitted():
    # Should omit carets when they would cover the entire non-empty line
    tb = Traceback()
    region = Region.line_span('whole.py', 1, 1, 5)  # Covers entire "error" word
    file_content = {"whole.py": "error"}

    result = tb._format_entry("whole_func", region, file_content)

    expected = [
        '  File "whole.py", line 1, in whole_func',
        '    error'  # No caret line since it would cover the whole word
    ]
    assert result == expected

def test_format_entry_whole_line_with_trailing_space_caret_omitted():
    # Should omit carets when they would cover entire non-empty content (ignoring trailing spaces)
    tb = Traceback()
    region = Region.line_span('trail.py', 1, 1, 5)  # Covers "error" part
    file_content = {"trail.py": "error   "}  # Trailing spaces

    result = tb._format_entry("trail_func", region, file_content)

    expected = [
        '  File "trail.py", line 1, in trail_func',
        '    error   '  # No caret line since it would cover the whole non-empty content
    ]
    assert result == expected

def test_format_entry_partial_line_caret_included():
    # Should include carets when they don't cover the entire line
    tb = Traceback()
    region = Region.line_span('partial.py', 1, 1, 3)  # Only covers "err" of "error"
    file_content = {"partial.py": "error"}

    result = tb._format_entry("partial_func", region, file_content)

    expected = [
        '  File "partial.py", line 1, in partial_func',
        '    error',
        '    ^^^'  # Carets included since they don't cover the whole word
    ]
    assert result == expected

def test_format_entry_indented_whole_line_caret_omitted():
    # Should omit carets for whole line even after indentation adjustment
    tb = Traceback()
    region = Region.line_span('indent.py', 1, 5, 9)  # Covers "func" after 4 spaces
    file_content = {"indent.py": "    func"}

    result = tb._format_entry("indent_func", region, file_content)

    expected = [
        '  File "indent.py", line 1, in indent_func',
        '    func'  # No caret line since adjusted region covers the whole stripped content
    ]
    assert result == expected

def test_format_entry_with_colors():
    # Should include ANSI color codes when color=True
    tb = Traceback()
    region = Region.line_span('test.py', 1, 1, 5)
    file_content = {"test.py": "error"}

    result = tb._format_entry("test_func", region, file_content, color=True)

    # Check for color codes in file line
    assert '\033[35m"test.py"\033[0m' in result[0]  # MAGENTA filename
    assert '\033[35m1\033[0m' in result[0]          # MAGENTA line number
    assert ', in test_func' in result[0]

    # Source line should be plain (no colors on source code itself)
    assert result[1] == '    error'

    # No caret line since it covers whole word
    assert len(result) == 2

def test_format_entry_with_colors_and_carets():
    # Should colorize carets and source code when color=True and carets are shown
    tb = Traceback()
    region = Region.line_span('test.py', 1, 1, 3)  # Partial coverage
    file_content = {"test.py": "error_message"}

    result = tb._format_entry("test_func", region, file_content, color=True)

    # Check for color codes in file line
    assert '\033[35m"test.py"\033[0m' in result[0]

    # Source line should have the highlighted portion colored
    assert result[1] == '    \033[1;31merr\033[0mor_message'  # "err" highlighted in red

    # Caret line should have red carets
    assert result[2] == '    \033[1;31m^^^\033[0m'  # BOLD_RED carets

def test_format_entry_with_colors_unknown_region():
    # Should colorize unknown file info when color=True
    tb = Traceback()
    result = tb._format_entry("unknown_func", None, {}, color=True)

    # Check for color codes in unknown file line
    assert '\033[35m"<unknown>"\033[0m' in result[0]  # MAGENTA filename
    assert '\033[35m?\033[0m' in result[0]            # MAGENTA line number
    assert ', in unknown_func' in result[0]

def test_traceback_format_with_colors():
    # Should format complete traceback with colors
    tb = Traceback()
    region = Region.line_span('test.py', 1, 2, 4)
    tb.add_frame("main", region)

    file_content = {"test.py": "func()"}
    result = tb.format(file_content, color=True)

    expected_start = "Traceback (most recent call last):"
    assert result[0] == expected_start

    # File line should have colors
    assert '\033[35m"test.py"\033[0m' in result[1]
    assert '\033[35m1\033[0m' in result[1]

    # Source line should have highlighted portion
    assert result[2] == '    f\033[1;31munc\033[0m()'  # "unc" highlighted in red

    # Caret line should be colored
    assert '\033[1;31m^^^\033[0m' in result[3]

def test_p4error_format_with_colors():
    # Should work with color parameter (though P4Error doesn't use it yet)
    error = P4Error("Test error message")
    result = error.format(color=True)
    assert result == "Test error message"  # Color doesn't change the message for basic P4Error

def test_can_colorize():
    # Should return a boolean indicating if stderr is a TTY
    from rpyp4sp.error import can_colorize
    result = can_colorize()
    assert isinstance(result, bool)  # Should return either True or False

def test_format_entry_with_colors_full_line_no_highlight():
    # Should NOT color source code when it covers the entire line
    tb = Traceback()
    region = Region.line_span('test.py', 1, 1, 5)  # Covers entire "error" word
    file_content = {"test.py": "error"}

    result = tb._format_entry("test_func", region, file_content, color=True)

    # Check for color codes in file line
    assert '\033[35m"test.py"\033[0m' in result[0]

    # Source line should be plain (no highlighting since it covers whole word)
    assert result[1] == '    error'

    # No caret line since it covers whole word
    assert len(result) == 2

def test_format_p4error_function():
    # Test the format_p4error function from error.py
    from rpyp4sp.error import format_p4error

    # Test basic error
    error = P4Error("Test error message")
    result = format_p4error(error, {}, color=False)
    assert result == "Test error message"

    # Test error with traceback
    error_with_trace = P4Error("Division by zero")
    region = Region.line_span('calc.py', 10, 1, 5)
    error_with_trace.traceback.add_frame("divide", region)

    result = format_p4error(error_with_trace, {}, color=False)
    lines = result.split('\n')
    assert lines[0] == "Division by zero"
    assert "Traceback (most recent call last):" in lines[1]
    assert 'File "calc.py", line 10, in divide' in lines[2]

    # Test auto color detection (should return False when not in TTY)
    result_auto = format_p4error(error_with_trace, {})  # color=None, auto-detect
    assert result_auto == result  # Should be same as color=False when not in TTY

    # Test with colors enabled
    result_colored = format_p4error(error_with_trace, {}, color=True)
    lines_colored = result_colored.split('\n')
    assert lines_colored[0] == "Division by zero"  # Error message unchanged
    assert "Traceback (most recent call last):" in lines_colored[1]
    # File line should have color codes
    assert '\033[35m"calc.py"\033[0m' in lines_colored[2]  # MAGENTA filename
    assert '\033[35m10\033[0m' in lines_colored[2]  # MAGENTA line number

    # Test with new list format [filenames, contents]
    file_content_list = [["calc.py"], ["error content"]]
    result_list_format = format_p4error(error_with_trace, file_content_list, color=False)
    lines_list = result_list_format.split('\n')
    assert lines_list[0] == "Division by zero"
    assert "Traceback (most recent call last):" in lines_list[1]
    assert 'File "calc.py", line 10, in divide' in lines_list[2]
