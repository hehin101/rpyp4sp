import sys

def safe_slice(s, start=0, stop=sys.maxint):
    assert start >= 0
    assert stop >= 0
    if stop == sys.maxint:
        return s[start:]
    else:
        return s[start:stop]

class P4Error(Exception):
    def __init__(self, msg, region=None):
        self.msg = msg
        self.traceback = Traceback()
        self.region = region

    def maybe_add_region(self, region):
        if region is None or not region.has_information():
            return
        if self.region is None or not self.region.has_information():
            self.region = region

    def traceback_add_frame(self, name, region, ast):
        self.traceback.add_frame(name, region, ast)

    def format(self, color=False):
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

def extract_line(region, file_content):
    """
    Extract the line specified by a region from file content.

    Args:
        region: A Region object
        file_content: Dict with filename keys and file content (str) as values

    Returns:
        str: The line content if region is a line_span and file exists, None otherwise
    """
    if region is None:
        return None

    if not region.is_line_span():
        return None

    filename = region.left.file
    if filename not in file_content:
        return None

    content = file_content[filename]
    lines = content.splitlines()

    # Convert to 0-based indexing (region uses 1-based line numbers)
    line_number = region.left.line - 1

    if line_number < 0 or line_number >= len(lines):
        return None

    return lines[line_number]


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

    def _format_entry(self, name, region, file_content, color=False):
        """
        Format a single traceback entry.

        Args:
            name: Function/context name
            region: Region object
            file_content: Dict with filename keys and file content (str) as values
            color: Whether to include ANSI color codes

        Returns:
            list of str: Lines representing the formatted traceback entry
        """
        lines = []

        if region is None or not region.has_information():
            if color:
                lines.append('  File %s"%s"%s, line %s%s%s, in %s' % (
                    ANSIColors.MAGENTA, "<unknown>", ANSIColors.RESET,
                    ANSIColors.MAGENTA, "?", ANSIColors.RESET, name))
            else:
                lines.append('  File "<unknown>", line ?, in %s' % name)
            return lines

        filename = region.left.file if region.left.has_information() and region.left.file else "<unknown>"
        line_num = str(region.left.line) if region.left.has_information() else "?"

        if color:
            lines.append('  File %s"%s"%s, line %s%s%s, in %s' % (
                ANSIColors.MAGENTA, filename, ANSIColors.RESET,
                ANSIColors.MAGENTA, line_num, ANSIColors.RESET, name))
        else:
            lines.append('  File "%s", line %s, in %s' % (filename, line_num, name))

        # Try to extract and display the source line
        source_line = extract_line(region, file_content)
        if source_line is not None:
            # Regularize indentation - strip leading whitespace and add 4 spaces
            stripped_line = source_line.lstrip()

            # Color the source line if color is enabled and we have region info
            if color and region.is_line_span() and region.left.has_information() and region.right.has_information():
                start_col = region.left.column
                end_col = region.right.column
                original_indent = len(source_line) - len(stripped_line)
                adjusted_start_col = max(1, start_col - original_indent)
                adjusted_end_col = max(adjusted_start_col, end_col - original_indent)

                # Only color if it doesn't cover the entire non-empty line
                stripped_line_length = len(stripped_line.rstrip())
                if not (adjusted_start_col == 1 and adjusted_end_col >= stripped_line_length):
                    # Color the highlighted portion
                    before = safe_slice(stripped_line, 0, adjusted_start_col - 1)
                    highlighted = safe_slice(stripped_line, adjusted_start_col - 1, adjusted_end_col)
                    after = safe_slice(stripped_line, adjusted_end_col)
                    colored_line = before + ANSIColors.BOLD_RED + highlighted + ANSIColors.RESET + after
                    lines.append('    %s' % colored_line)
                else:
                    # Full line coverage - no coloring
                    lines.append('    %s' % stripped_line)
            else:
                lines.append('    %s' % stripped_line)

            # Add caret indicator if it's a line span with column information
            if region.is_line_span() and region.left.has_information() and region.right.has_information():
                start_col = region.left.column
                end_col = region.right.column

                # Adjust column positions based on how much whitespace was stripped
                original_indent = len(source_line) - len(stripped_line)
                adjusted_start_col = max(1, start_col - original_indent)
                adjusted_end_col = max(adjusted_start_col, end_col - original_indent)

                # Create caret line with appropriate spacing and carets
                if start_col > 0 and end_col >= start_col and adjusted_start_col > 0 and adjusted_end_col >= adjusted_start_col:
                    # Skip carets if they would cover the entire non-empty line
                    stripped_line_length = len(stripped_line.rstrip())  # Remove trailing whitespace for length check
                    if not (adjusted_start_col == 1 and adjusted_end_col >= stripped_line_length):
                        caret_line = '    ' + ' ' * (adjusted_start_col - 1)
                        if adjusted_end_col > adjusted_start_col:
                            carets = '^' * (adjusted_end_col - adjusted_start_col + 1)
                        else:
                            carets = '^'

                        if color:
                            caret_line += ANSIColors.BOLD_RED + carets + ANSIColors.RESET
                        else:
                            caret_line += carets
                        lines.append(caret_line)

        return lines

    def format(self, file_content, color=False):
        """
        Format the complete traceback.

        Args:
            file_content: Dict with filename keys and file content (str) as values
            color: Whether to include ANSI color codes

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

        for name, region, ast in reversed_frames:
            entry_lines = self._format_entry(name, region, file_content, color=color)

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

        return all_lines


def format_p4error(e, file_content, color=None):
    """
    Format a P4Error exception with traceback information.

    Args:
        e: P4Error exception to format
        file_content: List of [filenames, contents] or dict with filename keys and file content (str) as values
        color: Whether to include ANSI color codes. If None, auto-detects TTY

    Returns:
        str: Formatted error message with traceback
    """
    if color is None:
        color = can_colorize()

    lines = []

    # Add traceback first if available
    if e.traceback.frames:
        # Convert file_content to dict format if it's a list of [filenames, contents]
        if isinstance(file_content, list) and len(file_content) == 2:
            filenames, contents = file_content
            file_content_dict = dict(zip(filenames, contents))
        else:
            file_content_dict = file_content

        traceback_lines = e.traceback.format(file_content_dict, color=color)
        lines.extend(traceback_lines)

    # Add the error message at the bottom
    lines.append(e.format(color=color))

    return '\n'.join(lines)
