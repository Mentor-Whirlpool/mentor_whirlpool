#!/bin/sh
pushd $(git rev-parse --show-toplevel)

python3 -m nose2 --with-coverage --coverage-report html --coverage-config tests/coveragerc tests.database_unit_tests

popd
