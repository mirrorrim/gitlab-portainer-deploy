from setuptools import setup

setup(
    name="gitlab-portainer-deploy",
    version="0.2",
    packages=["deploy"],
    zip_safe=False,
    install_requires=[
        "httpx",
        "typer",
        "yarl",
    ],
    entry_points="""
        [console_scripts]
        deploy=deploy.cli:app
    """
)
