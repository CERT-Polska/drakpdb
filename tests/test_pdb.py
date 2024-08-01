from drakpdb.drakpdb import make_pdb_profile


def test_pdb_profile(pdb_file):
    profile = make_pdb_profile(pdb_file)
    assert "$STRUCTS" in profile
    assert profile["$FUNCTIONS"]
    assert profile["$CONSTANTS"]
    assert profile["$METADATA"]


def test_kernel_types(nt_kernel_pdb_file):
    profile = make_pdb_profile(nt_kernel_pdb_file)
    structs = profile["$STRUCTS"]
    # There are parsed structs
    assert structs
    # including unions like _HANDLE_TABLE_ENTRY
    assert "_HANDLE_TABLE_ENTRY" in structs
    # Size of structure is more than 0
    assert structs["_HANDLE_TABLE_ENTRY"][0] > 0
