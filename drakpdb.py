import argparse
import os

import pdbparse
import json

import requests
from construct import EnumIntegerString
from pdbparse.undname import undname
from requests import HTTPError


# from rekall
TYPE_ENUM_TO_VTYPE = {
    "T_32PINT4": ["Pointer", dict(target="long")],
    "T_32PLONG": ["Pointer", dict(target="long")],
    "T_32PQUAD": ["Pointer", dict(target="long long")],
    "T_32PRCHAR": ["Pointer", dict(target="unsigned char")],
    "T_32PREAL32": ["Pointer", dict(target="Void")],
    "T_32PREAL64": ["Pointer", dict(target="Void")],
    "T_32PSHORT": ["Pointer", dict(target="short")],
    "T_32PUCHAR": ["Pointer", dict(target="unsigned char")],
    "T_32PUINT4": ["Pointer", dict(target="unsigned int")],
    "T_32PULONG": ["Pointer", dict(target="unsigned long")],
    "T_32PUQUAD": ["Pointer", dict(target="unsigned long long")],
    "T_32PUSHORT": ["Pointer", dict(target="unsigned short")],
    "T_32PVOID": ["Pointer", dict(target="Void")],
    "T_32PWCHAR": ["Pointer", dict(target="UnicodeString")],
    "T_64PLONG": ["Pointer", dict(target="long")],
    "T_64PQUAD": ["Pointer", dict(target="long long")],
    "T_64PRCHAR": ["Pointer", dict(target="unsigned char")],
    "T_64PUCHAR": ["Pointer", dict(target="unsigned char")],
    "T_64PWCHAR": ["Pointer", dict(target="String")],
    "T_64PULONG": ["Pointer", dict(target="unsigned long")],
    "T_64PUQUAD": ["Pointer", dict(target="unsigned long long")],
    "T_64PUSHORT": ["Pointer", dict(target="unsigned short")],
    "T_64PVOID": ["Pointer", dict(target="Void")],
    "T_BOOL08": ["unsigned char", {}],
    "T_CHAR": ["char", {}],
    "T_INT4": ["long", {}],
    "T_INT8": ["long long", {}],
    "T_LONG": ["long", {}],
    "T_QUAD": ["long long", {}],
    "T_RCHAR": ["unsigned char", {}],
    "T_REAL32": ["float", {}],
    "T_REAL64": ["double", {}],
    "T_REAL80": ["long double", {}],
    "T_SHORT": ["short", {}],
    "T_UCHAR": ["unsigned char", {}],
    "T_UINT4": ["unsigned long", {}],
    "T_ULONG": ["unsigned long", {}],
    "T_UQUAD": ["unsigned long long", {}],
    "T_USHORT": ["unsigned short", {}],
    "T_VOID": ["Void", {}],
    "T_WCHAR": ["UnicodeString", {}],
}


class DummyOmap(object):
    def remap(self, addr):
        return addr


def get_field_type_info(field):
    if isinstance(field.index, EnumIntegerString):
        return TYPE_ENUM_TO_VTYPE[str(field.index)]

    try:
        return [field.index.name, {}]
    except AttributeError:
        return ["<unknown>", {}]


def process_struct(struct_info):
    ss = {}

    try:
        for struct in struct_info.fieldlist.substructs:
            ss[struct.name] = struct
    except AttributeError:
        pass

    fields = [struct.name for struct in ss.values()]
    field_info = {ss[field].name: [ss[field].offset, get_field_type_info(ss[field])] for field in fields}
    return [struct_info.size, field_info]


def make_pdb_profile(filepath):
    filepath = filepath + ".pdb"
    pdb = pdbparse.parse(filepath)

    try:
        sects = pdb.STREAM_SECT_HDR_ORIG.sections
        omap = pdb.STREAM_OMAP_FROM_SRC
    except AttributeError as e:
        # In this case there is no OMAP, so we use the given section
        # headers and use the identity function for omap.remap
        sects = pdb.STREAM_SECT_HDR.sections
        omap = DummyOmap()

    gsyms = pdb.STREAM_GSYM
    profile = {"$FUNCTIONS": {}, "$CONSTANTS": {}, "$STRUCTS": {}}
    struct_specs = {
        structName: process_struct(pdb.STREAM_TPI.structures[structName])
        for structName in pdb.STREAM_TPI.structures.keys()
    }
    for structName, structFields in struct_specs.items():
        profile["$STRUCTS"][structName] = structFields

    for sym in gsyms.globals:
        try:
            off = sym.offset
            sym_name = sym.name
            virt_base = sects[sym.segment - 1].VirtualAddress
            mapped = omap.remap(off + virt_base)
            is_function = (sym.symtype & 2) == 2
        except IndexError as e:
            # skip symbol because segment was not found
            continue
        except AttributeError as e:
            # missing offset in symbol?
            continue

        if sym_name.startswith("?"):
            sym_name = undname(sym_name)

        if is_function:
            profile["$FUNCTIONS"][sym_name] = mapped
        else:
            profile["$CONSTANTS"][sym_name] = mapped

    guid = pdb.STREAM_PDB.GUID
    guid_str = "%.8X%.4X%.4X%s" % (guid.Data1, guid.Data2, guid.Data3, guid.Data4.hex().upper())
    symstore_hash = "%s%s" % (guid_str, pdb.STREAM_PDB.Age)
    base_fn = os.path.splitext(os.path.basename(filepath))[0]

    profile["$METADATA"] = {
        "GUID_AGE": symstore_hash,
        "PDBFile": os.path.basename(filepath),
        "ProfileClass": base_fn[0].upper() + base_fn[1:].lower(),
        "Timestamp": pdb.STREAM_PDB.TimeDateStamp.replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%SZ"),
        "Type": "Profile",
        "Version": pdb.STREAM_PDB.Version
    }
    print(json.dumps(profile, indent=4, sort_keys=True))


def fetch_pdb(pdbname, guidage):
    pdbname = pdbname + ".pdb"
    url = "https://msdl.microsoft.com/download/symbols/{}/{}/{}".format(pdbname, guidage.lower(), pdbname)

    try:
        with requests.get(url, stream=True) as res:
            res.raise_for_status()

            with open(os.path.basename(pdbname), "wb") as f:
                for chunk in res.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

        return True
    except HTTPError as e:
        print("Failed to download from: {}, reason: {}".format(url, str(e)))

    return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='drakpdb')
    parser.add_argument('action', type=str, help='one of: fetch_pdb, parse_pdb')
    parser.add_argument('pdb_name', type=str, help='name of pdb file without extension, e.g. ntkrnlmp')
    parser.add_argument('guid_age', nargs='?', help='guid/age of the pdb file')

    args = parser.parse_args()

    if args.action == "parse_pdb":
        make_pdb_profile(args.pdb_name)
    elif args.action == "fetch_pdb":
        fetch_pdb(args.pdb_name, args.guid_age)
    else:
        raise RuntimeError('Unknown action')
