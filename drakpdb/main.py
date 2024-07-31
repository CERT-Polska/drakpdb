import argparse
import json

from .drakpdb import make_pdb_profile, pe_codeview_data
from .fetch_pdb import fetch_pdb


def main():
    parser = argparse.ArgumentParser(description="drakpdb")

    pdbname_subparser = argparse.ArgumentParser(add_help=False)
    pdbname_subparser.add_argument("pdb_name", type=str, help="name of the pdb file")

    dllname_subparser = argparse.ArgumentParser(add_help=False)
    dllname_subparser.add_argument("dll_name", type=str, help="path to the dll file")

    guidage_subparser = argparse.ArgumentParser(add_help=False)
    guidage_subparser.add_argument(
        "guid_age", type=str, help="guid/age of the pdb file"
    )

    action = parser.add_subparsers(help="Action commands", dest="action")
    action.required = True
    action.add_parser(
        "parse_pdb",
        parents=[pdbname_subparser],
        help="Parse PDB file into Rekall profile",
    )
    action.add_parser(
        "fetch_pdb",
        parents=[pdbname_subparser, guidage_subparser],
        help="Fetch PDB file matching PDB name and GUID/Age",
    )
    action.add_parser(
        "pe_codeview_data",
        parents=[dllname_subparser],
        help="Get PDB name and GUID/Age for DLL path",
    )
    args = parser.parse_args()

    if args.action == "parse_pdb":
        profile = make_pdb_profile(args.pdb_name)
        print(json.dumps(profile, indent=4))
    elif args.action == "fetch_pdb":
        fetch_pdb(args.pdb_name, args.guid_age)
    elif args.action == "pe_codeview_data":
        print(pe_codeview_data(args.dll_name))
    else:
        raise RuntimeError("Unknown action")
