from setuptools import setup, find_packages

setup(
    name="youtube_fetcher",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "youtube-transcript-api",
        "yt-dlp",
        "requests",
    ],
    author="NateAlyzer Team",
    description="A robust YouTube transcript fetcher with multi-layer fallback strategies, designed for AI agents.",
    python_requires=">=3.8",
)
