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

    def traceback_add_frame(self, name, ast):
        self.traceback.add_frame(name, ast)

    def format(self):
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


class Traceback(object):
    def __init__(self):
        self.frames = []

    def add_frame(self, name, ast):
        self.frames.append((name, ast.region, ast))

    def _format_entry(self, name, region, file_content):
        """
        Format a single traceback entry.

        Args:
            name: Function/context name
            region: Region object
            file_content: Dict with filename keys and file content (str) as values

        Returns:
            list of str: Lines representing the formatted traceback entry
        """
        lines = []

        if region is None or not region.has_information():
            lines.append('  File "<unknown>", line ?, in %s' % name)
            return lines

        filename = region.left.file if region.left.has_information() and region.left.file else "<unknown>"
        line_num = region.left.line if region.left.has_information() else "?"

        lines.append('  File "%s", line %s, in %s' % (filename, line_num, name))

        # Try to extract and display the source line
        source_line = extract_line(region, file_content)
        if source_line is not None:
            # Regularize indentation - strip leading whitespace and add 4 spaces
            stripped_line = source_line.lstrip()
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
                            caret_line += '^' * (adjusted_end_col - adjusted_start_col + 1)
                        else:
                            caret_line += '^'
                        lines.append(caret_line)

        return lines

    def format(self, file_content):
        """
        Format the complete traceback.

        Args:
            file_content: Dict with filename keys and file content (str) as values

        Returns:
            list of str: Lines representing the formatted traceback
        """
        if not self.frames:
            return []

        # Reverse the frames to show most recent call last
        reversed_frames = self.frames[:]
        reversed_frames.reverse()

        # Format all entries
        all_lines = []
        if reversed_frames:
            all_lines.append("Traceback (most recent call last):")

        for name, region, ast in reversed_frames:
            entry_lines = self._format_entry(name, region, file_content)
            all_lines.extend(entry_lines)

        return all_lines
