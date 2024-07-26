import argparse

from .drakpdb import make_pdb_profile, fetch_pdb, pe_codeview_data

def main():
    parser = argparse.ArgumentParser(description='drakpdb')
    parser.add_argument('action', type=str, help='one of: fetch_pdb, parse_pdb')
    parser.add_argument('pdb_name', type=str, help='name of pdb file without extension, e.g. ntkrnlmp')
    parser.add_argument('guid_age', nargs='?', help='guid/age of the pdb file')

    args = parser.parse_args()

    if args.action == "parse_pdb":
        make_pdb_profile(args.pdb_name)
    elif args.action == "fetch_pdb":
        fetch_pdb(args.pdb_name, args.guid_age)
    elif args.action == "pe_codeview_data":
        print(pe_codeview_data(args.file))
    else:
        raise RuntimeError('Unknown action')
