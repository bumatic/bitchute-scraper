import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="bitchute-scraper", 
    version="0.1.8",
    author="Marcus Burkhardt",
    author_email="marcus.burkhardt@gmail.com",
    description="A package to scrape BitChute platform recommendations using Selenium.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/bumatic/bitchute-scraper",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
    install_requires = ['beautifulsoup4', 'markdownify', 'pandas', 'python-dateutil', 'retrying', 'selenium', 'tqdm', 
'webdriver-manager'],
)
