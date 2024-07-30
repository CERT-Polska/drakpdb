from construct import EnumIntegerString

# Derived from rekall
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
    "T_32PHRESULT": ["Pointer", dict(target="long")],
    "T_64PINT4": ["Pointer", dict(target="long")],
    "T_64PLONG": ["Pointer", dict(target="long")],
    "T_64PQUAD": ["Pointer", dict(target="long long")],
    "T_64PSHORT": ["Pointer", dict(target="short")],
    "T_64PRCHAR": ["Pointer", dict(target="unsigned char")],
    "T_64PUCHAR": ["Pointer", dict(target="unsigned char")],
    "T_64PCHAR": ["Pointer", dict(target="char")],
    "T_64PWCHAR": ["Pointer", dict(target="String")],
    "T_64PULONG": ["Pointer", dict(target="unsigned long")],
    "T_64PUQUAD": ["Pointer", dict(target="unsigned long long")],
    "T_64PUSHORT": ["Pointer", dict(target="unsigned short")],
    "T_64PVOID": ["Pointer", dict(target="Void")],
    "T_64PREAL32": ["Pointer", dict(target="float")],
    "T_64PREAL64": ["Pointer", dict(target="double")],
    "T_64PUINT4": ["Pointer", dict(target="unsigned int")],
    "T_64PHRESULT": ["Pointer", dict(target="long")],
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
    "T_UINT8": ["unsigned long long", {}],
    "T_ULONG": ["unsigned long", {}],
    "T_UQUAD": ["unsigned long long", {}],
    "T_USHORT": ["unsigned short", {}],
    "T_VOID": ["Void", {}],
    "T_WCHAR": ["UnicodeString", {}],
    "T_HRESULT": ["long", {}],
}


def process_structure_reference(member):
    return [member.name, {}]


def process_pointer(member):
    return ["Pointer", {**process_base_type_info(member.utype)}]


def process_bitfield(member):
    return [
        "BitField",
        {
            "start_bit": member.position,
            "end_bit": member.position + member.length,
            **process_base_type_info(member.base_type),
        },
    ]


def process_base_type_info(node):
    target, target_args = process_member_type(node)
    if not target_args:
        return {"target": target}
    else:
        return {"target": target, "target_args": target_args}


def process_member_type(member_type):
    if isinstance(member_type, EnumIntegerString):
        return TYPE_ENUM_TO_VTYPE.get(member_type, "<unknown>")
    # TODO: Right now we don't handle LF_ARRAY, LF_ENUM,
    #       nested unnamed struct/unions etc
    complex_leaf_types = {
        "LF_STRUCTURE": process_structure_reference,
        "LF_UNION": process_structure_reference,
        "LF_BITFIELD": process_bitfield,
        "LF_POINTER": process_pointer,
    }
    if (
        not hasattr(member_type, "leaf_type")
        or member_type.leaf_type not in complex_leaf_types
    ):
        return ["<unknown>", {}]
    return complex_leaf_types[member_type.leaf_type](member_type)


def process_structure_member(member):
    return process_member_type(member.index)


def process_structure(struct):
    if struct.leaf_type != "LF_STRUCTURE":
        # Unhandled type of structure
        return [0, {}]
    if not hasattr(struct.fieldlist, "substructs"):
        # Usually T_NOTYPE
        return [0, {}]
    return [
        struct.size,
        {
            member.name: process_structure_member(member)
            for member in struct.fieldlist.substructs
        },
    ]


def process_tpi(pdb):
    """
    Processes Type Information into Rekall-like representation
    """
    return {
        "$STRUCTS": {
            name: process_structure(structure)
            for name, structure in pdb.STREAM_TPI.structures.items()
        }
    }
