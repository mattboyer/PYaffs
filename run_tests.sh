#!/usr/bin/bash

declare -i PEP_CLEAN NOSE_SUCCESS

pep8 -v src/*.py
PEP_CLEAN=${?}

nosetests --with-cov --cover-package=src -v test/
NOSE_SUCCESS=${?}

exit $(( PEP_CLEAN + NOSE_SUCCESS ))
