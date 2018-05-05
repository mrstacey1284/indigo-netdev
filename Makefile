# Makefile for indigo-netdev

PLUGIN_NAME = Network Devices

PLUGIN_DIR = $(PLUGIN_NAME).indigoPlugin
ZIPFILE = $(PLUGIN_NAME).zip
PYTHONPATH = "$(PLUGIN_DIR)/Contents/Server Plugin/"

DELETE_FILE = rm -f
EXECUTE_PY = PYTHONPATH=$(PYTHONPATH) $(shell which python)

.PHONY: clean test dist

test: clean
	$(EXECUTE_PY) -m unittest discover -v ./test/

dist: clean zipfile

zipfile:
	zip -9r "$(ZIPFILE)" "$(PLUGIN_DIR)"

clean:
	$(DELETE_FILE) "$(ZIPFILE)"
	find . -name '*.pyc' -exec $(DELETE_FILE) {} \;
