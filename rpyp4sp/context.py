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


class EnvKeys(object):
    def __init__(self, keys):
        self.keys = keys # type: dict[tuple[str, str], int]
        self.next_venv_keys = {} # type: dict[tuple[str, str], EnvKeys]
        self._next_var_name = None
        self._next_var_iter = None
        self._next_env_keys = None

    # TODO: default für var_iter
    @jit.elidable
    def get_pos(self, var_name, var_iter):
        # type: (str, str) -> int
        return self.keys.get((var_name, var_iter), -1)

    # TODO: default für var_iter
    @jit.elidable
    def add_key(self, var_name, var_iter):
        # type: (str, str) -> EnvKeys
        if (self._next_var_name is not None and 
                self._next_var_name == var_name and
                self._next_var_iter == var_iter):
            return self._next_env_keys
        key = (var_name, var_iter)
        res = self.next_venv_keys.get(key)
        if res is not None:
            return res
        else:
            keys = self.keys.copy()
            keys[key] = len(keys)
            res = EnvKeys(keys)
            self.next_venv_keys[key] = res
            if self._next_env_keys is None:
                self._next_var_name = var_name
                self._next_var_iter = var_iter
                self._next_env_keys = res
            return res

    def __repr__(self):
        l = ["context.ENV_KEYS_ROOT"]
        for var_name, var_iter in self.keys:
            l.append(".add_key(%r, %r)" % (var_name, var_iter))
        return "".join(l)

    def __str__(self):
        l = ["<keys "]
        for index, (var_name, var_iter) in enumerate(self.keys):
            if index == 0:
                l.append("%r" % (var_name + var_iter))
            else:
                l.append(", %r" % (var_name + var_iter))
        l.append(">")
        return "".join(l)

ENV_KEYS_ROOT = EnvKeys({})

class TDenvDict(object):
    def __init__(self, keys=ENV_KEYS_ROOT, typdefs=None):
        self._keys = keys # type: EnvKeys
        self._typdefs = [] if typdefs is None else typdefs # type: list[p4specast.DefTyp]

    def get(self, id_value):
        # type: (str) -> p4specast.DefTyp
        pos = jit.promote(self._keys).get_pos(id_value, '')
        if pos < 0:
            raise P4ContextError('id_value %s does not exist' % (id_value))
        return self._typdefs[pos]

    def set(self, id_value, typdef):
        # type: (str, p4specast.DefTyp) -> TDenvDict
        pos = jit.promote(self._keys).get_pos(id_value, '')
        jit.promote(len(self._typdefs))
        if pos < 0:
            keys = self._keys.add_key(id_value, '')
            typdefs = self._typdefs + [typdef]
            return TDenvDict(keys, typdefs)
        else:
            typdefs = self._typdefs[:]
            typdefs[pos] = typdef
            return TDenvDict(self._keys, typdefs)

    def has_key(self, id_value):
        # type: (str) -> bool
        pos = jit.promote(self._keys).get_pos(id_value, '')
        return pos >= 0

    def bindings(self):
        # type: () -> list[tuple[str, tuple[list, p4specast.DefTyp]]]
        bindings = []
        for ((id_value, _), pos) in self._keys.keys.items():
            bindings.append((id_value, self._typdefs[pos]))
        return bindings

    def __repr__(self):
        l = ["context.TDenvDict()"]
        for id_value, _ in self._keys.keys:
            pos = jit.promote(self._keys).get_pos(id_value, '')
            typdef = self._typdefs[pos]
            l.append(".set(%r, %r)" % (id_value, typdef))
        return "".join(l)

    def __str__(self):
        l = ["<tdenv "]
        for index, (id_value, _) in enumerate(self._keys.keys):
            pos = jit.promote(self._keys).get_pos(id_value, '')
            typdef = self._typdefs[pos]
            if index == 0:
                l.append("%r: %r" % (id_value, typdef))
            else:
                l.append(", %r: %r" % (id_value, typdef))
        l.append(">")
        return "".join(l)

class FenvDict(object):
    def __init__(self, keys=ENV_KEYS_ROOT, funcs=None):
        self._keys = keys # type: EnvKeys
        self._funcs = [] if funcs is None else funcs # type: list[p4specast.DecD]

    def get(self, id_value):
        # type: (str) -> p4specast.DecD
        pos = jit.promote(self._keys).get_pos(id_value, '')
        if pos < 0:
            raise P4ContextError('id_value %s does not exist' % (id_value))
        return self._funcs[pos]

    def set(self, id_value, func):
        # type: (str, p4specast.DecD) -> FenvDict
        jit.promote(len(self._funcs))
        pos = jit.promote(self._keys).get_pos(id_value, '')
        if pos < 0:
            keys = self._keys.add_key(id_value, '')
            funcs = self._funcs + [func]
            return FenvDict(keys, funcs)
        else:
            funcs = self._funcs[:]
            funcs[pos] = func
            return FenvDict(self._keys, funcs)

    def has_key(self, id_value):
        # type: (str) -> bool
        pos = jit.promote(self._keys).get_pos(id_value, '')
        return pos >= 0

    def __repr__(self):
        l = ["context.FenvDict()"]
        for id_value, _ in self._keys.keys:
            pos = jit.promote(self._keys).get_pos(id_value, '')
            func = self._funcs[pos]
            l.append(".set(%r, %r)" % (id_value, func))
        return "".join(l)

    def __str__(self):
        l = ["<fenv "]
        for index, (id_value, _) in enumerate(self._keys.keys):
            pos = jit.promote(self._keys).get_pos(id_value, '')
            func = self._funcs[pos]
            if index == 0:
                l.append("%r: %r" % (id_value, func))
            else:
                l.append(", %r: %r" % (id_value, func))
        l.append(">")
        return "".join(l)

class VenvDict(object):
    def __init__(self, keys=ENV_KEYS_ROOT, values=None):
        self._keys = keys # type: EnvKeys
        self._values = [] if values is None else values # type: list[objects.BaseV]

    def get(self, var_name, var_iter, vare_cache=None):
        # type: (str, str, p4specast.VarE | None) -> objects.BaseV
        if not jit.we_are_jitted() and vare_cache is not None and vare_cache._ctx_keys is self._keys:
            pos = vare_cache._ctx_index
        else:
            pos = jit.promote(self._keys).get_pos(var_name, var_iter)
            if not jit.we_are_jitted() and vare_cache is not None:
                vare_cache._ctx_index = pos
                vare_cache._ctx_keys = self._keys
        if pos < 0:
            raise P4ContextError('id_value %s%s does not exist' % (var_name, var_iter))
        return self._values[pos]

    @jit.unroll_safe
    def set(self, var_name, var_iter, value):
        # type: (str, str, objects.BaseV) -> VenvDict
        pos = jit.promote(self._keys).get_pos(var_name, var_iter)
        values = self._values
        length = jit.promote(len(values))
        if pos < 0:
            keys = jit.promote(self._keys).add_key(var_name, var_iter)
            newvalues = [None] * (length + 1)
            for i in range(length):
                newvalues[i] = values[i]
            newvalues[length] = value
            return VenvDict(keys, newvalues)
        else:
            values = self._values[:]
            values[pos] = value
            return VenvDict(self._keys, values)

    def has_key(self, var_name, var_iter):
        # type: (str, str) -> bool
        pos = jit.promote(self._keys).get_pos(var_name, var_iter)
        return pos >= 0

    def __repr__(self):
        l = ["context.VenvDict()"]
        for var_name, var_iter in self._keys.keys:
            pos = self._keys.get_pos(var_name, var_iter)
            value = self._values[pos]
            l.append(".set(%r, %r, %r)" % (var_name, var_iter, value))
        return "".join(l)

    def __str__(self):
        l = ["<venv "]
        for index, (var_name, var_iter) in enumerate(self._keys.keys):
            pos = self._keys.get_pos(var_name, var_iter)
            value = self._values[pos]
            if index == 0:
                l.append("%r: %r" % (var_name + var_iter, value))
            else:
                l.append(", %r: %r" % (var_name + var_iter, value))
        l.append(">")
        return "".join(l)

class Context(object):
    def __init__(self, filename, derive=False, glbl=None, values_input=None, tdenv=None, fenv=None, venv=None):
        self.filename = filename
        self.glbl = GlobalContext() if glbl is None else glbl
        # the local context is inlined
        self.derive = derive
        self.values_input = values_input if values_input is not None else []
        self.tdenv = tdenv if tdenv is not None else TDenvDict()
        self.fenv = fenv if fenv is not None else FenvDict()
        self.venv = venv if venv is not None else VenvDict()

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
        return self.copy_and_change(tdenv=TDenvDict(), fenv=FenvDict(), venv=VenvDict())

    def localize_inputs(self, values_input):
        # tpye: (VenvDict) -> Context
        return self.copy_and_change(values_input=values_input)

    def localize_venv(self, venv):
        return self.copy_and_change(venv=venv)

    def find_value_local(self, id, iterlist, vare_cache=None):
        # type: (p4specast.Id, list[p4specast.Iter], p4specast.VarE | None) -> objects.BaseV
        jit.promote(id)
        return self.venv.get(id.value, iterlist_to_key(iterlist), vare_cache)

    def bound_value_local(self, id, iterlist):
        # type: (p4specast.Id, list[p4specast.Iter]) -> bool
        jit.promote(id)
        return self.venv.has_key(id.value, iterlist_to_key(iterlist))

    # TODO: why Id and not Tparam?
    def find_typdef_local(self, id):
        # type: (p4specast.Id) -> tuple[list, p4specast.DefTyp]
        if self.tdenv.has_key(id.value):
            typdef = self.tdenv.get(id.value)
        else:
            typdef = jit.promote(self.glbl).tdenv[id.value]
        return typdef

    def find_rel_local(self, id):
        res = jit.promote(self.glbl)._find_rel(id.value)
        if res is None:
            raise P4ContextError("rel %s not found" % id.value)
        return res

    def add_value_local(self, id, iterlist, value):
        # type: (p4specast.Id, list, objects.BaseV) -> Context
        venv = self.venv.set(id.value, iterlist.to_key(), value)
        result = self.copy_and_change(venv=venv)
        return result

    def add_func_local(self, id, func):
        # type: (p4specast.Id, p4specast.DecD) -> Context
        fenv = self.fenv.set(id.value, func)
        result = self.copy_and_change(fenv=fenv)
        return result

    def add_typdef_local(self, id, typdef):
        # type: (p4specast.TParam, tuple[list[p4specast.TParam], p4specast.DefTyp]) -> Context
        tdenv = self.tdenv.set(id.value, typdef)
        result = self.copy_and_change(tdenv=tdenv)
        return result

    def find_func_local(self, id):
        # type: (p4specast.Id) -> p4specast.DecD
        if self.fenv.has_key(id.value):
            func = self.fenv.get(id.value)
        else:
            func = jit.promote(self.glbl)._find_func(id.value)
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
            value = self.find_value_local(var.id, var.iter.append_opt())
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

    @jit.unroll_safe
    def sub_list(self, vars):
        # this is unroll_safe because vars comes from an ast, so is
        # constant-sized.

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
            value = self.find_value_local(var.id, var.iter.append_list())
            value_list = value.get_list()
            if first_list is not None:
                if len(first_list) != len(value_list):
                    raise P4ContextError("cannot transpose a matrix of value batches")
            else:
                first_list = value_list
            values_batch.append(value_list)
        assert first_list is not None
        return SubListIter(self, vars, len(first_list), values_batch)


class SubListIter(object):
    def __init__(self, ctx, vars, length, values_batch):
        self.vars = vars
        self.length = length
        self.j = 0
        self.values_batch = values_batch
        self.ctx = ctx

    def __iter__(self):
        return self

    @jit.unroll_safe
    def next(self):
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
        if self.j >= self.length:
            raise StopIteration
        ctx_sub = self.ctx
        for i, var in enumerate(self.vars):
            value = self.values_batch[i][self.j]
            ctx_sub = ctx_sub.add_value_local(var.id, var.iter, value)
        self.j += 1
        return ctx_sub

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



