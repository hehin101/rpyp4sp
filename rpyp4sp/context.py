from rpyp4sp import p4specast

class GlobalContext(object):
    def __init__(self):
        self.tdenv = {}
        self.renv = {}
        self.fenv = {}

class LocalContext(object):
    def __init__(self, values_input=None, tdenv=None, fenv=None, venv=None):
        self.values_input = values_input if values_input is not None else []
        self.tdenv = tdenv if tdenv is not None else {}
        self.fenv = fenv if fenv is not None else {}
        self.venv = venv if venv is not None else {}

    def copy_and_change(self, values_input=None, tdenv=None, fenv=None, venv=None):
        values_input = values_input if values_input is not None else self.values_input
        tdenv = tdenv if tdenv is not None else self.tdenv
        fenv = fenv if fenv is not None else self.fenv
        venv = venv if venv is not None else self.venv
        return LocalContext(values_input, tdenv, fenv, venv)
    

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

    def localize_inputs(self, values_input):
        ctx = Context(self.filename, self.derive)
        ctx.glbl = self.glbl
        ctx.local = ctx.local.copy_and_change(values_input=values_input)
        return ctx

    def find_value_local(self, id, iterlist):
        assert iterlist == []
        return self.local.venv[id.value]

    def find_typdef_local(self, id):
        # TODO: actually use the local tdenv
        decl = self.glbl.tdenv[id.value]
        return decl.tparams, decl.deftyp

    def find_rel_local(self, id):
        return self.glbl.renv[id.value]

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

