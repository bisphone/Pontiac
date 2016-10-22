SHELL=/bin/bash

install: install_reqs venv

install_reqs:
	apt-get -q update
	apt-get -qy install build-essential python-dev redis-server

venv: venv/bin/activate

venv/bin/activate: requirements.txt
	@test -d venv || virtualenv venv
	@source ./venv/bin/activate; \
	pip install -Ur requirements.txt
	@touch venv/bin/activate

run: venv
	@source ./venv/bin/activate; \
	python -BRtu ./pontiac-server.py --verbose --queuer queue --executer thread

test: venv

clean:
	@find . -name "*.pyc" -delete
	@find . -name "*.log" -delete
	@rm -f *.{log,pid}

distclean:
	@rm -rf ./venv/

.PHONY: run clean distclean
