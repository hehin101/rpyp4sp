from rpyp4sp import smalllist

class Sign(object):
    # Sign instances represent a (ctx, sign) tuple in Ocaml
    # get the ctx by call sign_get_ctx
    # an Ocaml tuple ctx, Cont is represented as just a Context in Python
    # (Context inherits from Sign for that purpose)

    _attrs_ = []

    # abstract base
    def sign_is_cont(self):
        return False

    def sign_get_ctx(self):
        raise NotImplementedError

@smalllist.inline_small_list(immutable=True)
class Res(Sign):
    def __init__(self, ctx):
        #self.ctx = ctx
        pass

    def sign_get_ctx(self):
        assert 0


class Ret(Sign):
    def __init__(self, ctx, value):
        self.value = value

    def sign_get_ctx(self):
        assert 0, 'shouldn\'t be called'
