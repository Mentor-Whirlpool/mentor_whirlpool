#!/bin/sh

pushd $(git rev-parse --show-toplevel)/mentor_whirlpool

python3 -m unittest tests/database_unit_tests.py

popd
