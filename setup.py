from setuptools import find_packages, setup

with open("swiftpyaci/README.md", "r") as f:
    long_description = f.read()

setup(
    name="SwitftPyACI",
    version="0.0.10",
    description="A simple Cisco ACI Python Client",
    package_dir={"": "swiftpyaci"},
    packages=find_packages(where="swiftpyaci"),
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/0x2a-se/SwiftPyACI",
    author="0x2a-se",
    author_email="olle@x2a.se",
    license='Apache License 2.0',
    classifiers=[
            'Development Status :: 5 - Production/Stable',
            'Intended Audience :: Developers',
            'Intended Audience :: Network Administrators',
            'Intended Audience :: Telecommunications Industry',
            'License :: OSI Approved :: Apache Software License',
            'Programming Language :: Python :: 3',
        ],
    install_requires=["httpx >= 0.25.2"],
    extras_require={
        "dev": ["pytest>=7.0", "twine>=4.0.2"],
    },
    python_requires=">=3.10",
)