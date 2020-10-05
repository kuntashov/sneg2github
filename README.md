# Transfer issues from snegopat.ru/forum to infostart-hub

```sh
export GITHUB_TOKEN=your_token
python3 sneg2github.py --db ./test.db init-db
python3 sneg2github.py --db ./test.db export-from-forum
python3 sneg2github.py --db ./test.db import-to-github
```
