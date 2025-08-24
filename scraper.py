import praw
import threading
import json
import csv
import os
import requests
import re
from queue import Queue
from datetime import datetime, timezone
from dotenv import load_dotenv
from bs4 import BeautifulSoup

#load vars from .env file (contains our api credentials) and initialize reddit api crendentials
load_dotenv()
REDDIT_CLIENT_ID = os.getenv('REDDIT_CLIENT_ID')
REDDIT_CLIENT_SECRET = os.getenv('REDDIT_CLIENT_SECRET')
REDDIT_USER_AGENT = os.getenv('REDDIT_USER_AGENT')
SUBREDDIT_NAME = os.getenv('SUBREDDIT_NAME')

#make praw reddit instnace
reddit = praw.Reddit(
    client_id=REDDIT_CLIENT_ID,     #uses given credentials
    client_secret=REDDIT_CLIENT_SECRET,
    user_agent=REDDIT_USER_AGENT
)

#global vars and configs
post_queue = Queue()        #que of reddit posts
visited_ids = set()         #already visited, to avoid dupes
visited_lock = threading.Lock()
NUM_WORKERS = 7     #num of threads used
SENTINEL = None     #when to stop, but reddit has built in stop already 
MAX_FILE_SIZE = 10 * 1024 * 1024  #10 MB used for maximum 10mb json file
file_index = 0
json_file = None

def extract_urls(text):
    return re.findall(r'(https?://\S+)', text)

def get_title_from_url(url):      #finds url in posts and records page title of url
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=5)           #waits 5 seconds before timing out
        soup = BeautifulSoup(response.text, 'html.parser')      #beautifulsoup parses html
        return soup.title.string.strip() if soup.title else ''
    except Exception as e:
        return f"Error, couldn't get title: {e}"     #error handling for 5 sec timmeout

#init log file 
def initialize_log_file(subreddit_name):
    log_filename = f'{subreddit_name.lower()}_log.csv'
    log_file = open(log_filename, 'w', newline='', encoding='utf-8')
    log_writer = csv.writer(log_file)
    log_writer.writerow(['post_id', 'created_date'])    #post ids and crweation
    return log_file, log_writer

#init json files
def initialize_json_file(subreddit_name):
    global json_file, file_index
    filename = f'{subreddit_name.lower()}_{file_index}.json'
    json_file = open(filename, 'w', encoding='utf-8')
    file_index += 1     #adds 1 to index for next call, this is used when creating/namingn new json file bc new file is created when file is > 10mb

#writes to json file and log file
def write_to_files(post_data, log_writer):
    global json_file
    json_file.write(json.dumps(post_data, ensure_ascii=False) + '\n')       #writes to json
    log_writer.writerow([post_data['post_id'], post_data['created_date']])  #writee to log

    #file size checker, creates new when > 10mb
    if json_file.tell() >= MAX_FILE_SIZE:
        json_file.close()
        initialize_json_file(SUBREDDIT_NAME)

#scraper
def scrape_worker(thread_id, log_writer):       #runs using each thread
    while True:
        post = post_queue.get()                 #infinite loop until it reaches reddit's built in stopper
        if post is SENTINEL:                    #or designated SENTINEL stopper
            post_queue.task_done()
            break
        with visited_lock:
            if post.id in visited_ids:         #doesnt check dupes
                post_queue.task_done()
                continue
            visited_ids.add(post.id)
        try:
            post.comments.replace_more(limit=None)          #expands all comments and collects it
            comment_bodies = [comment.body for comment in post.comments.list()]
        except Exception as e:
            comment_bodies = [f"Error fetching comments: {e}"]

        #uses utc timezone, gives date as well as time in utc
        created_date = datetime.fromtimestamp(post.created_utc, tz=timezone.utc).isoformat()

        urls = extract_urls(post.selftext)
        url_titles = {url: get_title_from_url(url) for url in urls}

        #dictionary used for all info for json files
        post_data = {
            'post_id': post.id,
            'user_id': str(post.author),
            'post_title': post.title,
            'post_body': post.selftext,
            'num_upvotes': post.ups,
            'num_downvotes': post.downs,
            'post_score': post.score,
            'tags': post.link_flair_text,
            'created_date': created_date,
            'comments': comment_bodies,
            'post_permalink': f"https://reddit.com{post.permalink}",        #added permalink to post
            'post_urls': urls,
            'url_titles': url_titles
        }
        write_to_files(post_data, log_writer)       #writes to files
        post_queue.task_done()

#gets posts
def producer():
    print(f"Started getting posts from r/{SUBREDDIT_NAME}")
    subreddit = reddit.subreddit(SUBREDDIT_NAME)

    tabs = [
        subreddit.hot(limit=None),      #now checks all tabs instead of only 'hot'
        subreddit.new(limit=None),
        subreddit.top(limit=None),
        subreddit.rising(limit=None),
        #subreddit.best(limit=None)
    ]

    for tab in tabs:
        for post in tab:
            post_queue.put(post)

    # for post in subreddit.hot(limit=None):
    #     post_queue.put(post)
    for _ in range(NUM_WORKERS):
        post_queue.put(SENTINEL)        #adds stopper at end
    print("Finished getting posts")

def main():
    global json_file    #global json, accessed and closed later
    # subreddit_name = os.getenv('SUBREDDIT_NAME')    #subreddit to use
    #init log + json files and empty thread list
    threads = []
    log_file, log_writer = initialize_log_file(SUBREDDIT_NAME)
    initialize_json_file(SUBREDDIT_NAME)

    #producer threads
    print("Starting producer threads")
    producer_thread = threading.Thread(target=producer)
    producer_thread.start()

    #worker threads
    print("Starting worker threads")
    for i in range(NUM_WORKERS):        #uses dedicated thrreads
        t = threading.Thread(target=scrape_worker, args=(i, log_writer))
        t.start()
        threads.append(t)

    #wait threads complete
    producer_thread.join()
    for t in threads:
        t.join()

    #close both files safely when done
    json_file.close()
    log_file.close()

    print("\nAll threads have completed")       #notify when everything finished

if __name__ == '__main__':
    main()