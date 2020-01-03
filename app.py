import logging
import os
import re
import time
import traceback
from dotenv import load_dotenv

import coloredlogs
import praw
import requests
from imgurpython import ImgurClient
from imgurpython.helpers.error import ImgurClientError, ImgurClientRateLimitError
from tqdm import tqdm

load_dotenv()
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    if not os.path.exists("logs"):
        os.mkdir("logs")
    timestr = time.strftime("%d-%m-%Y--%H-%M-%S")
    logger.addHandler(logging.FileHandler(f"logs/{timestr}.log"))
    # change level to DEBUG for debug logging
    coloredlogs.install(level="INFO", logger=logger, fmt="[%(levelname)s] %(asctime)s: %(message)s",
                        datefmt="[%m-%d-%Y %I:%M:%S]")

imgur_regex = re.compile(r'(https://i.imgur.com/(.*))(\?.*)?')
imgur_album_regex = re.compile(r'(http://imgur.com/a/(.*))(\?.*)?')
gfycat_regex = re.compile(r'(https://gfycat.com/(.*))(\?.*)?')
gfycat_album_regex = re.compile(r'(https://gfycat.com/(.*))(/collections/)(.*)?')
image_regex = re.compile(r'(png|jpg|jpeg)')

imgur_client_id = os.getenv("IMGUR_CLIENT_ID")
imgur_client_secret = os.getenv("IMGUR_CLIENT_SECRET")
imgur_client = ImgurClient(imgur_client_id, imgur_client_secret)

subreddits = []

gfycat_api_url = "https://api.gfycat.com/v1/gfycats/"
gfycat_albums_api_url = "https://api.gfycat.com/v1/users/%s/albums/%s"
reddit = praw.Reddit(client_id=os.getenv("REDDIT_CLIENT_ID"), client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
                     user_agent="Scrapper")

# check if the images directory exists and create if not
if not os.path.exists("images"):
    try:
        os.mkdir("images")
        logger.debug("Created images dir")
    except Exception as e:
        logger.critical(f"Failed to create images directory! {e}")
    else:
        logger.debug("Images dir exists")


def download_from_url(url, dst):
    """
    @param: url to download file
    @param: dst place to put the file
    """
    file_size = int(requests.head(url).headers["Content-Length"])
    if os.path.exists(dst):
        logger.debug("file exists")
        first_byte = os.path.getsize(dst)
    else:
        first_byte = 0
    if first_byte >= file_size:
        return file_size
    header = {"Range": "bytes=%s-%s" % (first_byte, file_size)}
    pbar = tqdm(
        total=file_size, initial=first_byte,
        unit='B', unit_scale=True, desc=url.split('/')[-1])
    req = requests.get(url, headers=header, stream=True)
    with(open(dst, 'ab')) as f:
        for chunk in req.iter_content(chunk_size=1024):
            if chunk:
                f.write(chunk)
                pbar.update(1024)
    pbar.close()
    return file_size


# loop all the subreddits for downloading
for subreddit in subreddits:
    if not os.path.exists(f"images\\{subreddit}"):
        try:
            os.mkdir(f"images\\{subreddit}")
            logger.debug("Subreddit dir created")
        except Exception as e:
            logger.critical(f"Failed to create subreddit image directory! {e}")
    else:
        logger.debug("subreddit dir exists")

    # fetch posts
    posts = reddit.subreddit(subreddit).new(limit=900)

    # loop posts
    for index, post in enumerate(posts):
        logger.debug(f"{900 - index} remaining from subreddit {subreddit}...")
        logger.debug(f"API Requests Available: {reddit.auth.limits['available']}; API Requests Used: {reddit.auth.limits['used']}")
        try:
            if "pornhub" in post.url:
                continue

            if gfycat_regex.match(post.url):
                gfycat_id = post.url.split("/")[-1].split("-")[0].split("?")[0]
                response = requests.get(f"{gfycat_api_url}{gfycat_id}").json()
                try:
                    direct_url = response["gfyItem"]["mp4Url"]
                    path = f"images\\{subreddit}\\{gfycat_id}.mp4"
                    download_from_url(direct_url, path)
                except KeyError:
                    logger.error(f"Gfycat doesn't contain a 'gfyItem' key, it may have been deleted. URL: {post.url}")
            elif gfycat_album_regex.match(post.url):
                match = gfycat_album_regex.match(post.url)
                user = match.group(1).split("/")[3].split("@")[1]
                album_id = match.group(4).split("/")[0]
                response = requests.get(gfycat_albums_api_url.format(user, album_id)).json()
                try:
                    gfys = response["publishedGfys"]
                    for gfy in gfys:
                        gfy_id = gfy["id"]
                        mp4_url = gfy["mp4Url"]
                        path = f"images\\{subreddit}\\{gfy_id}.mp4"
                        download_from_url(mp4_url, path)
                except Exception as e:
                    logger.error(f"Error downloading video from Gfycat collection! Error: {e}")

            elif imgur_regex.match(post.url):
                filename = post.url.split("/")[-1].split("?")[0]
                ext = filename.split(".")[-1]
                imgur_image_id = filename.split(".")[0]
                path = f"images\\{subreddit}\\{filename}"
                if image_regex.match(ext):
                    # is image
                    try:
                        image = imgur_client.get_image(imgur_image_id)
                        image_url = image.link
                        download_from_url(image_url, path)
                    except ImgurClientError as e:
                        logger.error(e)
                else:
                    try:
                        image = imgur_client.get_image(imgur_image_id)
                        if image["animated"] and image["type"] == "image/gif":
                            mp4_url = image["mp4"]
                            download_from_url(mp4_url, path)
                        else:
                            image_url = image.link
                            download_from_url(image_url, path)
                    except ImgurClientError as e:
                        logger.error(f"Imgur API Error! Error: {e}")
                    except TypeError as e:
                        try:
                            download_from_url(post.url, path)
                        except Exception as e1:
                            logger.info(f"TypeError - URL: {post.url}")
                            logger.error(f"Failed to download image! Error: {e1}; Image URL: {post.url}")

            elif imgur_album_regex.match(post.url):
                album_id = post.url.split("/")[-1].split("?")[0]
                album = imgur_client.get_album(album_id)
                if album.images_count > 0:
                    for image in album.images:
                        if image["animated"] and image["type"] == "image/gif":
                            mp4_url = image["mp4"]
                            filename = mp4_url.split("/")[-1].split("?")[0]
                            ext = filename.split(".")[-1]
                            path = f"images\\{subreddit}\\{filename}"
                            download_from_url(mp4_url, path)
                        else:
                            image_url = image["link"]

                            filename = image_url.split("/")[-1].split("?")[0]
                            ext = filename.split(".")[-1]
                            path = f"images\\{subreddit}\\{filename}"
                            download_from_url(image_url, path)
        except ImgurClientRateLimitError as e:
            logger.critical(f"Imgur API Rate Limit! Error: {e}")
        except Exception as e:
            traceback.print_exc()
