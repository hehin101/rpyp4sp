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

class Traceback(object):
    def __init__(self):
        self.frames = []

    def add_frame(self, name, ast):
        self.frames.append((name, ast.region, ast))
