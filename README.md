# 🛠️ Reddit Scraper Tool

A multi-threaded, Python based subreddit Scraper that utilizes PRAW and scrapes data from various subreddits and saves it into JSON files. 

**NOTE:** This tool was the first part of a larger scale project, in which there existed an inverted index built using PyLucene to parse the JSON files. This handled the search in the backend, and there was also a web UI frontend, but these files were loss in various data transfers. 

<div align="center">
  <img src=redditscraper-img.png alt="Reddit Search Engine">
</div>

## ⚙️ Technologies
- `Python`

## ✅ Features
- Multi-threaded Reddit crawler built in python using threading and queue modules
- 7 worker threads
- 1 producer thread
- Posts duplication handler to avoid checking same posts more than once
- Works with any subreddit

## 👩🏽‍🍳 The "Why"
Reddit is one of the largest social platforms where users share experiences, ask for advice, and debate everyday issues. The goal was to create a search engine that helps users find relevant advice posts from subreddits like AITA, AmIOverreacting, AmITheDevil, AskReddit, and more. Instead of browsing manually, users can search posts by keywords, rank results by relevance, recency, or upvotes, and explore advice more efficiently.


## 📏 The Architecture
As mentioned earlier, the system had two main components:

### Crawler & Data Collection
- Built in Python with `praw`, `threading`, `queue`, and `BeautifulSoup`.
- Multi-threaded producer-consumer pipeline (1 producer + 7 workers).
- Collected posts across multiple Reddit filters (hot, new, top, rising).
- Deduplication using post IDs stored in a `set`.
- Data written to segmented `.json` files (10MB max each) and `.csv` log files for tracking.

### Search Engine
- Indexer: Uses PyLucene to parse JSON Reddit data and build an inverted index.
- Search Backend: Flask server with Lucene’s `QueryParser` and `IndexSearcher` to rank/filter results.
- Frontend: Web UI inspired by traditional search engines, supporting keyword queries and filtering by date/upvotes.

## 📚 Challenges and What I Learned

This project taught me a lot about multi-threading and scraping data.