import pathlib

package_dir = pathlib.Path(__file__).parent.absolute()
pdbs_dir = package_dir / "pdbs"


def pytest_generate_tests(metafunc):
    if 'pdb_file' in metafunc.fixturenames:
        pdbs_files = list(pdbs_dir.glob("*.pdb"))
        metafunc.parametrize('pdb_file', pdbs_files)
    if 'nt_kernel_pdb_file' in metafunc.fixturenames:
        pdbs_files = list(pdbs_dir.glob("ntkrnlmp*.pdb"))
        metafunc.parametrize('nt_kernel_pdb_file', pdbs_files)
