import pathlib
import toml

from drakpdb.fetch_pdb import fetch_pdb

package_dir = pathlib.Path(__file__).parent.absolute()
pdbs_dir = package_dir / "pdbs"
pdbs_file = pdbs_dir / "pdbs.toml"


def add_guid_to_name(pdbname, guidage):
    return pdbname.rsplit(".", 1)[0] + "_" + guidage + ".pdb"


def update_pdbs():
    pdbs_config_data = pdbs_file.read_text()
    pdbs_config = toml.loads(pdbs_config_data)
    for pdb_spec in pdbs_config["pdbs"]:
        target_path = pdbs_dir / add_guid_to_name(str(pdb_spec["pdbname"]), pdb_spec["guidage"])
        if target_path.exists():
            print(f"{str(target_path)} already fetched")
            continue
        fetch_pdb(pdb_spec["pdbname"], pdb_spec["guidage"], destdir=str(pdbs_dir))
        current_path = pdbs_dir / pdb_spec["pdbname"]
        current_path.rename(target_path)
        print(f"{str(target_path)} downloaded")


if __name__ == "__main__":
    update_pdbs()
