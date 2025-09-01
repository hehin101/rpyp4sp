from rpyp4sp import p4specast

class GlobalContext(object):
    def __init__(self):
        self.tdenv = {}
        self.renv = {}
        self.fenv = {}

class LocalContext(object):
    def __init__(self):
        self.values_input = []
        self.tdenv = {}
        self.fenv = {}
        self.venv = {}

class Context(object):
    def __init__(self, filename, derive=False):
        self.filename = filename
        self.glbl = GlobalContext()
        self.local = LocalContext()
        self.derive = derive

    def load_spec(self, spec):
        for definition in spec:
            if isinstance(definition, p4specast.TypD):
                self.glbl.tdenv[definition.id.value] = definition
            elif isinstance(definition, p4specast.RelD):
                self.glbl.renv[definition.id.value] = definition
            else:
                assert isinstance(definition, p4specast.DecD)
                self.glbl.fenv[definition.id.value] = definition



