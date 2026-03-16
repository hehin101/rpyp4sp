# rpyp4sp

An RPython implementation of [P4-SpecTec](https://github.com/kaist-plrg/p4-spectec)

## Building the Project

### Prerequisites

Installing opam and dependencies for P4-SpecTec:
```bash
make install-opam
make install-opam-dependencies
```

Get PyPy:
```bash
make _pypy_binary/bin/python
make setup-pypy
```

Get P4-SpecTec:
```bash
make p4-spectec/p4spectec
```

Create `ast.json`:
```bash
make ast.json
```

### Run tests
```bash
_pypy_binary/bin/python pypy/pytest.py rpyp4sp -v -k-all
```

### Translate binary
```bash
PYTHONPATH=. _pypy_binary/bin/python pypy/rpython/bin/rpython -Ojit rpyp4sp/targetrpyp4sp.py
```

### Make P4 json samples
```bash
cd p4-spectec
for f in p4c/testdata/p4_16_samples/*.p4; do ./p4spectec p4-program-value-json -i p4c/p4include -p "$f" > "${f}.json"; done
cd ..
```

### Run P4 json samples with targetrpyp4sp-c
```bash
# with JIT
./targetrpyp4sp-c run-p4-json p4-spectec/p4c/testdata/p4_16_samples/*.p4.json
# without JIT
./targetrpyp4sp-c run-p4-json --jit off p4-spectec/p4c/testdata/p4_16_samples/*.p4.json
```
