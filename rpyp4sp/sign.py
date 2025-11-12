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

    def sign_get_cover(self):
        return None

class Res(Sign):
    @staticmethod
    def make(values, ctx):
        from rpyp4sp import context
        if isinstance(ctx, context.ContextWithCoverage):
            return ResWithCover.make(values, ctx.get_cover())
        else:
            return ResNoCover.make(values)

    @staticmethod
    def make0(ctx):
        from rpyp4sp import context
        if isinstance(ctx, context.ContextWithCoverage):
            return ResWithCover.make0(ctx.get_cover())
        else:
            return ResNoCover.make0()

@smalllist.inline_small_list(immutable=True)
class ResNoCover(Res):
    def __init__(self):
        pass


@smalllist.inline_small_list(immutable=True)
class ResWithCover(Res):
    def __init__(self, cover):
        self.cover = cover

    def sign_get_cover(self):
        return self.cover


class Ret(Sign):
    def __init__(self, value):
        self.value = value

    @staticmethod
    def make(ctx, value):
        from rpyp4sp import context
        if isinstance(ctx, context.ContextWithCoverage):
            return RetWithCover(value, ctx.get_cover())
        return Ret(value)

class RetWithCover(Ret):
    def __init__(self, value, cover):
        self.value = value
        self.cover = cover

    def sign_get_cover(self):
        return self.cover
