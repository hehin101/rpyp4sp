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