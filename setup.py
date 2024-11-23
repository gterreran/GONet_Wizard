from setuptools import setup, find_packages

setup(
    name='GONet_utils',
        version='0.0.1',
        install_requires=[
            'numpy',
            'pillow',
            'tifffile',
        ],
    packages=find_packages(
        where='src',
        include=['GONet_utils'],
    ),
)