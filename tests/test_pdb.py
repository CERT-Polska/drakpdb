from drakpdb.drakpdb import make_pdb_profile


def test_pdb_profile(pdb_file):
    profile = make_pdb_profile(pdb_file)
    assert "$STRUCTS" in profile
    assert profile["$FUNCTIONS"]
    assert profile["$CONSTANTS"]
    assert profile["$METADATA"]
