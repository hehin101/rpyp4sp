from rpyp4sp import p4specast, objects, smalllist
from rpyp4sp.error import P4ContextError

class GlobalContext(object):
    file_content = {}
    spec_dirname = None

    def __init__(self):
        self.tdenv = {}
        self.renv = {}
        self.fenv = {}


class EnvKeys(object):
    def __init__(self, keys):
        self.keys = keys # type: dict[tuple[str, str], int]
        self.next_env_keys = {} # type: dict[tuple[str, str], EnvKeys]

    # TODO: default für var_iter
    def get_pos(self, var_name, var_iter):
        # type: (str, str) -> int
        return self.keys.get((var_name, var_iter), -1)

    # TODO: default für var_iter
    def add_key(self, var_name, var_iter):
        # type: (str, str) -> EnvKeys
        key = (var_name, var_iter)
        res = self.next_env_keys.get(key)
        if res is not None:
            return res
        else:
            keys = self.keys.copy()
            keys[key] = len(keys)
            res = EnvKeys(keys)
            self.next_env_keys[key] = res
            return res

    def __repr__(self):
        l = ["EnvKeys.EMPTY"]
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

EnvKeys.EMPTY = EnvKeys({})

class TDenvDict(object):
    def __init__(self, keys=EnvKeys.EMPTY, typdefs=None):
        self._keys = keys # type: EnvKeys
        self._typdefs = [] if typdefs is None else typdefs # type: list[p4specast.DefTyp]

    def get(self, id_value):
        # type: (str) -> p4specast.DefTyp
        pos = self._keys.get_pos(id_value, '')
        if pos < 0:
            raise P4ContextError('id_value %s does not exist' % (id_value))
        return self._typdefs[pos]

    def set(self, id_value, typdef):
        # type: (str, p4specast.DefTyp) -> TDenvDict
        pos = self._keys.get_pos(id_value, '')
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
        pos = self._keys.get_pos(id_value, '')
        return pos >= 0

    def bindings(self):
        # type: () -> list[tuple[str, tuple[list, p4specast.DefTyp]]]
        bindings = []
        for ((id_value, _), pos) in self._keys.keys.items():
            bindings.append((id_value, self._typdefs[pos]))
        return bindings

    def __repr__(self):
        l = ["context.TDenvDict.EMPTY"]
        for id_value, _ in self._keys.keys:
            pos = self._keys.get_pos(id_value, '')
            typdef = self._typdefs[pos]
            l.append(".set(%r, %r)" % (id_value, typdef))
        return "".join(l)

    def __str__(self):
        l = ["<tdenv "]
        for index, (id_value, _) in enumerate(self._keys.keys):
            pos = self._keys.get_pos(id_value, '')
            typdef = self._typdefs[pos]
            if index == 0:
                l.append("%r: %r" % (id_value, typdef))
            else:
                l.append(", %r: %r" % (id_value, typdef))
        l.append(">")
        return "".join(l)

TDenvDict.EMPTY = TDenvDict()

class FenvDict(object):
    def __init__(self, keys=EnvKeys.EMPTY, funcs=None):
        self._keys = keys # type: EnvKeys
        self._funcs = [] if funcs is None else funcs # type: list[p4specast.DecD]

    def get(self, id_value):
        # type: (str) -> p4specast.DecD
        pos = self._keys.get_pos(id_value, '')
        if pos < 0:
            raise P4ContextError('id_value %s does not exist' % (id_value))
        return self._funcs[pos]

    def set(self, id_value, func):
        # type: (str, p4specast.DecD) -> FenvDict
        pos = self._keys.get_pos(id_value, '')
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
        pos = self._keys.get_pos(id_value, '')
        return pos >= 0

    def __repr__(self):
        l = ["context.FenvDict()"]
        for id_value, _ in self._keys.keys:
            pos = self._keys.get_pos(id_value, '')
            func = self._funcs[pos]
            l.append(".set(%r, %r)" % (id_value, func))
        return "".join(l)

    def __str__(self):
        l = ["<fenv "]
        for index, (id_value, _) in enumerate(self._keys.keys):
            pos = self._keys.get_pos(id_value, '')
            func = self._funcs[pos]
            if index == 0:
                l.append("%r: %r" % (id_value, func))
            else:
                l.append(", %r: %r" % (id_value, func))
        l.append(">")
        return "".join(l)

@smalllist.inline_small_list(immutable=True)
class Context(object):
    def __init__(self, filename, derive=False, glbl=None, tdenv=None, fenv=None, venv_keys=None):
        self.filename = filename
        self.glbl = GlobalContext() if glbl is None else glbl
        # the local context is inlined
        self.derive = derive
        self.tdenv = tdenv if tdenv is not None else TDenvDict.EMPTY
        self.fenv = fenv if fenv is not None else FenvDict()
        self.venv_keys = venv_keys if venv_keys is not None else EnvKeys.EMPTY # type: EnvKeys

    def copy_and_change(self, tdenv=None, fenv=None, venv_keys=None, venv_values=None):
        tdenv = tdenv if tdenv is not None else self.tdenv
        fenv = fenv if fenv is not None else self.fenv
        venv_keys = venv_keys if venv_keys is not None else self.venv_keys
        venv_values = venv_values if venv_values is not None else self._get_full_list()
        return Context.make(venv_values, self.filename, self.derive, self.glbl, tdenv, fenv, venv_keys)

    def copy_and_change_append_venv(self, value, venv_keys):
        return self._append_list(value, self.filename, self.derive, self.glbl, self.tdenv, self.fenv, venv_keys)

    def load_spec(self, spec, file_content, spec_dirname):
        self.glbl.file_content = file_content
        self.glbl.spec_dirname = spec_dirname
        for definition in spec:
            if isinstance(definition, p4specast.TypD):
                self.glbl.tdenv[definition.id.value] = (definition.tparams, definition.deftyp)
            elif isinstance(definition, p4specast.RelD):
                self.glbl.renv[definition.id.value] = definition
            else:
                assert isinstance(definition, p4specast.DecD)
                self.glbl.fenv[definition.id.value] = definition

    def localize(self):
        return self.copy_and_change(tdenv=TDenvDict.EMPTY, fenv=FenvDict(), venv_keys=EnvKeys.EMPTY, venv_values=[])

    def localize_venv(self, venv_keys, venv_values):
        # type: (EnvKeys, list[objects.BaseV]) -> Context
        return self.copy_and_change(venv_keys=venv_keys, venv_values=venv_values)

    def find_value_local(self, id, iterlist=p4specast.IterList.EMPTY, vare_cache=None):
        # type: (p4specast.Id, list[p4specast.Iter], p4specast.VarE | None) -> objects.BaseV
        var_iter = iterlist.to_key()
        if vare_cache is not None and vare_cache._ctx_keys is self.venv_keys:
            pos = vare_cache._ctx_index
        else:
            pos = self.venv_keys.get_pos(id.value, var_iter)
            if vare_cache is not None:
                vare_cache._ctx_index = pos
                vare_cache._ctx_keys = self.venv_keys
        if pos < 0:
            raise P4ContextError('id_value %s%s does not exist' % (id.value, var_iter))
        return self._get_list(pos)

    def bound_value_local(self, id, iterlist):
        # type: (p4specast.Id, list[p4specast.Iter]) -> bool
        pos = self.venv_keys.get_pos(id.value, iterlist.to_key())
        return pos >= 0

    # TODO: why Id and not Tparam?
    def find_typdef_local(self, id):
        # type: (p4specast.Id) -> tuple[list, p4specast.DefTyp]
        if self.tdenv.has_key(id.value):
            typdef = self.tdenv.get(id.value)
        else:
            typdef =  self.glbl.tdenv[id.value]
        return typdef

    def find_rel_local(self, id):
        return self.glbl.renv[id.value]

    def add_value_local(self, id, iterlist, value, vare_cache=None):
        # type: (p4specast.Id, list, objects.BaseV, p4specast.VarE | None) -> Context
        if vare_cache is not None and vare_cache._ctx_keys_add is self.venv_keys:
            venv_keys = vare_cache._ctx_keys_next
            return self.copy_and_change_append_venv(value, venv_keys)
        var_iter = iterlist.to_key()
        pos = self.venv_keys.get_pos(id.value, var_iter)
        if pos < 0:
            venv_keys = self.venv_keys.add_key(id.value, var_iter)
            if vare_cache:
                vare_cache._ctx_keys_add = self.venv_keys
                vare_cache._ctx_keys_next = venv_keys
            return self.copy_and_change_append_venv(value, venv_keys)
        else:
            venv_values = self._get_full_list_copy()
            venv_values[pos] = value
            return self.copy_and_change(venv_values=venv_values)

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
            value = self.find_value_local(var.id, var.iter.append_list())
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

    def _venv_str(self):
        l = ["<venv "]
        for index, (var_name, var_iter) in enumerate(self.venv_keys.keys):
            pos = self.venv_keys.get_pos(var_name, var_iter)
            value = self._get_list(pos)
            if index == 0:
                l.append("%r: %r" % (var_name + var_iter, value))
            else:
                l.append(", %r: %r" % (var_name + var_iter, value))
        l.append(">")
        return "".join(l)

    def venv_items(self):
        res = []
        for key, index in self.venv_keys.keys.items():
            res.append((key, self._get_list(index)))
        return res


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



