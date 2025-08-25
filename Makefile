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
	opam --yes install dune bignum menhir core core_unix bisect_ppx
