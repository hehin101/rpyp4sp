import sys

def safe_slice(s, start=0, stop=sys.maxint):
    assert start >= 0
    assert stop >= 0
    if stop == sys.maxint:
        return s[start:]
    else:
        return s[start:stop]

class P4Error(Exception):
    def __init__(self, msg, region=None, ctx=None):
        self.msg = msg
        self.traceback = Traceback()
        self.region = region
        self.ctx = ctx

    def maybe_add_region(self, region):
        if region is None or not region.has_information():
            return
        if self.region is None or not self.region.has_information():
            self.region = region

    def maybe_add_ctx(self, ctx):
        if self.ctx is None:
            self.ctx = ctx

    def traceback_add_frame(self, name, region, ast=None):
        self.traceback.add_frame(name, region, ast)

    def traceback_patch_last_name(self, name):
        if not self.traceback.frames and self.region and self.region.has_information():
            self.traceback_add_frame('???', self.region)
        self.traceback.patch_last_name(name)

    def format(self, color=False):
        if color:
            return ANSIColors.MAGENTA + self.msg + ANSIColors.RESET
        return self.msg

    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, self.msg)


class P4NotImplementedError(P4Error):
    """Error for features that are not yet implemented"""
    pass

class P4UnknownTypeError(P4Error):
    """Error for unknown or unhandled types"""
    pass

class P4EvaluationError(P4Error):
    """Error during expression or instruction evaluation"""
    pass

class P4TypeSubstitutionError(P4Error):
    """Error during type substitution operations"""
    pass

class P4CastError(P4Error):
    """Error during type casting operations (upcast/downcast)"""
    pass

class P4BuiltinError(P4Error):
    """Error in builtin function operations"""
    pass

class P4RelationError(P4Error):
    """Error when a relation is not matched"""
    pass

class P4ContextError(P4Error):
    """Error in context operations"""
    pass

class P4ParseError(P4Error):
    """Error during parsing operations"""
    pass

def find_nth(string, substring, n, startpos=0):
    """
    Find the nth occurrence of substring in string.

    Args:
        string: The string to search in
        substring: The substring to find
        n: Which occurrence to find (0-based)
        startpos: Starting position for search

    Returns:
        int: Position of nth occurrence, or -1 if not found
    """
    pos = startpos
    for i in range(n + 1):
        assert pos >= 0
        pos = string.find(substring, pos)
        if pos < 0:
            return -1
        if i < n:  # Don't advance past the last occurrence
            pos += len(substring)
    return pos

def extract_lines_region(region, file_content):
    """
    Extract all complete lines that a region spans from file content.
    Ignores column information and returns all lines from start_line to end_line.

    Args:
        region: A Region object
        file_content: Dict with filename keys and file content (str) as values

    Returns:
        str: The complete lines content for the region if file exists, None otherwise
    """
    if region is None:
        return None

    if not region.has_information():
        return None

    filename = region.left.file
    if filename not in file_content:
        return None

    content = file_content[filename]

    # Get start and end line numbers
    if not region.left.has_information():
        return None

    start_line = region.left.line - 1  # Convert to 0-based

    # Determine end line
    if region.is_line_span():
        end_line = start_line  # For line spans, start and end are the same
    else:
        # Multi-line region
        if not region.right.has_information():
            return None
        # Check that both positions are in the same file
        if region.right.file != filename:
            return None
        end_line = region.right.line - 1  # Convert to 0-based

    # Validate line range
    if start_line < 0 or end_line < start_line:
        return None

    # Find start of the first line
    if start_line == 0:
        line_start = 0
    else:
        line_start = find_nth(content, '\n', start_line - 1)
        if line_start < 0:
            return None
        line_start += 1  # Move past the newline

    # Find end of the last line
    if start_line == end_line:
        # Single line case - find the first newline after line_start
        line_end = content.find('\n', line_start)
        if line_end < 0:
            line_end = len(content)  # Last line without trailing newline
    else:
        # Multi-line case - find the newline that ends the target end_line
        # We need to skip (end_line - start_line) newlines from line_start
        lines_to_skip = end_line - start_line
        target_newline = find_nth(content, '\n', lines_to_skip, line_start)
        if target_newline < 0:
            # We've reached the end of file before end_line
            line_end = len(content)
        else:
            line_end = target_newline

    # Check if we found a valid range
    if line_start >= len(content):
        return None

    return safe_slice(content, line_start, line_end)


def can_colorize():
    import os

    # Check environment variables that disable colors
    if os.environ.get('NO_COLOR'):
        return False
    if os.environ.get('ANSI_COLORS_DISABLED'):
        return False
    if os.environ.get('FORCE_COLOR') == '0':
        return False
    if os.environ.get('TERM') == 'dumb':
        return False

    # Force color if explicitly requested
    if os.environ.get('FORCE_COLOR') == '1':
        return True

    # Default: check if stdout is a TTY
    try:
        return os.isatty(1)
    except (AttributeError, OSError):
        return False


class ANSIColors(object):
    """ANSI color constants for terminal output"""
    RESET = '\033[0m'
    BOLD_RED = '\033[1;31m'
    BOLD_MAGENTA = '\033[1;35m'
    MAGENTA = '\033[35m'


class Traceback(object):
    def __init__(self):
        self.frames = []

    def add_frame(self, name, region, ast=None):
        self.frames.append((name, region, ast))

    def patch_last_name(self, name):
        if not self.frames:
            return
        oldname, region, ast = self.frames.pop()
        if oldname != '???':
            name = oldname
        self.frames.append((name, region, ast))

    def _format_file_line(self, name, filename, line_num, color, spec_dirname=None):
        """Helper to format the file/line/function header line."""
        if color:
            formatted_filename = filename
            if spec_dirname is not None and filename != "<unknown>":
                # Create terminal link with file:// scheme
                import os
                absolute_path = spec_dirname + os.path.sep + filename
                formatted_filename = '\033]8;;file://%s\033\\%s\033]8;;\033\\' % (absolute_path, filename)

            return '  File %s"%s"%s, line %s%s%s, in %s%s%s' % (
                ANSIColors.MAGENTA, formatted_filename, ANSIColors.RESET,
                ANSIColors.MAGENTA, line_num, ANSIColors.RESET,
                ANSIColors.MAGENTA, name, ANSIColors.RESET)
        else:
            return '  File "%s", line %s, in %s' % (filename, line_num, name)

    def _should_skip_highlighting(self, adjusted_start_col, adjusted_end_col, stripped_line):
        """Helper to determine if highlighting should be skipped for full-line coverage."""
        stripped_line_length = len(stripped_line.rstrip())

        # Skip if highlighting covers the entire line
        if adjusted_start_col == 1 and adjusted_end_col >= stripped_line_length:
            return True

        # Skip if the only non-covered part is a "-- " prefix at the start
        if (adjusted_start_col == 3 and adjusted_end_col >= stripped_line_length and
            stripped_line.startswith("-- ")):
            return True

        return False

    def _adjust_column_positions(self, start_col, end_col, original_indent):
        """Helper to adjust column positions after stripping indentation."""
        adjusted_start_col = max(1, start_col - original_indent)
        adjusted_end_col = max(adjusted_start_col, end_col - original_indent)
        return adjusted_start_col, adjusted_end_col

    def _format_dedented_line(self, source_line, min_indent):
        """
        Helper to format a single line by removing common indentation.

        Args:
            source_line: The source line to format
            min_indent: Minimum indentation to remove from all lines

        Returns:
            str: Formatted line with 4-space prefix and common indentation removed
        """
        if not source_line.strip():
            # Empty or whitespace-only line
            return '    '
        else:
            # Remove common indentation and add 4-space prefix
            dedented = source_line[min_indent:] if len(source_line) >= min_indent else source_line.lstrip()
            return '    %s' % dedented

    def _format_multiline_source(self, source_content):
        """
        Format multi-line source content with optional abbreviation.

        For regions with more than 5 lines, shows first 2 and last 2 lines
        with an omission message in between. Preserves relative indentation
        by removing only the minimum common indentation.

        Args:
            source_content: String containing the source lines (may contain newlines)

        Returns:
            list of str: Formatted source lines with 4-space indentation
        """
        lines = []
        source_lines = source_content.split('\n')

        # Calculate minimum indentation across all non-empty lines
        min_indent = -1
        for source_line in source_lines:
            if source_line.strip():  # Only consider non-empty lines
                indent = len(source_line) - len(source_line.lstrip())
                if min_indent < 0 or indent < min_indent:
                    min_indent = indent

        # If all lines are empty, use 0 indentation
        if min_indent < 0:
            min_indent = 0

        if len(source_lines) <= 5:
            # Show all lines if 5 or fewer
            for source_line in source_lines:
                lines.append(self._format_dedented_line(source_line, min_indent))
        else:
            # Show first 2 and last 2 lines with omission message
            for i in range(2):
                if i < len(source_lines):
                    lines.append(self._format_dedented_line(source_lines[i], min_indent))

            omitted_count = len(source_lines) - 4
            lines.append('    [%d lines omitted]' % omitted_count)

            for i in range(len(source_lines) - 2, len(source_lines)):
                if i >= 0:
                    lines.append(self._format_dedented_line(source_lines[i], min_indent))

        return lines

    def _format_entry(self, name, region, file_content, color=False, spec_dirname=None):
        """
        Format a single traceback entry.

        Args:
            name: Function/context name
            region: Region object
            file_content: Dict with filename keys and file content (str) as values
            color: Whether to include ANSI color codes
            spec_dirname: Absolute path to join with relative file paths

        Returns:
            list of str: Lines representing the formatted traceback entry
        """
        lines = []

        # Handle missing region information
        if region is None or not region.has_information():
            lines.append(self._format_file_line(name, "<unknown>", "?", color, spec_dirname))
            return lines

        # Extract filename and line number
        filename = region.left.file if region.left.has_information() and region.left.file else "<unknown>"
        line_num = str(region.left.line) if region.left.has_information() else "?"
        lines.append(self._format_file_line(name, filename, line_num, color, spec_dirname))

        # Try to extract and display the source line(s)
        source_content = extract_lines_region(region, file_content)
        if source_content is not None:
            # Handle single-line regions (line spans) with highlighting and carets
            if (region.is_line_span() and region.left.has_information() and
                region.right.has_information()):

                stripped_line = source_content.lstrip()
                original_indent = len(source_content) - len(stripped_line)

                start_col = region.left.column
                end_col = region.right.column
                adjusted_start_col, adjusted_end_col = self._adjust_column_positions(
                    start_col, end_col, original_indent)

                skip_highlighting = self._should_skip_highlighting(adjusted_start_col, adjusted_end_col, stripped_line)

                # Source line with optional color highlighting
                if color and not skip_highlighting:
                    before = safe_slice(stripped_line, 0, adjusted_start_col - 1)
                    highlighted = safe_slice(stripped_line, adjusted_start_col - 1, adjusted_end_col)
                    after = safe_slice(stripped_line, adjusted_end_col)
                    colored_line = before + ANSIColors.BOLD_RED + highlighted + ANSIColors.RESET + after
                    lines.append('    %s' % colored_line)
                else:
                    lines.append('    %s' % stripped_line)

                # Add caret indicator if valid column range and not skipping
                if (start_col > 0 and end_col >= start_col and
                    adjusted_start_col > 0 and adjusted_end_col >= adjusted_start_col and
                    not skip_highlighting):

                    caret_line = '    ' + ' ' * (adjusted_start_col - 1)
                    carets = '^' * (adjusted_end_col - adjusted_start_col + 1) if adjusted_end_col > adjusted_start_col else '^'

                    if color:
                        caret_line += ANSIColors.BOLD_RED + carets + ANSIColors.RESET
                    else:
                        caret_line += carets
                    lines.append(caret_line)
            else:
                # Handle multi-line regions - show multiple lines without carets or highlighting
                lines.extend(self._format_multiline_source(source_content))

        return lines

    def format(self, file_content, color=False, ctx=None, spec_dirname=None):
        """
        Format the complete traceback.

        Args:
            file_content: Dict with filename keys and file content (str) as values
            color: Whether to include ANSI color codes
            ctx: Context for local variables
            spec_dirname: Absolute path to join with relative file paths

        Returns:
            list of str: Lines representing the formatted traceback
        """
        if not self.frames:
            return []

        # Reverse the frames to show most recent call last
        reversed_frames = self.frames[:]
        reversed_frames.reverse()

        # Format all entries with run-length encoding for repeated entries
        all_lines = []
        if reversed_frames:
            all_lines.append("Traceback (most recent call last):")

        prev_entry_lines = None
        repeat_count = 0
        region = None

        for name, region, ast in reversed_frames:
            entry_lines = self._format_entry(name, region, file_content, color=color, spec_dirname=spec_dirname)

            if prev_entry_lines is not None and entry_lines == prev_entry_lines:
                repeat_count += 1
            else:
                # If we have accumulated repeats, add the repeat message
                if repeat_count > 0:
                    if repeat_count == 1:
                        all_lines.append("  [Previous entry repeated 1 time]")
                    else:
                        all_lines.append("  [Previous entry repeated %d times]" % repeat_count)
                    repeat_count = 0

                # Add the current entry
                all_lines.extend(entry_lines)
                prev_entry_lines = entry_lines

        # Handle any remaining repeats at the end
        if repeat_count > 0:
            if repeat_count == 1:
                all_lines.append("  [Previous entry repeated 1 time]")
            else:
                all_lines.append("  [Previous entry repeated %d times]" % repeat_count)
        if ctx:
            last_line = extract_lines_region(region, file_content) if region is not None else None
            all_lines.extend(format_ctx(ctx, last_line, color=color))

        return all_lines

def format_ctx(ctx, entry_line, color=False):
    lines = ["Local variables:"]
    for (varname, iterators), value in ctx.venv.items():
        if entry_line is None or varname in entry_line:
            if color:
                lines.append("%s%s%s%s:" % (ANSIColors.MAGENTA, varname, iterators, ANSIColors.RESET))
            else:
                lines.append("%s%s:" % (varname, iterators))
            s = value.tostring()
            sublines = s.split('\n')
            if len(sublines) > 5:
                sublines = value.tostring(short=True).split('\n')
            for line in sublines:
                lines.append("    " + line)
    lines.append('')
    return lines

def format_p4error(e, file_content, color=None, spec_dirname=None):
    """
    Format a P4Error exception with traceback information.

    Args:
        e: P4Error exception to format
        file_content: List of [filenames, contents] or dict with filename keys and file content (str) as values
        color: Whether to include ANSI color codes. If None, auto-detects TTY
        spec_dirname: Absolute path to join with relative file paths

    Returns:
        str: Formatted error message with traceback
    """
    if color is None:
        color = can_colorize()

    lines = []

    # Add traceback first if available
    if e.traceback.frames:
        file_content_dict = file_content

        traceback_lines = e.traceback.format(file_content_dict, color=color, ctx=e.ctx, spec_dirname=spec_dirname)
        lines.extend(traceback_lines)

    # Add the error message at the bottom
    lines.append(e.format(color=color))

    return '\n'.join(lines)
