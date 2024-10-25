import asyncio
import os
from pathlib import Path
from typing import Dict, List

import aiofiles
from aiohttp import ClientSession
from aiohttp.client_exceptions import (
    ClientConnectorCertificateError,
    ClientConnectorError,
    ClientResponseError,
)
from bs4 import BeautifulSoup

SAVE_DIR = Path(__file__).resolve().parent.parent.parent / "data"
PARSE_URL = "https://news.ycombinator.com/"
VISITED_NEW: Dict[str, str] = dict()


async def main(interval: int) -> None:
    async with ClientSession() as session:
        while True:
            page = await get_html(session, PARSE_URL)
            _dict_news = parse_main(page)
            for k, v in _dict_news.items():
                if k in VISITED_NEW.keys():
                    continue
                VISITED_NEW[k] = v
                news_content = await get_html(session, v)
                asyncio.create_task(save_page(news_content, k))
                comments_link = f"https://news.ycombinator.com/item?id={v}"
                comment_content = await get_html(session, comments_link)
                comment_lins = parse_comments(comment_content)
                for link in comment_lins:
                    link_content = await get_html(session, link)
                    await save_page(link_content, f"{k}_comments")
            await asyncio.sleep(interval)


async def get_html(session: ClientSession, url: str) -> str:
    _result: str = ""
    try:
        async with session.get(url) as response:
            try:
                response.raise_for_status()
            except (ClientResponseError,):
                pass
            _result = await response.text()
    except (ClientConnectorCertificateError, ClientConnectorError):
        pass
    return _result


async def save_page(content: str, file_name: str) -> None:
    directory = SAVE_DIR / file_name
    os.makedirs(directory, exist_ok=True)
    async with aiofiles.open(
        directory / f"{file_name}.html", "w+", encoding="utf-8"
    ) as f:
        await f.write(content)


def parse_main(content: str) -> Dict[str, str]:
    soup = BeautifulSoup(content, "html.parser")

    links = [
        x.find(lambda tag: tag.name == "a").get("href")
        for x in soup.find_all(
            lambda tag: tag.name == "span" and tag.get("class") == ["titleline"]
        )
    ]

    ids = [
        x.get("id")
        for x in soup.find_all(
            lambda tag: tag.name == "tr" and tag.get("class") == ["athing"]
        )
    ]

    return dict(zip(ids, links))


def parse_comments(content: str) -> List[str]:
    soup = BeautifulSoup(content, "html.parser")
    links = [
        x.find_all(lambda tag: tag.name == "a" and tag.get("href").find("reply"))
        for x in soup.find_all(
            lambda tag: tag.name == "div" and tag.get("class") == ["comment"]
        )
    ]

    result_links = []
    for link in links:
        if link:
            soup = BeautifulSoup(str(link), "html.parser")
            lin = [x.get("href") for x in soup.find_all(lambda tag: tag.name == "a")]
            result_links.extend(lin)

    return result_links


if __name__ == "__main__":
    asyncio.run(main(30))
