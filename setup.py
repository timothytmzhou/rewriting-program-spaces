from setuptools import setup, find_packages

setup(
    name='rewriting_program_spaces',
    version='1.0',
    description='A module for parsing partial programs into representations of sets of parse trees and sets of ASTs.',
    packages=find_packages(exclude="tests")
)
