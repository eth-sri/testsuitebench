#!/usr/bin/env bash
set -u

usage() {
    cat <<'EOF'
Usage: build_mutant_repos_parallel.sh [--jobs N] [--cpus N] [ROOT]

Run build.sh concurrently for mutant repositories under ROOT.
ROOT defaults to /workspace. Repositories are immediate children named repo_*.
Successful builds are content-addressed, so unchanged repositories are reused
on subsequent invocations while edited repositories are rebuilt normally.
EOF
}

jobs="${PROGRAMBENCH_MUTANT_BUILD_JOBS:-}"
cpus="${PROGRAMBENCH_MUTANT_BUILD_CPUS:-}"
root="/workspace"

while [ "$#" -gt 0 ]; do
    case "$1" in
        --jobs|-j)
            if [ "$#" -lt 2 ]; then
                echo "missing value for $1" >&2
                exit 2
            fi
            jobs="$2"
            shift 2
            ;;
        --cpus)
            if [ "$#" -lt 2 ]; then
                echo "missing value for $1" >&2
                exit 2
            fi
            cpus="$2"
            shift 2
            ;;
        --help|-h)
            usage
            exit 0
            ;;
        --)
            shift
            break
            ;;
        -*)
            echo "unknown option: $1" >&2
            usage >&2
            exit 2
            ;;
        *)
            root="$1"
            shift
            ;;
    esac
done

if [ -z "$jobs" ]; then
    jobs="$(getconf _NPROCESSORS_ONLN 2>/dev/null || printf '1')"
fi
case "$jobs" in
    ''|*[!0-9]*|0)
        echo "jobs must be a positive integer, got: $jobs" >&2
        exit 2
        ;;
esac

if [ -z "$cpus" ]; then
    cpus="$(getconf _NPROCESSORS_ONLN 2>/dev/null || printf '1')"
fi
case "$cpus" in
    ''|*[!0-9]*|0)
        echo "cpus must be a positive integer, got: $cpus" >&2
        exit 2
        ;;
esac

if [ ! -d "$root" ]; then
    echo "root directory does not exist: $root" >&2
    exit 2
fi

build_fingerprint() {
    repo="$1"
    (
        cd "$repo" || exit 1
        prune_path=./.programbench-unused-prune-path
        if [ -f Cargo.toml ]; then prune_path=./target; fi
        {
            printf '%s\0' "${PROGRAMBENCH_BUILDER_DIGEST:-}" "${RUSTUP_TOOLCHAIN:-}" "${PROGRAMBENCH_RUST_REMAP_FLAGS:-}" "${PROGRAMBENCH_ORIGINAL_RUSTFLAGS:-}"
            find . -path "$prune_path" -prune -o -type f ! -name executable ! -name .programbench-build-cache -print0 \
                | sort -z \
                | xargs -0 -r sha256sum
            find . -path "$prune_path" -prune -o -type l ! -name executable -printf '%p -> %l\n' \
                | sort
        } | sha256sum | awk '{print $1}'
    )
}

build_one() {
    repo="$1"
    name="$(basename "$repo")"
    BUILD_ONE_OUTCOME=failed
    if [ ! -f "$repo/build.sh" ]; then
        echo "[$name] missing build.sh" >&2
        return 1
    fi

    cache="$repo/.programbench-build-cache"
    if [ -f "$repo/executable" ] && [ -f "$cache" ]; then
        read -r expected_inputs expected_executable < "$cache" || true
        current_inputs="$(build_fingerprint "$repo")"
        current_executable="$(sha256sum "$repo/executable" | awk '{print $1}')"
        if [ -n "${expected_inputs:-}" ] \
            && [ "$current_inputs" = "$expected_inputs" ] \
            && [ "$current_executable" = "${expected_executable:-}" ]; then
            echo "[$name] build reused (inputs unchanged)"
            BUILD_ONE_OUTCOME=reused
            return 0
        fi
    fi

    echo "[$name] build started"
    (
        set -euo pipefail
        cd "$repo" || exit 1
        if [ "${PROGRAMBENCH_USE_SCCACHE:-}" = 1 ] && command -v sccache >/dev/null 2>&1; then
            export RUSTC_WRAPPER=sccache
        fi
        # Keep in sync with NORMALIZE_BUILD_ENV_SHELL in source_build.py: the
        # reference binary must be compiled with exactly these settings.
        export RUSTFLAGS="${PROGRAMBENCH_RUST_REMAP_FLAGS:---remap-path-prefix=$PWD=/build}${RUSTFLAGS:+ $RUSTFLAGS}"
        export GOFLAGS="-trimpath${GOFLAGS:+ $GOFLAGS}"
        rm -f executable .programbench-build-cache || exit 1
        chmod +x build.sh || exit 1
        phase_started=$(date +%s%3N)
        ./build.sh || exit $?
        printf '[mutant-build-timing] repo=%s phase=build_script elapsed_ms=%s\n' "$name" "$(( $(date +%s%3N) - phase_started ))"
        test -s executable || exit 1
        chmod a+rx executable || exit 1
        phase_started=$(date +%s%3N)
        inputs="$(build_fingerprint "$repo")" || exit $?
        printf '[mutant-build-timing] repo=%s phase=fingerprint elapsed_ms=%s\n' "$name" "$(( $(date +%s%3N) - phase_started ))"
        executable_hash="$(sha256sum executable | awk '{print $1}')" || exit $?
        printf '%s %s\n' "$inputs" "$executable_hash" > .programbench-build-cache || exit 1
    )
    status="$?"
    if [ "$status" -eq 0 ]; then
        BUILD_ONE_OUTCOME=compiled
        echo "[$name] build finished"
    else
        echo "[$name] build failed with status $status" >&2
    fi
    return "$status"
}

show_sccache_stats() {
    [ "${PROGRAMBENCH_USE_SCCACHE:-}" = 1 ] || return 0
    command -v sccache >/dev/null 2>&1 || return 0
    local stats
    stats="$(sccache --show-stats 2>/dev/null | tr '\n' '|' | tr -s ' ')"
    printf '[mutant-build-sccache] at=%s %s\n' "$1" "$stats"
    if [[ "$stats" == *"--remap-path-prefix"* ]]; then
        printf '[mutant-build-cache-warning] Rust path remapping is not cacheable; rebuild the task_mutantbuild image with sccache 0.10.0 or newer\n'
    fi
}

report_progress() {
    name="$1"
    outcome="$2"
    build_duration_ms="$3"
    build_duration_second="$(awk -v duration_ms="$build_duration_ms" 'BEGIN { printf "%.1f", duration_ms / 1000 }')"
    while ! mkdir "$progress_lock" 2>/dev/null; do
        sleep 0.01
    done
    printf '%s\t%s\t%s\n' "$name" "$outcome" "$build_duration_ms" >> "$progress_file"
    completed="$(wc -l < "$progress_file")"
    compiled="$(awk -F '\t' '$2 == "compiled" { count++ } END { print count + 0 }' "$progress_file")"
    reused="$(awk -F '\t' '$2 == "reused" { count++ } END { print count + 0 }' "$progress_file")"
    failed="$(awk -F '\t' '$2 == "failed" { count++ } END { print count + 0 }' "$progress_file")"
    printf '[mutant-build-progress] completed=%s/%s compiled=%s reused=%s failed=%s last=%s outcome=%s build_duration_second=%s cpus_per_build=%s\n' \
        "$completed" "$progress_total" "$compiled" "$reused" "$failed" "$name" "$outcome" "$build_duration_second" "$build_cpus"
    awk -F '\t' -v now_ms="$(date +%s%3N)" -v start_ms="$build_batch_started_ms" \
        -v workers="$active_jobs" -v total="$progress_total" '
        { busy_ms += $3; if ($3 > max_ms) max_ms = $3 }
        END {
            elapsed = (now_ms - start_ms) / 1000;
            rate = elapsed > 0 ? NR / elapsed : 0;
            printf "[mutant-build-metrics] elapsed_second=%.3f rate=%.3f/s eta_second=%.1f worker_second=%.3f avg_active=%.2f configured_workers=%d mean_build_second=%.3f max_build_second=%.3f (occupancy includes IO; not CPU utilization)\n", elapsed, rate, (rate > 0 ? (total - NR) / rate : 0), busy_ms / 1000, (elapsed > 0 ? busy_ms / 1000 / elapsed : 0), workers, (NR > 0 ? busy_ms / 1000 / NR : 0), max_ms / 1000;
        }' "$progress_file"
    if [ "$((completed % 10))" -eq 0 ] || [ "$completed" -eq "$progress_total" ]; then
        show_sccache_stats "completed=$completed"
    fi
    rmdir "$progress_lock"
}

export -f build_fingerprint build_one report_progress show_sccache_stats

mapfile -d '' repos < <(find "$root" -maxdepth 1 -type d -name 'repo_*' -print0 | sort -z)
if [ "${#repos[@]}" -eq 0 ]; then
    echo "no repo_* directories found under $root" >&2
    exit 1
fi
active_jobs="$jobs"
if [ "$active_jobs" -gt "$cpus" ]; then
    active_jobs="$cpus"
fi
if [ "$active_jobs" -gt "${#repos[@]}" ]; then
    active_jobs="${#repos[@]}"
fi
build_cpus=$((cpus / active_jobs))
if [ "$build_cpus" -lt 1 ]; then
    build_cpus=1
fi

rustup_toolchain="${PROGRAMBENCH_MUTANT_RUSTUP_TOOLCHAIN:-${RUSTUP_TOOLCHAIN:-}}"
if [ -z "$rustup_toolchain" ] && command -v rustup >/dev/null 2>&1; then
    rustup_toolchain="$(cd / && rustup show active-toolchain 2>/dev/null | awk 'NR == 1 { print $1 }')"
fi
if [ -n "$rustup_toolchain" ]; then
    RUSTUP_TOOLCHAIN="$rustup_toolchain"
    export RUSTUP_TOOLCHAIN
fi


progress_dir="$(mktemp -d /tmp/programbench-mutant-build-progress.XXXXXX)"
progress_file="$progress_dir/status.tsv"
progress_lock="$progress_dir/lock"
progress_total="${#repos[@]}"
: > "$progress_file"
mkdir -p "$progress_dir/bin"
printf '#!/bin/sh\nprintf "%%s\\n" "%s"\n' "$build_cpus" > "$progress_dir/bin/nproc"
chmod +x "$progress_dir/bin/nproc"

helper_dir="$(cd "$(dirname "$0")" && pwd)"
if [ -f "$helper_dir/build-apt-cache.py" ]; then
    chmod +x "$helper_dir/build-apt-cache.py"
    ln -s "$helper_dir/build-apt-cache.py" "$progress_dir/bin/apt-get"
    ln -s "$helper_dir/build-apt-cache.py" "$progress_dir/bin/apt"
    export PROGRAMBENCH_BUILD_APT_CACHE="$progress_dir/apt"
fi
PATH="$progress_dir/bin:$PATH"
MAKEFLAGS="-j${build_cpus}"
CARGO_BUILD_JOBS="$build_cpus"
CMAKE_BUILD_PARALLEL_LEVEL="$build_cpus"
GOMAXPROCS="$build_cpus"
RAYON_NUM_THREADS="$build_cpus"
export PATH MAKEFLAGS CARGO_BUILD_JOBS CMAKE_BUILD_PARALLEL_LEVEL GOMAXPROCS RAYON_NUM_THREADS
PROGRAMBENCH_BUILDER_DIGEST="$(sha256sum "$0" | cut -d ' ' -f 1)"
PROGRAMBENCH_ORIGINAL_RUSTFLAGS="${RUSTFLAGS:-}"
export PROGRAMBENCH_BUILDER_DIGEST PROGRAMBENCH_ORIGINAL_RUSTFLAGS
build_batch_started_ms="$(date +%s%3N)"
export progress_file progress_lock progress_total build_cpus build_batch_started_ms active_jobs

printf '[mutant-build-plan] mutants=%s parallel_builds=%s total_cpus=%s cpus_per_build=%s rust_toolchain=%s\n' \
    "$progress_total" "$active_jobs" "$cpus" "$build_cpus" "${rustup_toolchain:-system}"

show_sccache_stats start

cleanup_progress() {
    rm -rf "$progress_dir"
}
trap cleanup_progress EXIT

run_one() {
    build_started_ms="$(date +%s%3N)"
    if build_one "$1"; then
        status=0
    else
        status=$?
    fi
    build_finished_ms="$(date +%s%3N)"
    report_progress "$(basename "$1")" "$BUILD_ONE_OUTCOME" \
        "$((build_finished_ms - build_started_ms))"
    return "$status"
}
export -f run_one

# Every repo in a group receives identical remapping arguments. Per-repo
# RUSTFLAGS poison dependency cache keys even when sccache supports the flag.
# Bound groups by argument bytes to stay below Linux's per-string exec limit.
# Each group's first build warms dependencies before its parallel fan-out.
status=0
remaining=("${repos[@]}")
while [ "${#remaining[@]}" -gt 0 ]; do
    group=()
    PROGRAMBENCH_RUST_REMAP_FLAGS=""
    for repo in "${remaining[@]}"; do
        flag="--remap-path-prefix=$(cd "$repo" && pwd)=/build"
        if [ "${#group[@]}" -gt 0 ] && [ "$(( ${#PROGRAMBENCH_RUST_REMAP_FLAGS} + ${#flag} ))" -gt 24000 ]; then
            break
        fi
        group+=("$repo")
        PROGRAMBENCH_RUST_REMAP_FLAGS+="${PROGRAMBENCH_RUST_REMAP_FLAGS:+ }$flag"
    done
    export PROGRAMBENCH_RUST_REMAP_FLAGS
    first_status=0
    printf '[mutant-build-warmup] serial_build=%s group_size=%s\n' "${group[0]}" "${#group[@]}"
    run_one "${group[0]}" || first_status=$?
    if [ "$first_status" -ne 0 ]; then
        echo "[mutant-build] first build failed; the shared source or environment is broken" >&2
        exit "$first_status"
    fi
    if [ "${#group[@]}" -gt 1 ]; then
        printf '%s\0' "${group[@]:1}" | xargs -0 -n 1 -P "$active_jobs" bash -c 'run_one "$1"' _
        group_status=$?
        if [ "$group_status" -ne 0 ]; then status=$group_status; fi
    fi
    remaining=("${remaining[@]:${#group[@]}}")
done
show_sccache_stats end
exit "$status"
