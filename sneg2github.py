import os
import sys
import time
import logging
import os.path
import sqlite3
import requests


from bs4 import BeautifulSoup
from argparse import ArgumentParser


SNEGOPAT_FORUM_URL = 'https://snegopat.ru/forum'
SNEGOBUGS_FORUM_PATH = "/viewforum.php?f=8"

GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')

DB = None


logging.getLogger('requests').setLevel(logging.CRITICAL)
fmt = '[%(asctime)s] %(filename)s:%(lineno)d %(levelname)s - %(message)s'
logging.basicConfig(
    stream=sys.stdout,
    format=fmt,
    level=logging.INFO,
    datefmt='%d.%m.%Y %H:%M:%S')


class Database:

    def __init__(self, path):
        self.path = os.path.expanduser(path)
        self._conn = sqlite3.connect(self.path, isolation_level=None)
        self._conn.row_factory = sqlite3.Row

    def __del__(self):
        self._conn.close()

    def execute(self, sql, args=()):
        cursor = self._conn.execute(sql, args)
        # self._conn.commit()
        return cursor

    def first(self, sql, args=()):
        cursor = self.execute(sql, args)
        if cursor is None:
            return None
        return cursor.fetchone()

    def get(self, sql, args):
        row = self.first(sql, args)
        if row is None:
            return None
        return row[0]

    def insert(self, table, fields, ignore=False):
        ignore_kwd = ''
        if ignore:
            ignore_kwd = 'OR IGNORE'
        sql = "INSERT {ignore} INTO {table} ({fields}) VALUES({values})"
        sql = sql.format(
            ignore=ignore_kwd,
            table=table,
            fields=','.join(fields.keys()),
            values=','.join(['?'] * len(fields))
        )
        return self.execute(sql, tuple(fields.values())).lastrowid


def get_db_schema():
    schema = {
        "topics": (
            "CREATE TABLE topics ("
            "  id integer primary key autoincrement,"
            "  title text not null,"
            "  href text not null unique,"
            "  author text DEFAULT '',"
            "  text text default ''"
            " )"
        )
    }
    return schema


def load_forum_topics(url):
    topics = []
    page = requests.get(url)
    soup = BeautifulSoup(page.content, "html.parser")
    topics_rows = soup.select('#pagecontent .tablebg tr')[3:-1]
    return [parse_topic_row(row.select('td')) for row in soup.select('#pagecontent .tablebg tr')[3:-1]]


def parse_topic_row(cells):
    a_topic = cells[2].select_one('.topictitle')
    return {
        'title': a_topic.getText(),
        'href': a_topic['href'],
        'author': cells[3].select_one('.topicauthor').getText(),
        'text': ''
    }


def parse_arguments():
    parser = ArgumentParser(description="Export snegopat.ru/forum to github.com issues")
    parser.add_argument('--db', help='Path to database')
    subparsers = parser.add_subparsers(help="commands", dest="command")

    subparsers.add_parser("init-db", description="Init script database")
    subparsers.add_parser("export-from-forum", description="Export snegopat forum topics to database")
    subparsers.add_parser("import-to-github", description="Import issues to github")

    return parser


def init_database():
    logging.info("Initializing database - Start")
    for table_name, stmt in get_db_schema().items():
        DB.execute(stmt)
        logging.info("Created table `%s`" % (table_name,))
    logging.info("Initializing database - Done")


def load_topics_message(topics):
    for topic in topics:
        logging.info(f'Loading topic {topic["href"]}')
        url = SNEGOPAT_FORUM_URL + topic["href"][1:]
        topic['text'] = load_topic_message(url)
    return topics


def load_topic_message(url):
    message = ''
    page = requests.get(url)
    soup = BeautifulSoup(page.content, "html.parser")
    rows = [author.parent.parent.parent for author in soup.select('.postauthor')]
    messages = []
    for row in rows:
        msg = parse_topic_message(row, url)

        messages.append(format_message(msg))

    return "\n<hr/>\n".join(messages)


def parse_topic_message(msg_row, url):
    a_title = msg_row.select('.gensmall')[0].select_one('a')
    return {
        'url': url + a_title['href'],
        'title': a_title.getText(),
        'author': msg_row.select_one('.postauthor').getText().strip(),
        'post': html_to_markdown(msg_row.select_one('.postbody'))
    }


def html_to_markdown(html):
    # Оставим пока для простоты в html, github нормально переваривает
    html = ''.join([str(tag) for tag in html.children])
    return html


def format_message(msg):
    parts = [];
    parts.append(f'<b>{msg["author"]}</b> <a href="{msg["url"]}">{msg["title"]}</a>')
    parts.append(msg["post"])
    return '\n'.join(parts);


def save_topics_to_db(topics):
    for topic in topics:
        DB.insert('topics', topic)
        logging.info('Loaded topic "{t}"'.format(t=topic['title']))


def import_to_github(owner, repo):
    sql = 'select title, text from topics where title != ?'
    for row in DB.execute(sql, ('Как писать об ошибках',)):
        create_issue(owner, repo, {
            'title': row['title'],
            'body': row['text'],
            'labels': ['bug', 'forum']
        })
        time.sleep(1.5)


def create_issue(owner, repo, issue):
    endpoint = f'https://api.github.com/repos/{owner}/{repo}/issues'
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/vnd.github.v3+json',
        'Authorization': f'token {GITHUB_TOKEN}'
    }
    r = requests.post(endpoint, headers=headers, json=issue)
    logging.info(r.json())


if __name__ == '__main__':

    argparser = parse_arguments()
    args = argparser.parse_args()

    DB = Database(args.db)

    if args.command == 'init-db':
        init_database()

    if args.command == 'export-from-forum':
        logging.info("Loading forum topics")
        for page in [0, 25]:
            url = SNEGOPAT_FORUM_URL + SNEGOBUGS_FORUM_PATH + f'&start={page}'
            topics = load_forum_topics(url)
            topics = load_topics_message(topics)
            save_topics_to_db(topics)
            break

    if args.command == 'import-to-github':
        import_to_github('kuntashov', 'snegopat-test-issues')
        pass
