from rpython.rlib import jit
from rpyp4sp import p4specast, objects
from rpyp4sp.error import P4ContextError

class GlobalContext(object):
    def __init__(self):
        self.tdenv = {}
        self.renv = {}
        self.fenv = {}

    @jit.elidable
    def _find_rel(self, name):
        return self.renv.get(name, None)

    @jit.elidable
    def _find_func(self, name):
        return self.fenv.get(name, None)

    @jit.elidable
    def _find_typdef(self, name):
        return self.tdenv.get(name, (None, None))



def iterlist_to_key(l):
    if not l:
        return ''
    return _iterlist_to_key(l)

@jit.unroll_safe
def _iterlist_to_key(l):
    key = []
    for iter in l:
        if isinstance(iter, p4specast.Opt):
            key.append('?')
        else:
            assert isinstance(iter, p4specast.List)
            key.append('*')
    return ''.join(key)

class VenvKeys(object):
    def __init__(self, keys):
        self.keys = keys # type: dict[tuple[str, str], int]
        self.next_venv_keys = {} # type: dict[tuple[str, str], VenvKeys]

    def get_pos(self, var_name, var_iter):
        return self.keys.get((var_name, var_iter), -1)
    
    def add_key(self, var_name, var_iter):
        key = (var_name, var_iter)
        res = self.next_venv_keys.get(key)
        if res is not None:
            return res
        else:
            keys = self.keys.copy()
            keys[key] = len(keys)
            res = VenvKeys(keys)
            self.next_venv_keys[key] = res
            return res
        
    def __repr__(self):
        l = ["context.VENV_KEYS_ROOT"]
        for var_name, var_iter in self.keys:
            l.append(".add_key(%r, %r)" % (var_name, var_iter))
        return "".join(l)
    
    def __str__(self):
        l = ["<keys "]
        for var_name, var_iter in self.keys:
            l.append("%r" % (var_name + var_iter))
        l.append(">")
        return "".join(l)

VENV_KEYS_ROOT = VenvKeys({})

class VenvDict(object):
    def __init__(self, keys=VENV_KEYS_ROOT, values=None):
        self._keys = keys
        self._values = [] if values is None else values

    def get(self, var_name, var_iter):
        pos = self._keys.get_pos(var_name, var_iter)
        if pos < 0:
            raise P4ContextError('var_name %s%s does not exist' % (var_name, var_iter))
        return self._values[pos]

    def set(self, var_name, var_iter, value):
        # type: (str, str, objects.BaseV) -> VenvDict
        pos = self._keys.get_pos(var_name, var_iter)
        if pos < 0:
            keys = self._keys.add_key(var_name, var_iter)
            values = self._values + [value]
            return VenvDict(keys, values)
        else:
            values = self._values[:]
            values[pos] = value
            return VenvDict(self._keys, values)

class Context(object):
    def __init__(self, filename, derive=False, glbl=None, values_input=None, tdenv=None, fenv=None, venv=None):
        self.filename = filename
        self.glbl = GlobalContext() if glbl is None else glbl
        # the local context is inlined
        self.derive = derive
        self.values_input = values_input if values_input is not None else []
        self.tdenv = tdenv if tdenv is not None else {}
        self.fenv = fenv if fenv is not None else {}
        self.venv = venv if venv is not None else {}

    def copy_and_change(self, values_input=None, tdenv=None, fenv=None, venv=None):
        values_input = values_input if values_input is not None else self.values_input
        tdenv = tdenv if tdenv is not None else self.tdenv
        fenv = fenv if fenv is not None else self.fenv
        venv = venv if venv is not None else self.venv
        return Context(self.filename, self.derive, self.glbl, values_input, tdenv, fenv, venv)

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
        return self.copy_and_change(tdenv={}, fenv={}, venv={})

    def localize_inputs(self, values_input):
        return self.copy_and_change(values_input=values_input)
    
    def localize_venv(self, venv):
        return self.copy_and_change(venv=venv)

    def find_value_local(self, id, iterlist):
        return self.venv[id.value, iterlist_to_key(iterlist)]

    def bound_value_local(self, id, iterlist):
        return (id.value, iterlist_to_key(iterlist)) in self.venv

    def find_typdef_local(self, id):
        # TODO: actually use the local tdenv
        jit.promote(self.glbl)
        tup = self.glbl._find_typdef(id.value)
        if tup[0] is None and tup[1] is None:
            raise P4ContextError("rel %s not found" % id.value)
        return tup

    def find_rel_local(self, id):
        res = jit.promote(self.glbl)._find_rel(id.value)
        if res is None:
            raise P4ContextError("rel %s not found" % id.value)
        return res

    def add_value_local(self, id, iterlist, value):
        result = self.copy_and_change(venv=self.venv.copy())
        result.venv[id.value, iterlist_to_key(iterlist)] = value
        return result

    def add_func_local(self, id, func):
        result = self.copy_and_change(fenv=self.fenv.copy())
        result.fenv[id.value] = func
        return result

    def add_typdef_local(self, id, typdef):
        result = self.copy_and_change(tdenv=self.tdenv.copy())
        result.tdenv[id.value] = typdef
        return result

    def find_func_local(self, id):
        if id.value in self.fenv:
            func = self.fenv[id.value]
        else:
            jit.promote(self.glbl)
            func = self.glbl._find_func(id.value)
            if func is None:
                raise P4ContextError('func %s not found' % id.value)
        return func

    def commit(self, sub_ctx):
        # TODO: later add cover
        return self

    @jit.unroll_safe
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
                value_sub = objects.OptV(value, var.typ)
                ctx_sub = ctx_sub.add_value_local(var.id, var.iter, value_sub.value)
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
        assert vars
        first_list = None
        for var in vars:
            value = self.find_value_local(var.id, var.iter + [p4specast.List()])
            value_list = value.get_list()
            if first_list is not None:
                if len(first_list) != len(value_list):
                    raise P4ContextError("cannot transpose a matrix of value batches")
            else:
                first_list = value_list
            values_batch.append(value_list)
        assert first_list is not None
        if len(first_list) == 0:
            return []
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
        for j in range(len(first_list)):
            ctx_sub = self
            for i, var in enumerate(vars):
                value = values_batch[i][j]
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



