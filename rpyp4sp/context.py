from rpyp4sp import p4specast, objects
from rpyp4sp.error import P4ContextError

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

def iterlist_to_key(l):
    if not l:
        return ''
    key = []
    for iter in l:
        if isinstance(iter, p4specast.Opt):
            key.append('?')
        else:
            assert isinstance(iter, p4specast.List)
            key.append('*')
    return ''.join(key)

class Context(object):
    def __init__(self, filename, derive=False):
        self.filename = filename
        self.glbl = GlobalContext()
        self.local = LocalContext()
        self.derive = derive

    def load_spec(self, spec):
        for definition in spec:
            if isinstance(definition, p4specast.TypD):
                self.glbl.tdenv[definition.id.value] = (definition.tparams, definition.deftyp)
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
    
    def localize_venv(self, venv):
        ctx = Context(self.filename, self.derive)
        ctx.glbl = self.glbl
        ctx.local = ctx.local.copy_and_change(venv=venv)
        return ctx

    def find_value_local(self, id, iterlist):
        return self.local.venv[id.value, iterlist_to_key(iterlist)]

    def bound_value_local(self, id, iterlist):
        return (id.value, iterlist_to_key(iterlist)) in self.local.venv

    def find_typdef_local(self, id):
        # TODO: actually use the local tdenv
        return self.glbl.tdenv[id.value]

    def find_rel_local(self, id):
        return self.glbl.renv[id.value]

    def add_value_local(self, id, iterlist, value):
        result = Context(self.filename, self.derive)
        result.glbl = self.glbl
        result.local = LocalContext()
        result.local.tdenv = self.local.tdenv
        result.local.fenv = self.local.fenv
        result.local.venv = self.local.venv.copy()
        result.local.venv[id.value, iterlist_to_key(iterlist)] = value
        return result

    def add_func_local(self, id, func):
        result = Context(self.filename, self.derive)
        result.glbl = self.glbl
        result.local = self.local.copy_and_change(fenv=self.local.fenv.copy())
        result.local.fenv[id.value] = func
        return result

    def add_typdef_local(self, id, typdef):
        result = Context(self.filename, self.derive)
        result.glbl = self.glbl
        result.local = self.local.copy_and_change(tdenv=self.local.tdenv.copy())
        result.local.tdenv[id.value] = typdef
        return result

    def find_func_local(self, id):
        if id.value in self.local.fenv:
            func = self.local.fenv[id.value]
        else:
            func = self.glbl.fenv[id.value]
        return func

    def commit(self, sub_ctx):
        # TODO: later add cover
        return self

    def sub_opt(self, vars):
        #   (* First collect the values that are to be iterated over *)
        #   let values =
        #     List.map
        #       (fun (id, _typ, iters) ->
        #         find_value Local ctx (id, iters @ [ Il.Ast.Opt ]) |> Value.get_opt)
        #       vars
        values = []
        for var in vars:
            value = self.find_value_local(var.id, var.iter + [p4specast.Opt()])
            assert isinstance(value, objects.OptV)
            values.append(value.value)
        # check whether they are all None, all Some, or mixed
        noneness = values[0] is None
        for value in values:
            if (value is None) != noneness:
                raise P4ContextError("mismatch in optionality of iterated variables")
        #   in
        #   (* Iteration is valid when all variables agree on their optionality *)
        #   if List.for_all Option.is_some values then
        #     let values = List.map Option.get values in
        #     let ctx_sub =
        #       List.fold_left2
        #         (fun ctx_sub (id, _typ, iters) value ->
        #           add_value Local ctx_sub (id, iters) value)
        #         ctx vars values
        #     in
        #     Some ctx_sub
        #   else if List.for_all Option.is_none values then None
        #   else error no_region "mismatch in optionality of iterated variables"
        if noneness:
            return None
        else:
            ctx_sub = self
            for i, var in enumerate(vars):
                value = values[i]
                assert value is not None
                value_sub = objects.OptV(value, typ=var.typ)
                ctx_sub = ctx_sub.add_value_local(var.id, var.iter + [p4specast.Opt()], value_sub)
            return ctx_sub


    def sub_list(self, vars):
        # First break the values that are to be iterated over,
        # into a batch of values
        #   let values_batch =
        #     List.map
        #       (fun (id, _typ, iters) ->
        #         find_value Local ctx (id, iters @ [ Il.Ast.List ]) |> Value.get_list)
        #       vars
        #     |> transpose
        values_batch = []
        for var in vars:
            value = self.find_value_local(var.id, var.iter + [p4specast.List()])
            values_batch.append(value.get_list())
        value_matrix = transpose(values_batch)
        #   in
        #   (* For each batch of values, create a sub-context *)
        #   List.fold_left
        #     (fun ctxs_sub value_batch ->
        #       let ctx_sub =
        #         List.fold_left2
        #           (fun ctx_sub (id, _typ, iters) value ->
        #             add_value Local ctx_sub (id, iters) value)
        #           ctx vars value_batch
        #       in
        #       ctxs_sub @ [ ctx_sub ])
        #     [] values_batch
        ctxs_sub = []
        for value_batch in value_matrix:
            ctx_sub = self
            for i, var in enumerate(vars):
                value = value_batch[i]
                ctx_sub = ctx_sub.add_value_local(var.id, var.iter, value)
            ctxs_sub.append(ctx_sub)
        return ctxs_sub


def transpose(value_matrix):
    if not value_matrix:
        # | [] -> []
        return []
    # | _ ->
    width = len(value_matrix[0])  # let width = List.length (List.hd value_matrix) in
    # check
    for value_row in value_matrix:
        if len(value_row) != width:
            raise P4ContextError("cannot transpose a matrix of value batches")
    # List.init width (fun j ->
    #     List.init (List.length value_matrix) (fun i ->
    #         List.nth (List.nth value_matrix i) j))
    return [[value_matrix[i][j] for i in range(len(value_matrix))] for j in range(width)]



