class P4Error(Exception):
    def __init__(self, msg):
        self.msg = msg

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
