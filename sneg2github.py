import sys
import requests
import sqlite3
import os.path
import logging as logging

from bs4 import BeautifulSoup
from argparse import ArgumentParser


SNEGOBUGS_FORUM_URL = "https://snegopat.ru/forum/viewforum.php?f=8&sid=fe7bc0d24702e056da7ac4dc6a7d36fa"
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


def save_topics_to_db(topics):
    for topic in topics:
        DB.insert('topics', topic)
        logging.info('Loaded topic "{t}"'.format(t=topic['title']))


if __name__ == '__main__':

    argparser = parse_arguments()
    args = argparser.parse_args()

    DB = Database(args.db)

    if args.command == 'init-db':
        init_database()

    if args.command == 'export-from-forum':
        logging.info("Loading forum topics")
        topics = load_forum_topics(SNEGOBUGS_FORUM_URL)
        save_topics_to_db(topics)

    if args.command == 'import-to-github':
        logging.info("Uploading topics as issues")
        pass
