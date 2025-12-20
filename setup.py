from setuptools import setup, find_packages

setup(
    name="align_test",
    version="0.1.0",
    description="LLM Alignment Testing Framework - Test model behavior in scenarios with ethical concerns",
    author="Your Name",
    author_email="your.email@example.com",
    packages=find_packages(),
    python_requires=">=3.9",
    install_requires=[
        "openai>=1.0.0",
        "pandas>=2.0.0",
        "matplotlib>=3.7.0",
        "seaborn>=0.12.0",
        "pydantic>=2.0.0",
        "pyyaml>=6.0",
    ],
    extras_require={
        "vllm": ["vllm>=0.2.0"],
        "notebook": ["jupyter>=1.0.0", "ipykernel>=6.0.0"],
        "dev": ["pytest>=7.0.0", "black>=23.0.0", "mypy>=1.0.0"],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Science/Research",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)
