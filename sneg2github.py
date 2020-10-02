import requests
from bs4 import BeautifulSoup


SNEGOBUGS_FORUM_URL = "https://snegopat.ru/forum/viewforum.php?f=8&sid=fe7bc0d24702e056da7ac4dc6a7d36fa"


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
