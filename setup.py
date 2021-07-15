import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()


requestor_requirements = [
    "httpx==0.18.2",
    "yapapi-service-manager @ git+https://github.com/golemfactory/yapapi-service-manager.git",
]
provider_requirements = [
    "requests==2.25.1",
    "requests-unixsocket==0.2.0",
    "click==8.0.1",
]
test_requirements = requestor_requirements.copy()
test_requirements += [
    "pytest==6.2.3",
    "pytest-asyncio==0.15.1",
]


setuptools.setup(
    name="yagna-requests",
    version="0.0.0",
    author="Golem Factory, Jan Betley",
    author_email="contact@golem.network, jan.betley@golem.network",
    description="send requests to the server running on a provider",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://handbook.golem.network/yapapi/",
    download_url="https://github.com/golemfactory/yagna-requests",
    packages=setuptools.find_packages(),

    #   NOTE: all requirements are in "extras", because there are no common dependencies
    #         for the requestor and provider side, so the library has to be installed either
    #         as [provider] or as [requestor]
    install_requires=[],
    extras_require={
        'requestor': requestor_requirements,
        'provider': provider_requirements,
        'tests': test_requirements,
    },
    tests_require=test_requirements,
    classifiers=[
        "Development Status :: 0 - Alpha",
        "Framework :: YaPaPI",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU Lesser General Public License v3 or later (LGPLv3+)",
        "Operating System :: OS Independent",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Distributed Computing",
    ],
    python_requires=">=3.6.1",
)
