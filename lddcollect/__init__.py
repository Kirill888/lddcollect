""" Tools for listing files needed to run elf executable to use elf library.
"""
import subprocess
import sys
import warnings
from os import readlink
from pathlib import Path
from queue import Queue
from auditwheel.lddtree import lddtree


def dpkg_s(*args):
    """ Call `dpkg -S {arg}` and parse output into a list of tuples:

        [(pkg-name, full-path)]

        Returns
        =======
        [(pkg, path),...], [not-found-inputs]
    """
    def parse_line(line):
        idx = line.find(': ')
        if idx < 0:
            raise ValueError('Unexpected output from dpkg')
        deb, path = line[:idx], line[idx + 2:]
        return (deb, path)

    proc = subprocess.Popen(['/usr/bin/dpkg', '-S', *args],
                            stderr=subprocess.PIPE,
                            stdout=subprocess.PIPE)

    exit_code = proc.wait()
    lines = proc.stdout.read().decode('utf8').split('\n')
    parsed = [parse_line(l) for l in lines if l]
    missing = []
    if exit_code != 0:
        for arg in args:
            if not any(arg in path for _, path in parsed):
                missing.append(arg)

    return parsed, missing


def _resolve_link(link):
    next_link = Path(readlink(str(link)))
    if next_link.is_absolute():
        return next_link

    return link.parent/next_link


def _resolve_link_all(path):
    while path.is_symlink():
        yield(path)
        path = _resolve_link(path)
    yield path


def _lib_paths(lib):
    """ yield all symlinks starting from lib[path]->lib[realpath]
        Produces Empty sequence if lib[path] is None
    """
    path, realpath = lib['path'], lib['realpath']
    if path == realpath:
        if path is not None:
            yield path
    else:
        last = ""
        for p in _resolve_link_all(Path(path)):
            last = str(p)
            yield last

        if last != realpath:
            warnings.warn(f"Symlink didn't go to expected place: {last} != {realpath}")


def _paths(ltree):
    yield from _lib_paths(ltree)
    for lib in ltree['libs'].values():
        yield from _lib_paths(lib)


def files2deb(files):
    debs, non_deb = dpkg_s(*files)
    return {path: deb for deb, path in debs}


def process_elf(fname, verbose=False, dpkg=True):
    """Find dependencies for a given elf file.

    Returns:

      List of Debian package names that supplied file or it's non-dpkg
      dependants reference and a list of files that are not managed by dpkg.
      Also returns a list of library names that are needed but were not
      found, for a working binary one would expect this list to be empty.

      [pkgs], [files], [missing-libs]

    """
    if verbose:
        print(f"Finding dependencies ({fname})", file=sys.stderr)

    ltree = lddtree(fname)

    # lddtree seems to set realpath to path for top-level lib
    # but we want it to be just like any other lib
    if ltree['path'] == ltree['realpath']:
        root_path = Path(ltree['path'])
        if root_path.is_symlink():
            ltree['realpath'] = str(root_path.resolve())

    libs = ltree['libs']

    if dpkg:
        lib_files = list(_paths(ltree))

        if verbose:
            print(f"Mapping files to packages ({len(lib_files)})", file=sys.stderr)

        libpath2pkg = files2deb(lib_files)
        lib2pkg = {
            n: libpath2pkg.get(lib['path'], None)
            for n, lib in libs.items()
        }
        lib2pkg[fname] = libpath2pkg.get(ltree['path'], None)
    else:
        lib2pkg = {}

    seen = set()
    pkgs = set()
    files = set()
    missing_libs = []

    q = Queue()
    q.put((fname, ltree))

    while not q.empty():
        name, lib = q.get()
        if name in seen:
            continue

        if lib['path'] is None:
            if verbose:
                print(f"Failed to find lib: {name}", file=sys.stderr)
            missing_libs.append(name)

        seen.add(name)
        pkg = lib2pkg.get(name, None)
        if pkg is not None:
            pkgs.add(pkg)
            continue
        else:
            for p in _lib_paths(lib):
                files.add(p)

        for name in lib['needed']:
            if name not in seen:
                q.put((name, libs[name]))

    return list(pkgs), list(files), missing_libs
