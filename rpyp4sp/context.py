from __future__ import print_function
from rpython.rlib import jit
from rpyp4sp import p4specast, objects, smalllist, sign
from rpyp4sp.cover import Coverage
from rpyp4sp.error import P4ContextError
from rpython.rlib import jit

class GlobalContext(object):
    file_content = {}
    spec_dirname = None

    def __init__(self):
        self.filename = None
        self.derive = False
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
        self.next_env_keys = {} # type: dict[tuple[str, str], EnvKeys]
        self._next_var_name = None
        self._next_var_iter = None
        self._next_env_keys = None

    # TODO: default für var_iter
    @jit.elidable
    def get_pos(self, var_name, var_iter):
        # type: (str, str) -> int
        if not self.keys:
            return -1
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
        res = self.next_env_keys.get(key)
        if res is not None:
            return res
        else:
            keys = self.keys.copy()
            keys[key] = len(keys)
            res = EnvKeys(keys)
            self.next_env_keys[key] = res
            if self._next_env_keys is None:
                self._next_var_name = var_name
                self._next_var_iter = var_iter
                self._next_env_keys = res
            return res

    def __repr__(self):
        l = ["context.EnvKeys.EMPTY"]
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

@smalllist.inline_small_list(immutable=True, nonull=True, append_list_unroll_safe=True)
class TDenvDict(object):
    _immutable_fields_ = ['_keys']
    def __init__(self, keys=EnvKeys.EMPTY):
        self._keys = keys # type: EnvKeys

    def get(self, id_value):
        # type: (str) -> tuple[list[p4specast.TParam], p4specast.DefTyp]
        pos = jit.promote(self._keys).get_pos(id_value, '')
        if pos < 0:
            raise P4ContextError('id_value %s does not exist' % (id_value))
        return self._get_list(pos)

    def set(self, id_value, typdef):
        # type: (str, tuple[list[p4specast.TParam], p4specast.DefTyp]) -> TDenvDict
        pos = jit.promote(self._keys).get_pos(id_value, '')
        jit.promote(self._get_size_list())
        if pos < 0:
            keys = self._keys.add_key(id_value, '')
            return self._append_list(typdef, keys)
        else:
            typdefs = self._get_full_list_copy()
            typdefs[pos] = typdef
            return TDenvDict.make(typdefs, self._keys)

    def has_key(self, id_value):
        # type: (str) -> bool
        pos = jit.promote(self._keys).get_pos(id_value, '')
        return pos >= 0

    def bindings(self):
        # type: () -> list[tuple[str, tuple[list[p4specast.TParam], p4specast.DefTyp]]]
        bindings = []
        for ((id_value, _), pos) in self._keys.keys.items():
            bindings.append((id_value, self._get_list(pos)))
        return bindings

    def __repr__(self):
        l = ["context.TDenvDict.EMPTY"]
        for id_value, _ in self._keys.keys:
            pos = jit.promote(self._keys).get_pos(id_value, '')
            typdef = self._get_list(pos)
            l.append(".set(%r, %r)" % (id_value, typdef))
        return "".join(l)

    def __str__(self):
        l = ["<tdenv "]
        for index, (id_value, _) in enumerate(self._keys.keys):
            pos = jit.promote(self._keys).get_pos(id_value, '')
            typdef = self._get_list(pos)
            if index == 0:
                l.append("%r: %r" % (id_value, typdef))
            else:
                l.append(", %r: %r" % (id_value, typdef))
        l.append(">")
        return "".join(l)
TDenvDict.EMPTY = TDenvDict()

TDenvDict.EMPTY = TDenvDict.make0()

@smalllist.inline_small_list(immutable=True, append_list_unroll_safe=True)
class FenvDict(object):
    _immutable_fields_ = ['_keys']
    def __init__(self, keys=EnvKeys.EMPTY):
        self._keys = keys # type: EnvKeys

    def get(self, id_value):
        # type: (str) -> p4specast.DecD
        pos = jit.promote(self._keys).get_pos(id_value, '')
        if pos < 0:
            raise P4ContextError('id_value %s does not exist' % (id_value))
        return self._get_list(pos)

    def set(self, id_value, func):
        # type: (str, p4specast.DecD) -> FenvDict
        jit.promote(self._get_size_list())
        pos = jit.promote(self._keys).get_pos(id_value, '')
        if pos < 0:
            keys = self._keys.add_key(id_value, '')
            return self._append_list(func, keys)
        else:
            funcs = self._get_full_list_copy()
            funcs[pos] = func
            return FenvDict.make(funcs, self._keys)

    def has_key(self, id_value):
        # type: (str) -> bool
        pos = jit.promote(self._keys).get_pos(id_value, '')
        return pos >= 0

    def __repr__(self):
        l = ["context.FenvDict.EMPTY"]
        for id_value, _ in self._keys.keys:
            pos = self._keys.get_pos(id_value, '')
            func = self._get_list(pos)
            l.append(".set(%r, %r)" % (id_value, func))
        return "".join(l)

    def __str__(self):
        l = ["<fenv "]
        for index, (id_value, _) in enumerate(self._keys.keys):
            pos = jit.promote(self._keys).get_pos(id_value, '')
            func = self._get_list(pos)
            if index == 0:
                l.append("%r: %r" % (id_value, func))
            else:
                l.append(", %r: %r" % (id_value, func))
        l.append(">")
        return "".join(l)
FenvDict.EMPTY = FenvDict()

FenvDict.EMPTY = FenvDict.make0()

@smalllist.inline_small_list(immutable=True, append_list_unroll_safe=True)
class Context(sign.Sign):
    _immutable_fields_ = ['glbl', 'values_input[*]',
                          'tdenv', 'fenv', 'venv_keys', 'cover']
    def __init__(self, glbl=None, tdenv=None, fenv=None, venv_keys=None, cover=None):
        self.glbl = GlobalContext() if glbl is None else glbl
        # the local context is inlined
        self.tdenv = tdenv if tdenv is not None else TDenvDict.EMPTY # type: TDenvDict
        self.fenv = fenv if fenv is not None else FenvDict.EMPTY # type: FenvDict
        self.venv_keys = venv_keys if venv_keys is not None else EnvKeys.EMPTY # type: EnvKeys
        self._cover = cover if cover is not None else Coverage.EMPTY
        assert isinstance(self._cover, Coverage)

    def copy_and_change(self, tdenv=None, fenv=None, venv_keys=None, venv_values=None, cover=None):
        tdenv = tdenv if tdenv is not None else self.tdenv
        fenv = fenv if fenv is not None else self.fenv
        venv_keys = venv_keys if venv_keys is not None else self.venv_keys
        venv_values = venv_values if venv_values is not None else self._get_full_list()
        cover = cover if cover is not None else self._cover
        return Context.make(venv_values, self.glbl, tdenv, fenv, venv_keys, cover)

    def copy_and_change_append_venv(self, value, venv_keys):
        return self._append_list(value, self.glbl, self.tdenv, self.fenv, venv_keys, self._cover)

    def load_spec(self, spec, file_content, spec_dirname, filename, derive=False):
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
        self.glbl.filename = filename
        self.derive = derive

    def localize(self):
        return self.copy_and_change(tdenv=TDenvDict.EMPTY, fenv=FenvDict.EMPTY, venv_keys=EnvKeys.EMPTY, venv_values=[])

    def localize_venv(self, venv_keys, venv_values):
        # type: (EnvKeys, list[objects.BaseV]) -> Context
        return self.copy_and_change(venv_keys=venv_keys, venv_values=venv_values)

    def find_value_local(self, id, iterlist=p4specast.IterList.EMPTY, vare_cache=None):
        # type: (p4specast.Id, list[p4specast.IterList], p4specast.VarE | None) -> objects.BaseV
        var_iter = iterlist.to_key()
        jit.promote(id)
        if not jit.we_are_jitted() and vare_cache is not None and vare_cache._ctx_keys is self.venv_keys:
            pos = vare_cache._ctx_index
        else:
            pos = jit.promote(self.venv_keys).get_pos(id.value, var_iter)
            if not jit.we_are_jitted() and vare_cache is not None:
                vare_cache._ctx_index = pos
                vare_cache._ctx_keys = self.venv_keys
        if pos < 0:
            raise P4ContextError('id_value %s%s does not exist' % (id.value, var_iter))
        return self._get_list(pos)

    def bound_value_local(self, id, iterlist):
        # type: (p4specast.Id, p4specast.IterList) -> bool
        jit.promote(id)
        pos = jit.promote(self.venv_keys).get_pos(id.value, iterlist.to_key())
        return pos >= 0

    def find_typdef_local(self, id, typ_cache=None):
        # type: (p4specast.Id) -> tuple[list[p4specast.TParam], p4specast.DefTyp]
        if not jit.we_are_jitted() and typ_cache and typ_cache._ctx_tdenv_keys is self.tdenv._keys:
            return typ_cache._ctx_typ_res
        if self.tdenv.has_key(id.value):
            typdef = self.tdenv.get(id.value)
        else:
            typdef = jit.promote(self.glbl)._find_typdef(id.value)
            if not jit.we_are_jitted() and typ_cache:
                typ_cache._ctx_tdenv_keys = self.tdenv._keys
                typ_cache._ctx_typ_res = typdef
        return typdef

    def find_rel_local(self, id):
        res = jit.promote(self.glbl)._find_rel(id.value)
        if res is None:
            raise P4ContextError("rel %s not found" % id.value)
        return res

    def add_value_local(self, id, iterlist, value, vare_cache=None):
        # type: (p4specast.Id, p4specast.IterList, objects.BaseV, p4specast.VarE | None) -> Context
        if not jit.we_are_jitted() and vare_cache is not None and vare_cache._ctx_keys_add is self.venv_keys:
            venv_keys = vare_cache._ctx_keys_next
            return self.copy_and_change_append_venv(value, venv_keys)
        var_iter = iterlist.to_key()
        venv_keys = jit.promote(self.venv_keys)
        length = jit.promote(self._get_size_list())
        pos = venv_keys.get_pos(id.value, var_iter)
        if pos < 0:
            venv_keys = self.venv_keys.add_key(id.value, var_iter)
            if not jit.we_are_jitted() and vare_cache:
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

    def find_func_local(self, id, calle_cache=None):
        # type: (p4specast.Id) -> p4specast.DecD
        if not jit.we_are_jitted() and calle_cache and calle_cache._ctx_fenv_keys is self.fenv._keys:
            return calle_cache._ctx_func_res
        if self.fenv.has_key(id.value):
            func = self.fenv.get(id.value)
        else:
            func = jit.promote(self.glbl)._find_func(id.value)
            if not jit.we_are_jitted() and calle_cache:
                calle_cache._ctx_fenv_keys = self.fenv._keys
                calle_cache._ctx_func_res = func
        return func

    def commit(self, sub_ctx):
        return self.copy_and_change(cover=self._cover.union(sub_ctx._cover))

    def cover(self, is_hit, phantom, value=None):
        if phantom is None:
            return self
        new_cover = self._cover.cover(is_hit, phantom, value)
        if new_cover is self._cover:
            return self
        return self.copy_and_change(cover=new_cover)

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
                ctx_sub = ctx_sub.add_value_local(var.id, var.iter, value)
            return ctx_sub

    @jit.unroll_safe
    def sub_list(self, varlist):
        from rpyp4sp import interp
        # type: (interp.VarList) -> SubListIter
        # this is unroll_safe because varlist comes from an ast, so is
        # constant-sized.

        # First break the values that are to be iterated over,
        # into a batch of values
        #   let values_batch =
        #     List.map
        #       (fun (id, _typ, iters) ->
        #         find_value Local ctx (id, iters @ [ Il.Ast.List ]) |> Value.get_list)
        #       vars
        #     |> transpose
        values_batch = [None] * len(varlist.vars)
        assert varlist
        first_list = None
        first_list_length = 0
        for i, var in enumerate(varlist.vars):
            value = self.find_value_local(var.id, var.iter.append_list())
            value_len = value.get_list_len()
            if first_list is not None:
                if first_list_length != value_len:
                    raise P4ContextError("cannot transpose a matrix of value batches")
            else:
                first_list = value
                first_list_length = value_len
            values_batch[i] = value
        assert first_list is not None
        return SubListIter(self, varlist, first_list_length, values_batch)

    def _venv_str(self):
        l = ["<venv "]
        for index, (var_name, var_iter) in enumerate(self.venv_keys.keys):
            pos = self.venv_keys.get_pos(var_name, var_iter)
            value = self._get_list(i)
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

    def sign_is_cont(self):
        return True

    def sign_get_ctx(self):
        return self

class SubListIter(object):
    def __init__(self, ctx, varlist, length, values_batch):
        self.varlist = varlist
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
        len_oldvalues = jit.promote(ctx_sub._get_size_list())
        varlist = jit.promote(self.varlist)
        final_env_keys = _varlist_compute_final_env_keys(varlist, jit.promote(ctx_sub.venv_keys))
        if final_env_keys is None:
            # some of the keys exist and need to be overridden - the complicated case
            for i, var in enumerate(varlist.vars):
                value = self.values_batch[i]._get_list(self.j)
                ctx_sub = ctx_sub.add_value_local(var.id, var.iter, value)
        elif len(varlist.vars) == 1:
            # a single new variable
            value = self.values_batch[0]._get_list(self.j)
            ctx_sub = ctx_sub.copy_and_change_append_venv(value, final_env_keys)
        else:
            # several new variables
            oldvalues = ctx_sub._get_full_list()
            values = [None] * (len_oldvalues + len(varlist.vars))
            for i in range(len(oldvalues)):
                values[i] = oldvalues[i]
            ctxindex = len_oldvalues
            for i, var in enumerate(varlist.vars):
                value = self.values_batch[i]._get_list(self.j)
                values[ctxindex] = value
                ctxindex += 1
            ctx_sub = ctx_sub.copy_and_change(venv_keys=final_env_keys, venv_values=values)
        self.j += 1
        return ctx_sub

@jit.elidable
def _varlist_compute_final_env_keys(varlist, env_keys):
    # returns None if some of the vars are already present in the env_keys
    if varlist._ctx_env_key_cache is env_keys:
        return varlist._ctx_env_key_result
    begin_env_keys = env_keys
    for var in varlist.vars:
        if env_keys.get_pos(var.id.value, var.iter.to_key()) >= 0:
            return None
        env_keys = env_keys.add_key(var.id.value, var.iter.to_key())
    varlist._ctx_env_key_cache = begin_env_keys
    varlist._ctx_env_key_result = env_keys
    return env_keys

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



