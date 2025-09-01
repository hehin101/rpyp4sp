from __future__ import print_function
from rpyp4sp import p4specast

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

def test_full_ast():
    import json, os
    currfile = os.path.abspath(__file__)
    basedir = os.path.dirname(os.path.dirname(os.path.dirname(currfile)))
    fn = os.path.join(basedir, "ast.json")
    with open(fn) as f:
        value = json.loads(f.read())
    defs = {}
    for i, d in enumerate(value):
        try:
            defs[i] = p4specast.Def.fromjson(d)
        except Exception as e:
            import pdb; pdb.xpm()
            print("Error processing definition %d: %s" % (i, e))
    print("worked: %s, failed: %s, percent %s" % (len(defs), len(value) - len(defs), 100 * len(defs) / len(value)))

