import click
from . import process_elf


@click.command(name='lddcollect')
@click.option('--no-dpkg', is_flag=True, help="Do not use dpkg")
@click.option('--verbose', is_flag=True, help="Print some info to stderr")
@click.argument('libs',
                nargs=-1,
                type=click.Path(exists=True, dir_okay=False, file_okay=True))
def main(libs, no_dpkg=False, verbose=False):
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
        _debs, _files = process_elf(lib, verbose=verbose)
        debs.update(_debs)
        files.update(_files)

    for file in files:
        print(file)
    print("------------------------------------------")
    for deb in debs:
        print(deb)


main()
