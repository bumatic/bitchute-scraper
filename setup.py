import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="bitchute-scraper",
    version="2.0.0",
    author="Marcus Burkhardt",
    author_email="marcus.burkhardt@gmail.com",
    description="A package to scrape BitChute platform recommendations",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/bumatic/bitchute-scraper",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Development Status :: 5 - Production/Stable",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires='>=3.7',
    install_requires=[
        'requests>=2.28.0',
        'pandas>=1.5.0',
        'selenium>=4.10.0',
        'webdriver-manager>=3.8.0',
        'retrying>=1.3.0',
    ],
    extras_require={
        'full': [
            'openpyxl>=3.0.0',      # Excel export
            'pyarrow>=10.0.0',      # Parquet export
        ],
        'dev': [
            'pytest>=7.0.0',
            'black>=22.0.0',
            'flake8>=5.0.0',
        ]
    },
    entry_points={
        'console_scripts': [
            'bitchute-scraper=bitchute.cli:main',
        ],
    },
    keywords=[
        'bitchute', 'api', 'scraper', 'video', 'data-collection'
    ],
)