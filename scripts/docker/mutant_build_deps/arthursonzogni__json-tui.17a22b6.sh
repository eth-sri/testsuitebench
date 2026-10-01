#!/usr/bin/env bash
set -euo pipefail

# Every mutant's CMakeLists declares these with FIND_PACKAGE_ARGS, so CMake
# tries find_package() before falling back to a network fetch. Installing them
# at the pinned versions makes all 102 mutant builds resolve locally instead of
# git-cloning ftxui once per mutant, which is what failed 10 of them.
build_and_install() {
    url=$1 tag=$2 name=$3
    git clone --depth 1 --branch "$tag" "$url" "/tmp/src-$name"
    cmake -S "/tmp/src-$name" -B "/tmp/build-$name" \
        -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=/usr/local \
        -DFTXUI_BUILD_EXAMPLES=OFF -DFTXUI_BUILD_DOCS=OFF -DFTXUI_BUILD_TESTS=OFF \
        -DJSON_BuildTests=OFF -DARGS_BUILD_EXAMPLE=OFF -DARGS_BUILD_UNITTESTS=OFF
    cmake --build "/tmp/build-$name" --parallel "$(nproc)" --target install
    rm -rf "/tmp/src-$name" "/tmp/build-$name"
}

build_and_install https://github.com/ArthurSonzogni/ftxui v6.0.2 ftxui
build_and_install https://github.com/nlohmann/json v3.12.0 nlohmann_json
build_and_install https://github.com/Taywee/args 6.4.7 args
