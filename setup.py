import os
from setuptools import setup, Extension, find_packages
import sysconfig

cpython_internal_include = os.path.join(sysconfig.get_path("include"), "internal")

setup(
    ext_modules=[
        Extension(
            name="cryo._builtin_helpers",
            sources=["_builtin_helpers.c"],
            include_dirs=[
                cpython_internal_include
            ])
    ],
    packages=find_packages()
)
