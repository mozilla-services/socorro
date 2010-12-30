#! /bin/bash
# FIXME hardcoded install path
/data/socorro/stackwalk/bin/minidump_stackwalk $* 2> >(grep -v INFO >&2) 

