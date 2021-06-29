import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

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
    install_requires=[
        "requests==2.25.1",
        "requests-unixsocket==0.2.0",
        "httpx==0.18.2",
        "yapapi-service-manager git+https://github.com/golemfactory/yapapi-service-manager.git",
    ],
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
