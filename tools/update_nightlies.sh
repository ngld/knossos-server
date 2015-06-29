#!/bin/bash

cd "$(dirname "$0")/../static/ni"
export PATH="../../py-env/bin:$PATH"
export QT_API=headless

python ../../tools/nightlies.py nightlies.cfg.json >> ni.log 2>&1
python ../../knossos/converter.py checksums --no-curses --force-cache nightlies.cfg.json nightlies.json >> ni.log 2>&1
python ../../tools/fix_nightly_meta.py nightlies.json >> ni.log 2>&1

[ -e converter.log ] && rm converter.log
