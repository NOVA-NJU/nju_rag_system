"""Central configuration for the crawler module running inside the unified backend."""
from __future__ import annotations

import os


def _get_bool_env(name: str, default: bool) -> bool:
    """Parse boolean environment flags with sensible defaults."""
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


# Service ports (the crawler no longer exposes its own server but we keep the knob for completeness)
CRAWLER_PORT = int(os.getenv("CRAWLER_PORT", "8000"))

# Crawl scheduling
CRAWL_INTERVAL = int(os.getenv("CRAWL_INTERVAL", "3600"))
REQUEST_TIMEOUT = 30
MAX_RETRIES = 3
AUTO_CRAWL_ENABLED = _get_bool_env("AUTO_CRAWL_ENABLED", True)

# Whether to push crawled content into the vector store via direct function calls
VECTOR_SYNC_ENABLED = _get_bool_env("VECTOR_SYNC_ENABLED", True)

# OCR configuration (override via env if needed)
TESSERACT_CMD = "" # os.getenv("TESSERACT_CMD", r"D:\Apps\tesseract\tesseract.exe")
TESSDATA_DIR = "" #os.getenv("TESSDATA_DIR", r"D:\Apps\tesseract\tessdata")

# Database configuration
DATABASE_PATH = os.getenv("CRAWLER_DB_PATH", "./data/crawler.db")

# Target websites (copied from legacy NRS_data module)
TARGET_SOURCES = [
    {
        "id": "bksy_ggtz",
        "name": "本科生院-公告通知",
        "base_url": "https://jw.nju.edu.cn",
        "list_url": "https://jw.nju.edu.cn/ggtz/list1.htm",
        "max_pages": 5,
        "headers": {
            "USER_AGENT": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0"
            ),
            "host": "jw.nju.edu.cn",
        },
        "selectors": {
            "item_container": "#wp_news_w6 li.news",
            "date": ".news_meta",
            "title": ".news_title a",
            "url": ".news_title a",
            "type": ".wjj .lj",
        },
        "detail_selector": "#d-container .wp_articlecontent p",
    }
]

DETAIL_SELECTORS = {
    "meta_selector": {
        "item_container": "#d-container",
        "publisher": ".arti_publisher",
        "views": ".arti_views",
    },
    "text_selector": {
        "item_container": "#d-container",
        "content": ".wp_articlecontent",
    },
    "img_selector": {
        "item_container": "#d-container",
        "images": ".wp_articlecontent img[src]",
    },
    "pdf_selector": {
        "item_container": "#d-container",
        "files": ".wp_articlecontent a[href$=\".pdf\"]",
        "name": ".wp_articlecontent a[href$=\".pdf\"] span",
    },
    "doc_selector": {
        "item_container": "#d-container",
        "files": ".wp_articlecontent a[href$=\".doc\"], .wp_articlecontent a[href$=\".docx\"]",
        "name": ".wp_articlecontent a[href$=\".doc\"], .wp_articlecontent a[href$=\".docx\"]",
    },
    "embedded_pdf_selector": {
        "item_container": "#d-container",
        "viewer": ".wp_articlecontent iframe.wp_pdf_player",
        "download_link": ".wp_articlecontent img[src$=\"icon_pdf.gif\"] + a",
    },
}
