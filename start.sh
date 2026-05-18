#!/bin/zsh
set -e

cd /Users/eligross/Desktop/local_agent_infra/agent_infra/NOVA_Glass_GUI

export DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer
export SWIFTPM_MODULECACHE_OVERRIDE=/tmp/swiftpm-module-cache
export CLANG_MODULE_CACHE_PATH=/tmp/clang-module-cache

exec swift run
