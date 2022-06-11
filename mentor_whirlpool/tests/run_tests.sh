#!/bin/sh

pushd $(git rev-parse --show-toplevel)/mentor_whirlpool

python3 -m nose2 --verbose tests.database_unit_tests

popd
