from setuptools import setup, find_packages

setup(
    name="cokeydex",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "typer>=0.9.0",
        "rich>=13.7.0",
        "pydantic>=2.5.0",
        "pydantic-settings>=2.1.0",
        "openai>=1.8.0",
        "anthropic",
        "google-generativeai",
        "python-dotenv>=1.0.0",
        "ruamel.yaml>=0.18.0",
        "chromadb>=0.4.22",
    ],
    entry_points={
        "console_scripts": [
            "cokeydex=cli.main:app",
        ],
    },
    python_requires=">=3.10",
)