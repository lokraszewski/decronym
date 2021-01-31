default: test;

venv: venv/touchfile

venv/touchfile: requirements.txt
	test -d venv || python3 -m venv venv
	. venv/bin/activate; pip install -Ur requirements.txt
	touch venv/touchfile

test: venv
	. venv/bin/activate; nosetests tests

# Installs in venv for testing
install: venv
	. venv/bin/activate; pip install .

install_setup: venv
	. venv/bin/activate; pip install -U setuptools twine wheel

dist: install_setup
	. venv/bin/activate; python3 setup.py sdist bdist_wheel

dist_check: dist
	. venv/bin/activate; twine check dist/*

upload: dist_check
	. venv/bin/activate; python3 -m twine upload --repository testpypi dist/*

upload_prod: dist_check
	. venv/bin/activate; python3 -m twine upload dist/*

clean:
	rm -rf venv
	rm -rf build
	rm -rf dist
	find -iname "*.pyc" -delete

.PHONY: test clean default
