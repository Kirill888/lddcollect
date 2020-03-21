import click
from . import process_elf


@click.command(name='lddcollect')
@click.option('--dpkg/--no-dpkg', default=True, help="Lookup dpkg libs or not")
@click.option('--verbose', is_flag=True, help="Print some info to stderr")
@click.argument('libs',
                nargs=-1,
                type=click.Path(exists=True, dir_okay=False, file_okay=True))
def main(libs, dpkg=False, verbose=False):
    """Find all other libraries and debian dependencies this executable or library
    requires to run.

    Prints:
    1. Non-dpkg managed files, one per line
    2. Separator line: --------------------------------
    3. Package names, one per line
    """

    debs = set()
    files = set()

    for lib in libs:
        _debs, _files = process_elf(lib, verbose=verbose, dpkg=dpkg)
        debs.update(_debs)
        files.update(_files)

    for file in files:
        print(file)

    if dpkg:
        print("------------------------------------------")
        for deb in debs:
            print(deb)


main()
