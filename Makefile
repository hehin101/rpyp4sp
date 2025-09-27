.PHONY: install-opam
install-opam:
ifeq (,$(shell which opam))
ifeq (Linux, $(shell uname))
	sudo apt install opam
	opam init
else ifeq (Darwin, $(shell uname)) # macOS
	brew install opam
	opam init --auto-setup
endif
endif

.PHONY: install-opam-dependencies
install-opam-dependencies: install-opam
ifeq (, $(shell opam switch list | grep 5.1.0))
	opam switch create 5.1.0
	eval $(opam env)
endif
	opam switch 5.1.0
	opam --yes install dune bignum menhir core core_unix bisect_ppx yojson ppx_deriving_yojson

.PHONY: setup-pypy
setup-pypy:
	git clone https://github.com/pypy/pypy.git --dept=1


_pypy_binary/bin/python:  ## Download a PyPy binary
	mkdir -p _pypy_binary
	python3 get_pypy_to_download.py
	tar -C _pypy_binary --strip-components=1 -xf pypy.tar.bz2
	rm pypy.tar.bz2
	./_pypy_binary/bin/python -m ensurepip
	./_pypy_binary/bin/python -mpip install "hypothesis<4.40" junit_xml coverage==5.5 "pdbpp==0.10.3"

.PHONY: ast.json
ast.json: _pypy_binary/bin/python ## regenerate the AST json file
	_pypy_binary/bin/python prepare_ast.py


.PHONY: run-error-tests
run-error-tests:  ## Run integration tests for error output
	./targetrpyp4sp-c run-p4-json --no-times `cat integrationtests/errorfiles` > integrationtests/erroroutput.actual
	@if diff --color=auto -u integrationtests/erroroutput.expected integrationtests/erroroutput.actual; then \
		echo "\033[32mError output tests (no color) PASSED\033[0m"; \
	else \
		echo "\033[31mError output tests (no color) FAILED - differences found above\033[0m"; \
		exit 1; \
	fi
	FORCE_COLOR=1 ./targetrpyp4sp-c run-p4-json --no-times `cat integrationtests/errorfiles` > integrationtests/erroroutput_color.actual
	@# Normalize absolute paths in both files for comparison
	@sed 's|file://[^\\]*spec/|file://SPEC_DIR/|g' integrationtests/erroroutput_color.expected > integrationtests/erroroutput_color.expected.normalized
	@sed 's|file://[^\\]*spec/|file://SPEC_DIR/|g' integrationtests/erroroutput_color.actual > integrationtests/erroroutput_color.actual.normalized
	@if diff --color=auto -u integrationtests/erroroutput_color.expected.normalized integrationtests/erroroutput_color.actual.normalized; then \
		echo "\033[32mError output tests (with color) PASSED\033[0m"; \
	else \
		echo "\033[31mError output tests (with color) FAILED - differences found above\033[0m"; \
		exit 1; \
	fi
	@rm -f integrationtests/erroroutput_color.expected.normalized integrationtests/erroroutput_color.actual.normalized

.PHONY: update-error-tests-expectations
update-error-tests-expectations:  ## Update expected output files for error tests
	./targetrpyp4sp-c run-p4-json --no-times `cat integrationtests/errorfiles` > integrationtests/erroroutput.expected
	FORCE_COLOR=1 ./targetrpyp4sp-c run-p4-json --no-times `cat integrationtests/errorfiles` > integrationtests/erroroutput_color.expected.raw
	@# Normalize absolute paths in the color expected file
	@sed 's|file://[^\\]*spec/|file://SPEC_DIR/|g' integrationtests/erroroutput_color.expected.raw > integrationtests/erroroutput_color.expected
	@rm -f integrationtests/erroroutput_color.expected.raw
	@echo "\033[33mUpdated error test expectations\033[0m"

