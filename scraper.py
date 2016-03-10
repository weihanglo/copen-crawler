#!/usr/bin/env python3
# -*- coding: utf-8 -*-


import io
import re
from collections import Counter
from operator import itemgetter

import requests
from jseg.jieba import Jieba


class PttScraper(requests.Session):
    """
    Usage::
        # unformatted article
        url = 'https://www.ptt.cc/bbs/Gossiping/M.1457406335.A.0BA.html'

        # formatted ariticle
        url = 'https://www.ptt.cc/bbs/Gossiping/M.1457404523.A.DAD.html'

        ptt = PttScraper()
        ptt.fetch_html(url)
        ptt.extract_meta()
        ptt.extract_content()
        ptt.extract_news_meta()
        ptt.clean()

    """

    _re_meta = re.compile(r"""
        meta-tag">(.*?)</span>
        (?:.|\s)+?meta-value">
        (.*?)</span>
        """, re.VERBOSE)
    _re_content = re.compile(r"""
        <div\sid="main-content".*meta-value">
        .*?</div>
        (.*?)
        \n--+\n(?:Sent|<span[^>]*>※\s發信站)
        """, re.DOTALL | re.VERBOSE)
    _re_news_meta_in_content = re.compile(r"""
        (?:\d\.)?媒體來源:(?P<media>.*?)
        (?:\d\.)?完整新聞標題:(?P<news_title>.*?)
        (?:\d\.)?完整新聞內文:(?P<news_content>.*?)
        (?:\d\.)?完整新聞連結\s\(或短網址\):(?P<news_url>.*?)
        (?:\d\.)?備註:(?P<note>.*)
        (?:\n--+\n)?(?:Sent|<span[^>]*?>※\s發信站)?
        """, re.DOTALL | re.VERBOSE)

    def __init__(self):
        super().__init__()
        self.cookies.set(name='over18', value='1')
        self.url = None
        self.html = None
        self.meta = {}
        self.content = None

    def fetch_html(self, url):
        res = self.get(url)
        self.html = res.text
        self.url = url

    def extract_meta(self):
        matches = self._re_meta.findall(self.html)
        for match in matches:
            key = {
                '作者': 'author',
                '看板': 'ptt_board',
                '標題': 'ptt_title',
                '時間': 'date',
            }[match[0]]
            self.meta[key] = match[1]

        author = self.meta.get('author')
        self.meta.update({
            'author': re.sub(r'\s\(.*$', '', author if author else ''),
            'article_type': 'news',
            'source': 'PTT',
            'ptt_url': self.url,
        })
        return self.meta

    def extract_content(self):
        matches = self._re_content.search(self.html)
        self.content = matches.group(1)
        return self.content

    def extract_news_meta(self):
        matches = self._re_news_meta_in_content.search(self.content)
        if matches:
            meta_dict = matches.groupdict()

            for k, v in meta_dict.items():
                meta_dict[k] = v.strip()

            url = re.search(r'(?<=href=").*?(?=")', meta_dict['news_url'])
            meta_dict['news_url'] = url.group() if url else ''

            if meta_dict['news_content']:
                self.content = meta_dict.pop('news_content')
            else:
                del meta_dict['news_content']
        else:
            meta_dict = {
                'media': '',
                'news_title': '',
                'news_content': '',
                'news_url': '',
                'note': '',
            }

        self.meta.update(meta_dict)
        return self.meta

    def clean(self, tag=True, url=True, punct=True):
        if tag:
            self.content = re.sub(r'</?[^>]*>', '', self.content)
        if url:
            self.content = re.sub(r'https?://\S+', '', self.content)
        if punct:
            self.content = re.sub(r'[^\n\w]', ' ', self.content)
        self.content = self.content.strip()

class Coder(Jieba):
    """
    Usage::
        content = '''
        For Unicode (str) patterns:
            Matches Unicode word characters; this includes most characters.
        For 8-bit (bytes) patterns:
            Matches characters considered alphanumeric in the ASCII character.

        Matches any character which is not a Unicode word character.
        '''
        meta = dict(name='re', author='python3.5')

        coder = Coder()
        coder.print_vrt('demo.vrt', content, meta)
        coder.summary(content)

    """

    def __init__(self, *args, **kwargs):
        super(Coder, self).__init__(*args, **kwargs)
        #self.add_guaranteed_wordlist([line.rstrip('\n') \
        #        for line in open('idioms_4word.txt', 'r')])

    def _seg_sentence(self, *args, **kwargs):
        seg_result = self.seg(*args, **kwargs)
        sentence = '\n'.join(['\t'.join(token) for token in seg_result.raw])
        sentence_tag = '<s>\n{}\n</s>'.format(sentence)

        return sentence_tag

    def _generate_meta_tag(self, meta, file):
        meta['id'] = file
        meta_tag = '<text {}>'.format(' '.join(['{}="{}"'.\
                format(k, v) for k, v in meta.items()]))

        return meta_tag

    def print_vrt(self, file, content, meta):
        content = [p.splitlines() for p in content.split('\n\n')]

        buffer = io.StringIO()
        buffer.write(self._generate_meta_tag(meta, file))

        buffer.write('\n')
        for paragraph in content:
            if paragraph:
                buffer.write('<p>\n')
                for sentence in paragraph:
                    if sentence.strip():
                        buffer.write(self._seg_sentence(sentence, True))
                        buffer.write('\n')
                buffer.write('</p>\n')
        buffer.write('</text>')

        return buffer.getvalue()

    def summary(self, content, file=None):
        tokens = self.seg(re.sub('\n', ' ', content), False).raw
        types = set(tokens)
        counter = Counter(tokens)
        wfqtable = sorted(counter.items(), key=itemgetter(1), reverse=True)
        summary = {
            'token': len(tokens),
            'type': len(types),
            'wortfreq': wfqtable
        }
        if file:
            with open(file, 'w') as f:
                f.write(summary)
        else
            return summary
