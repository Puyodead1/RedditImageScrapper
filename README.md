# RedditImageScrapper
Scrape images from reddit using Python

![GitHub](https://img.shields.io/github/license/Puyodead1/RedditImageScrapper?style=plastic)

Python Version 3+ (Developed with 3.8)

Requires an imgur client id and secret (used for getting images from albums)<br>
Reddit client id and secret is optional but recommended

# How to use
edit the ``app.py`` file and locate the line with ``subreddits = []``, put the names of subreddits to scrape in this array, ex: ``subreddits = ["memes", "funny", "programminghumor"]``

you can enable debug logging by changing ``level="INFO"`` to ``level="DEBUG"``

# PyPI Packages Used
- [coloredlogs](https://pypi.org/project/coloredlogs/)
- [PRAW](https://pypi.org/project/praw/)
- [python-dotenv](https://pypi.org/project/python-dotenv/)
- [imgurpython](https://pypi.org/project/imgurpython/)
- [tqdm](https://pypi.org/project/tqdm/)
