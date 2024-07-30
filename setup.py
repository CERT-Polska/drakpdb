from setuptools import setup, Extension

setup_args = dict(
    ext_modules=[
        Extension(
            name='drakpdb.pdbparse._undname',
            sources=["drakpdb/pdbparse/_undname/undname.c", "drakpdb/pdbparse/_undname/undname_py.c"],
        )
    ]
)

setup(**setup_args)
