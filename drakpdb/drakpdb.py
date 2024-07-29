import json
import os
import re
from typing import Union

import pefile
from construct.lib.containers import Container

from .pdbparse.dbgold import CV_RSDS_HEADER
from .pdbparse.symlookup import DummyOmap
from . import pdbparse
from .type_info import process_tpi


class Demangler(object):
    """A utility class to demangle VC++ names.

    This is not a complete or accurate demangler, it simply extract the name and
    strips out args etc.

    Ref:
    http://www.kegel.com/mangle.html
    """

    STRING_MANGLE_MAP = {
        r"?0": ",",
        r"?1": "/",
        r"?2": r"\\",
        r"?4": ".",
        r"?3": ":",
        r"?5": "_",  # Really space.
        r"?6": ".",  # Really \n.
        r"?7": '"',
        r"?8": "'",
        r"?9": "-",
        r"?$AA": "",
        r"?$AN": "",  # Really \r.
        r"?$CF": "%",
        r"?$EA": "@",
        r"?$CD": "#",
        r"?$CG": "&",
        r"?$HO": "~",
        r"?$CI": "(",
        r"?$CJ": ")",
        r"?$DM1": "</",
        r"?$DMO": ">",
        r"?$DN": "=",
        r"?$CK": "*",
        r"?$CB": "!",
    }

    STRING_MANGLE_RE = re.compile(
        "("
        + "|".join(
            [x.replace("?", "\\?").replace("$", "\\$") for x in STRING_MANGLE_MAP]
        )
        + ")"
    )

    def _UnpackMangledString(self, string):
        string = string.split("@")[3]
        result = "str:" + self.STRING_MANGLE_RE.sub(
            lambda m: self.STRING_MANGLE_MAP[m.group(0)], string
        )
        return result

    SIMPLE_X86_CALL = re.compile(r"[_@]([A-Za-z0-9_]+)@(\d{1,3})$")
    FUNCTION_NAME_RE = re.compile(r"\?([A-Za-z0-9_]+)@")

    def DemangleName(self, mangled_name):
        """Returns the de-mangled name.

        At this stage we don't really do proper demangling since we usually dont
        care about the prototype, nor c++ exports. In the future we should
        though.
        """
        m = self.SIMPLE_X86_CALL.match(mangled_name)
        if m:
            # If we see x86 name mangling (_cdecl, __stdcall) with stack sizes
            # of 4 bytes, this is definitely a 32 bit pdb. Sometimes we dont
            # know the architecture of the pdb file for example if we do not
            # have the original binary, but only the GUID as extracted by
            # version_scan.
            # TODO set arch to i386
            return m.group(1)

        m = self.FUNCTION_NAME_RE.match(mangled_name)
        if m:
            return m.group(1)

        # Strip the first _ from the name. I386 mangled constants have a
        # leading _ but their AMD64 counterparts do not.
        if mangled_name and mangled_name[0] in "_.":
            mangled_name = mangled_name[1:]

        elif mangled_name.startswith("??_C@"):
            return self._UnpackMangledString(mangled_name)

        return mangled_name


def make_symstore_hash(
    codeview_struct: Union[Container, pdbparse.PDBInfoStream]
) -> str:
    """
    If `codeview_struct` is an instance of Container, it should be returned from `CV_RSDS_HEADER.parse()`.
    """
    guid = codeview_struct.GUID
    guid_str = "%08x%04x%04x%s" % (
        guid.Data1,
        guid.Data2,
        guid.Data3,
        guid.Data4.hex(),
    )
    return "%s%x" % (guid_str, codeview_struct.Age)


def make_pdb_profile(
    filepath, dll_origin_path=None, dll_path=None, dll_symstore_hash=None
):
    pdb = pdbparse.parse(filepath)

    try:
        sects = pdb.STREAM_SECT_HDR_ORIG.sections
        omap = pdb.STREAM_OMAP_FROM_SRC
    except AttributeError:
        # In this case there is no OMAP, so we use the given section
        # headers and use the identity function for omap.remap
        sects = pdb.STREAM_SECT_HDR.sections
        omap = DummyOmap()

    gsyms = pdb.STREAM_GSYM
    tpi = process_tpi(pdb)
    profile = {"$FUNCTIONS": {}, "$CONSTANTS": {}, **tpi}
    mapped_syms = {"$CONSTANTS": {}, "$FUNCTIONS": {}}

    for sym in gsyms.globals:
        try:
            off = sym.offset
            sym_name = sym.name
            virt_base = sects[sym.segment - 1].VirtualAddress
            mapped = omap.remap(off + virt_base)
            if (sym.symtype & 2) == 2:
                target_key = "$FUNCTIONS"
            else:
                target_key = "$CONSTANTS"
        except IndexError:
            # skip symbol because segment was not found
            continue
        except AttributeError:
            # missing offset in symbol?
            continue

        sym_name = Demangler().DemangleName(sym_name)

        if sym_name not in mapped_syms[target_key]:
            mapped_syms[target_key][sym_name] = list()

        mapped_syms[target_key][sym_name].append(mapped)

    for target_key, sym_dict in mapped_syms.items():
        for sym_name, value_set in sym_dict.items():
            ndx = 0

            for mapped in sorted(value_set):
                if ndx == 0:
                    next_sym_name = sym_name
                else:
                    next_sym_name = "{}_{}".format(sym_name, ndx)

                ndx += 1
                profile[target_key][next_sym_name] = mapped

    del mapped_syms
    pdb_symstore_hash = make_symstore_hash(pdb.STREAM_PDB)
    base_filename = os.path.splitext(os.path.basename(filepath))[0]

    profile["$METADATA"] = {
        "DLL_GUID_AGE": dll_symstore_hash,
        "GUID_AGE": pdb_symstore_hash,
        "PDBFile": os.path.basename(filepath),
        "ProfileClass": base_filename[0].upper() + base_filename[1:].lower(),
        "Timestamp": pdb.STREAM_PDB.TimeDateStamp.replace(tzinfo=None).strftime(
            "%Y-%m-%d %H:%M:%SZ"
        ),
        "Type": "Profile",
        "Version": pdb.STREAM_PDB.Version,
    }

    # Additional metadata requested by the ApiVectors developers
    profile["$EXTRAS"] = {}
    if dll_origin_path:
        profile["$EXTRAS"]["DLLPath"] = str(dll_origin_path)

    if dll_path:
        try:
            pe = pefile.PE(dll_path, fast_load=True)
            profile["$EXTRAS"]["ImageBase"] = hex(pe.OPTIONAL_HEADER.ImageBase)
        except AttributeError:
            # I think that DLLs have some sanity and the optional header is
            # always present. Ignore this error if it happens
            pass

    return json.dumps(profile, indent=4, sort_keys=True)


def pe_codeview_data(filepath):
    pe = pefile.PE(filepath, fast_load=True)
    pe.parse_data_directories()
    try:
        codeview = next(
            filter(
                lambda x: x.struct.Type
                == pefile.DEBUG_TYPE["IMAGE_DEBUG_TYPE_CODEVIEW"],
                pe.DIRECTORY_ENTRY_DEBUG,
            )
        )
    except StopIteration:
        print("Failed to find CodeView in pdb")
        raise RuntimeError("Failed to find GUID age")

    offset = codeview.struct.PointerToRawData
    size = codeview.struct.SizeOfData
    codeview_struct = CV_RSDS_HEADER.parse(pe.__data__[offset : offset + size])
    return {
        "filename": codeview_struct.Filename,
        "symstore_hash": make_symstore_hash(codeview_struct),
    }
