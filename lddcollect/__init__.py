""" Tools for listing files needed to run elf executable to use elf library.
"""
import subprocess
import sys
import warnings
from typing import List, Iterable, Tuple, Dict, Set, Any, Union, Optional
import collections
from os import readlink
from pathlib import Path
from queue import Queue
from .vendor.lddtree import lddtree


def dpkg_s(*args: str) -> Tuple[List[Tuple[str, str]], List[str]]:
    """ Call `dpkg -S {arg}` and parse output into a list of tuples:

        [(pkg-name, full-path)]

        Returns
        =======
        [(pkg, path),...], [not-found-inputs]
    """
    def parse_line(line: str) -> Tuple[str, str]:
        idx = line.find(': ')
        if idx < 0:
            raise ValueError('Unexpected output from dpkg')
        deb, path = line[:idx], line[idx + 2:]
        return (deb, path)

    proc = subprocess.Popen(['/usr/bin/dpkg', '-S', *args],
                            stderr=subprocess.PIPE,
                            stdout=subprocess.PIPE)

    exit_code = proc.wait()
    assert proc.stdout is not None
    lines = proc.stdout.read().decode('utf8').split('\n')
    parsed = [parse_line(line) for line in lines if line]
    missing = []
    found = set(path for _, path in parsed)
    if exit_code != 0:
        for arg in args:
            if arg.startswith('/') or arg.startswith('./'):
                if arg not in found:
                    missing.append(arg)
            else:
                if not any(arg in path for path in found):
                    missing.append(arg)

    return parsed, missing


def lib2pkg_debian(libs: Dict[str, Dict[str, str]]) -> Dict[str, Optional[str]]:
    """
    For each lib lookup Debian package that provides it.
    """

    path2lib = {}

    for name, lib in libs.items():
        realpath = lib['realpath']
        if realpath is None:
            # missing lib, was not resolved
            continue

        p = Path(realpath)
        path2lib[realpath] = name

        # Deal with /lib vs /usr/lib ambiguity on Ubuntu 20.04
        # On 20.04 /lib is a symlink to /usr/lib some packages use
        # /lib some /usr/lib so we have to lookup both
        p2 = p.resolve()
        if p2 != p:
            path2lib[str(p2)] = name

    debs, _ = dpkg_s(*list(path2lib))
    lib2pkg: Dict[str, Optional[str]] = {path2lib[path]: pkg
                                         for pkg, path in debs
                                         if path in path2lib}
    for name in libs:
        if name not in lib2pkg:
            lib2pkg[name] = None

    return lib2pkg


def _resolve_link(link: Path) -> Path:
    next_link = Path(readlink(str(link)))
    if next_link.is_absolute():
        return next_link

    return link.parent/next_link


def _resolve_link_all(path: Path) -> Iterable[Path]:
    while path.is_symlink():
        yield(path)
        path = _resolve_link(path)
    yield path


def _lib_paths(lib: Dict[str, str]) -> Iterable[str]:
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


def files2deb(files: List[str]) -> Dict[str, str]:
    debs, non_deb = dpkg_s(*files)
    return {path: deb for deb, path in debs}


def _update_realpath(ltree: Dict[str, Any]):
    # lddtree seems to set realpath to path for top-level lib
    # but we want it to be just like any other lib
    if ltree['path'] == ltree['realpath']:
        root_path = Path(ltree['path'])
        if root_path.is_symlink():
            ltree['realpath'] = str(root_path.resolve())


def process_elf(fname: Union[str, Iterable[str]],
                verbose: bool = False,
                dpkg: bool = True,
                dpkg_ignore: List[str] = []) -> Tuple[List[str], List[str], List[str]]:
    """Find dependencies for a given elf file.

    Returns:

      List of Debian package names that supplied file or it's non-dpkg
      dependants reference and a list of files that are not managed by dpkg.
      Also returns a list of library names that are needed but were not
      found, for a working binary one would expect this list to be empty.

      [pkgs], [files], [missing-libs]

    """
    q: 'Queue[Tuple[str, Dict[str, Any]]]' = Queue()

    ltree: Dict[str, Any] = {}
    if isinstance(fname, str):
        if verbose:
            print(f"Finding dependencies ({fname})", file=sys.stderr)

        ltree = lddtree(fname)
        _update_realpath(ltree)
        q.put((fname, ltree))
    elif isinstance(fname, collections.Iterable):
        # create fake top level lib that depends on supplied inputs
        roots = [f for f in fname]
        libs: Dict[str, Any] = {}
        ltree = dict(interp=None,
                     rpath=None,
                     runpath=None,
                     path=None,
                     realpath=None,
                     needed=roots,
                     libs=libs)
        for fname in roots:
            if verbose:
                print(f"Finding dependencies ({fname})", file=sys.stderr)

            _ldd = lddtree(fname, lib_cache=libs)
            _update_realpath(_ldd)
            libs.update(_ldd.pop('libs', {}))
            libs[fname] = _ldd

        q.put(('', ltree))
    else:
        raise ValueError("Only accept str or Iterable[str]")

    libs = ltree['libs']

    if dpkg:
        if verbose:
            print(f"Mapping libs to packages ({len(ltree['libs'])})", file=sys.stderr)
        lib2pkg = lib2pkg_debian(ltree['libs'])
        if len(dpkg_ignore) > 0:
            lib2pkg = {lib: pkg for lib, pkg in lib2pkg.items() if pkg not in dpkg_ignore}
    else:
        lib2pkg = {}

    seen: Set[str] = set()
    pkgs: Set[str] = set()
    files: Set[str] = set()
    missing_libs: List[str] = []

    while not q.empty():
        name, lib = q.get()
        if name in seen:
            continue

        if lib['path'] is None and name != '':
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
