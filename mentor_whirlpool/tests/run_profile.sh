#!/usr/bin/env bash

pushd $(git rev-parse --show-toplevel)/mentor_whirlpool

python3 -m nose2 --plugin nose2.plugins.prof --profile --config tests/profconfig tests.database_unit_tests
echo "open tests.prof with snakeviz"

popd
