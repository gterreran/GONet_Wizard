from setuptools import find_packages, setup

with open("README.md", "r") as inp:
    long_description = inp.read()

setup(
    name="GONet_wizard",
    version="0.8.0",
    description="Tools and methods to handle GONet data.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/gterreran/GONet_Wizard",
    author="Giacomo Terreran",
    author_email="gterreran@adlerplanetarium.org",
    license="MIT",
    packages=find_packages(),
    include_package_data=True,
    entry_points = {
        'console_scripts': [ 'GONet_Wizard=GONet_Wizard.__main__:main']
        },
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.8",
        "Operating System :: OS Independent",
    ],
    install_requires=[
        'numpy',
        'pillow',
        'matplotlib',
        'tifffile==2023.7.10',
        'python-dateutil',
        'dash==2.18.2',
        'dash_daq',
        'python-dotenv',
        'paramiko',
        'scp',
    ],
    extras_require={
        "dev": ["pytest>=7.0", "twine>=4.0.2"],
    },
    python_requires=">=3.10",
)