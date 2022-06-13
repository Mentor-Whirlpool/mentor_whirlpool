#!/bin/sh

pushd $(git rev-parse --show-toplevel)

python3 -m nose2 --verbose tests.database_unit_tests

popd
