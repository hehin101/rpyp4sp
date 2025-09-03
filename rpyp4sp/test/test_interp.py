import os
from rpyp4sp.rpyjson import loads
from rpyp4sp.context import Context
from rpyp4sp import p4specast, objects, interp

def load():
    currfile = os.path.abspath(__file__)
    basedir = os.path.dirname(os.path.dirname(os.path.dirname(currfile)))
    fn = os.path.join(basedir, "ast.json")
    with open(fn) as f:
        value = loads(f.read())
    defs = []
    for i, d in enumerate(value.value_array()):
        defs.append(p4specast.Def.fromjson(d))
    return defs

def test_load_spec():
    spec = load()
    ctx = Context('dummy')
    ctx.load_spec(spec)
    assert 'Prog_ok' in ctx.glbl.renv
    assert 'is_fbitt' in ctx.glbl.fenv
    print(ctx.glbl.fenv["is_fbitt"])
    
def test_is_fbitt():
    # dec $is_fbitt(typ) : bool
    #     hint(show % IS FBIT_T)
    # def $is_fbitt(FBitT _) = true
    # def $is_fbitt(typ) = false
    #   -- otherwise
    value_json = """{
            "it": [
              "CaseV",
              [
                [
                  [
                    {
                      "it": [ "Atom", "IntT" ],
                      "note": null,
                      "at": {
                        "left": {
                          "file": "spec/2c1-runtime-type.watsup",
                          "line": 36,
                          "column": 4
                        },
                        "right": {
                          "file": "spec/2c1-runtime-type.watsup",
                          "line": 36,
                          "column": 8
                        }
                      }
                    }
                  ]
                ],
                []
              ]
            ],
            "note": {
              "vid": 432,
              "typ": [
                "VarT",
                {
                  "it": "numtyp",
                  "note": null,
                  "at": {
                    "left": {
                      "file": "spec/2c1-runtime-type.watsup",
                      "line": 35,
                      "column": 7
                    },
                    "right": {
                      "file": "spec/2c1-runtime-type.watsup",
                      "line": 35,
                      "column": 13
                    }
                  }
                },
                []
              ]
            },
            "at": null

          }"""
    arg = objects.W_Base.fromjson(loads(value_json))
    print(arg)
    spec = load()
    ctx = Context('dummy')
    ctx.load_spec(spec)
    func = ctx.glbl.fenv["is_fbitt"]
    interp.invoke_func_def_attempt_clauses(ctx, func, [arg])
