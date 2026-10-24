from setuptools import find_packages, setup

setup(
    name="claude-cache-idiocracy",
    version="0.1.0",
    description="Local Claude Code context, read, retry and subagent guard",
    package_dir={"": "src"},
    packages=find_packages("src"),
    python_requires=">=3.9",
    entry_points={
        "console_scripts": [
            "hache-guard=hache_guard.cli:main",
            "hache-claude=hache_guard.supervisor:main",
            "hache-compact=hache_guard.cli:main",
            "hache-doctor=hache_guard.doctor:main",
            "hache-proxy=hache_guard.proxy:main",
        ]
    },
)
