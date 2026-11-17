# source this in a wsl shell before building or running gem5:
#   source scripts/env.sh
# matches the toolchain setup in CLAUDE.md.

if [ -z "${CONDA_EXE:-}" ] && [ -f "$HOME/anaconda3/etc/profile.d/conda.sh" ]; then
    . "$HOME/anaconda3/etc/profile.d/conda.sh"
fi
conda activate gem5-env

unset CPATH LIBRARY_PATH LD_LIBRARY_PATH LDFLAGS CPPFLAGS
export CPATH="$CONDA_PREFIX/include"
export LIBRARY_PATH="$CONDA_PREFIX/lib"
export LD_LIBRARY_PATH="$CONDA_PREFIX/lib"
export LDFLAGS="-L$CONDA_PREFIX/lib"
export CPPFLAGS="-I$CONDA_PREFIX/include"
export PKG_CONFIG_PATH="$CONDA_PREFIX/lib/pkgconfig"
export PATH="$HOME/gem5-tools/bin:$CONDA_PREFIX/bin:$PATH"
export CC="$HOME/gem5-tools/bin/gcc"
export CXX="$HOME/gem5-tools/bin/g++"
hash -r

export GEM5_ROOT="${GEM5_ROOT:-$HOME/gem5}"
