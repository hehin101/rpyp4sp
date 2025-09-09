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

    def localize(self):
        ctx = Context(self.filename, self.derive)
        ctx.glbl = self.glbl
        ctx.local = LocalContext()
        return ctx

    def find_value_local(self, id, iterlist):
        assert iterlist == []
        return self.local.venv[id.value]

    def find_typdef_local(self, id):
        # TODO: actually use the local tdenv
        decl = self.glbl.tdenv[id.value]
        return decl.tparams, decl.deftyp

    def add_value_local(self, id, iterlist, value):
        assert iterlist == []
        result = Context(self.filename, self.derive)
        result.glbl = self.glbl
        result.local = LocalContext()
        result.local.tdenv = self.local.tdenv
        result.local.fenv = self.local.fenv
        result.local.venv = self.local.venv.copy()
        result.local.venv[id.value] = value        
        return result
    
    def find_func_local(self, id):
        if id.value in self.local.fenv:
            func = self.local.fenv[id.value]
        else:
            func = self.glbl.fenv[id.value]
        return func

