from __future__ import print_function
import os
from rpyp4sp import p4specast, objects
from rpyp4sp.rpyjson import loads

decd_example = [
      "DecD",
      {
        "it": "sum",
        "note": None,
        "at": {
          "left": { "file": "spec/0-aux.watsup", "line": 18, "column": 5 },
          "right": { "file": "spec/0-aux.watsup", "line": 18, "column": 9 }
        }
      },
      [],
      [],
      []
    ]

def test_decd_example():
    assert p4specast.DecD.fromjson(decd_example) == p4specast.DecD(
        id=p4specast.Id(
            value="sum",
            region=p4specast.Region(
                left=p4specast.Position(
                    file="spec/0-aux.watsup",
                    line=18,
                    column=5
                ),
                right=p4specast.Position(
                    file="spec/0-aux.watsup",
                    line=18,
                    column=9
                )
            )
        ),
        tparams=[],
        args=[],
        instrs=[]
    )

def test_full_ast_rpython():
    currfile = os.path.abspath(__file__)
    basedir = os.path.dirname(os.path.dirname(os.path.dirname(currfile)))
    fn = os.path.join(basedir, "ast.json")
    with open(fn) as f:
        value = loads(f.read())
    defs = {}
    for i, d in enumerate(value.value_array()):
        defs[i] = p4specast.Def.fromjson(d)


def test_example_values_load():
    from rpyp4sp.rpyjson import loads
    import os
    currfile = os.path.abspath(__file__)
    testdir = os.path.dirname(currfile)
    fn = os.path.join(testdir, "example_values.json")
    with open(fn) as f:
        value = loads(f.read())
    res = objects.W_Base.fromjson(value)
