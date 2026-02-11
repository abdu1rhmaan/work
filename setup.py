from setuptools import setup, find_packages

setup(
    name="talabat-driver-wallet",
    version="1.0.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "textual>=0.34.0",
        "rich>=13.0.0",
        "pandas>=2.0.0",
        "numpy>=1.24.0",
    ],
    entry_points={
        "console_scripts": [
            "work=talabat_wallet.__main__:main",
        ],
    },
)