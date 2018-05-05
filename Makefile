# Makefile for indigo-netdev

PLUGIN_NAME = Network Devices
PYTHONPATH = "$(PLUGIN_NAME).indigoPlugin/Contents/Server Plugin/"
PYTHON = PYTHONPATH=$(PYTHONPATH) $(shell which python)

.PHONY: clean test

test: clean
	$(PYTHON) -m unittest discover -v ./test/

clean:
	find . -name '*.pyc' -exec rm {} \;
