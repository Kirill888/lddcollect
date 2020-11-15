import sys
from json import (dump as json_dump)
import click
from typing import List, Optional
from pathlib import Path
from . import process_elf, find_libs


@click.command(name='lddcollect')
@click.option('--dpkg/--no-dpkg', default=False, help="Lookup dpkg libs or not, default: no")
@click.option('--json', is_flag=True, help="Output in json format")
@click.option('--verbose', is_flag=True, help="Print some info to stderr")
@click.option('--ignore-pkg', multiple=True, type=str, help="Packages to ignore (list package files instead)")
@click.argument('libs_or_dir',
                nargs=-1,
                type=click.Path(exists=True, dir_okay=True, file_okay=True))
def main(libs_or_dir: List[str],
         dpkg: bool = False,
         json: bool = False,
         verbose: bool = False,
         ignore_pkg: List[str] = []):
    """
    Find all other libraries and optionally Debian dependencies listed
    applications/libraries require to run.

    Two ways to run:

    \b
    1. Supply single directory on input
       - Will locate all dynamic libs under that path
       - Will print external libs only (will not print any input libs that were found)
    2. Supply paths to individual ELF files on a command line
       - Will print input libs and any external libs referenced

    Prints libraries (including symlinks) that are referenced by input files, one
    file per line.

    When --dpkg option is supplied, print:

    \b
      1. Non-dpkg managed files, one per line
      2. Separator line: ...
      3. Package names, one per line
    """
    pkgs: Optional[List[str]] = None

    if len(libs_or_dir) == 1 and Path(libs_or_dir[0]).is_dir():
        prefix = libs_or_dir[0]
        libs = list(find_libs(prefix))
        pkgs, files, missing = process_elf(libs,
                                           verbose=verbose,
                                           dpkg=dpkg,
                                           dpkg_ignore=ignore_pkg,
                                           skip_prefix=prefix)
    else:
        libs = libs_or_dir
        pkgs, files, missing = process_elf(libs, verbose=verbose, dpkg=dpkg, dpkg_ignore=ignore_pkg)

    files = sorted(files)
    pkgs = sorted(pkgs) if dpkg else None

    if json:
        out = {'files': files}
        if pkgs is not None:
            out['packages'] = pkgs
        json_dump(out, sys.stdout, indent=2)
    else:
        for file in files:
            print(file)

        if pkgs is not None:
            print("...")
            for pkg in pkgs:
                print(pkg)

    if len(missing) > 0:
        sys.stdout.flush()
        print("\nThere were missing libraries", file=sys.stderr)
        for lib in missing:
            print(f"   {lib}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
