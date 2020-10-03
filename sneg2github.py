import requests

import sqlite3
import os.path

from bs4 import BeautifulSoup


SNEGOBUGS_FORUM_URL = "https://snegopat.ru/forum/viewforum.php?f=8&sid=fe7bc0d24702e056da7ac4dc6a7d36fa"


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
        sql = sql.format({
            'ignore':ignore_kwd,
            'table':table,
            'fields':','.join(fields.keys),
            'values': ','.join(['?'] * len(fields))
        })
        return self.execute(sql, tuple(fields.values())).lastrowid



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
        'author': cells[3].select_one('.topicauthor').getText()
    }


if __name__ == '__main__':
    from pprint import pprint
    pprint(load_forum_topics(SNEGOBUGS_FORUM_URL))
