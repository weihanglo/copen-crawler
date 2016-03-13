#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import io
import logging
import os
import re
import sys
import time
import json
from collections import Counter
from operator import itemgetter

import requests
from jseg.jieba import Jieba
from pyquery import PyQuery

# logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class PttScraper(requests.Session):
    """A scraper for ptt news

    Examples
    --------
    # unformatted article::
        url = 'https://www.ptt.cc/bbs/Gossiping/M.1457406335.A.0BA.html'

    # well-formatted ariticle::
        url  = 'https://www.ptt.cc/bbs/Gossiping/M.1452164857.A.979.html'

        url = 'http://www.ptt.cc/bbs/Gossiping/M.1452169410.A.DFD.html'

        p = PttScraper()
        p.fetch_html(url)
        p.extract_meta()
        p.extract_content()
        p.extract_news_meta()
        p.content = p.clean(p.content, tag=True, url=True, html_char=True)

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
        (?:\n--\n.*?)?
        \n--\n<span[^>]*>※\s發信站
        """, re.DOTALL | re.VERBOSE)
    _re_news_meta_in_content = re.compile(r"""
        \d\.媒體來源:                   (?P<media>.*)
        \d\.完整新聞標題:               (?P<news_title>.*)
        \d\.完整新聞內文:               (?P<news_content>.*)
        \d\.完整新聞連結\s\(或短網址\): (?P<news_url>.*?)
        (\d\.備註:                      (?P<note>.*))?$
        """, re.DOTALL | re.VERBOSE)

    def __init__(self):
        super().__init__()
        self.cookies.set(name='over18', value='1')
        self.url = None
        self.html = None
        self.meta = {}
        self.content = None

    def fetch_html(self, url):
        """
        url : URL to fetch
        """
        try:
            res = self.get(url)
            self.html = res.text
            self.url = url
        except:
            logger.error('FetchError at {} : {}'.\
                format(url, sys.exc_info()))

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
        date = self.meta.get('date')
        self.meta.update({
            'author': re.sub(r'\s\(.*$', '', author if author else ''),
            'date': time.strftime('%Y-%m-%d', \
                time.strptime(date, '%a %b %d %X %Y')),
            'article_type': 'news',
            'source': 'PTT',
            'gender': '',
            'age': '',
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
            for k, v in matches.groupdict().items():
                if v:
                    if k == 'news_url':
                        url = re.search(r'(?<=href=").*?(?=")', v)
                        self.meta[k] = url.group() if url else ''
                    elif k == 'news_content':
                        self.content = v if v else self.content
                    else:
                        self.meta[k] = self.clean(v.strip(), True, True, True)
                else:
                    self.meta[k] = ''
        else:
            self.meta.update({
                'media': '',
                'news_title': '',
                'news_url': '',
                'note': '',
            })

        return self.meta

    @staticmethod
    def clean(content, tag=False, url=False, html_char=False):
        """
        Parameters
        ----------
        tag : bool
            To remove html tags.
        url : bool
            To remove urls.
        html_char : bool
            To replace html escape characters with unicode characters.
        """
        html_chars = {
            '&amp;': '&',
            '&lt;': '<',
            '&gt;': '>',
            '&quot;': '"',
            '&#39;': '\'',
        }

        if tag:
            content = re.sub(r'</?[^>]*>', '', content)
        if url:
            content = re.sub(r'https?://\S+', '', content)
        if html_char:
            for k, v in html_chars.items():
                content = content.replace(k, v)

        return content.strip()

class PttConnector(requests.Session):
    """
    Usage::
        conn = PttConnector()
        conn.crawl_links(10000, 50000, 200)

    """
    _baseurl = 'http://www.ptt.cc'
    _css_selector = 'div.r-ent > .title > a[href]'
    _url_fmt = '/bbs/Gossiping/index{}.html'

    def __init__(self):
        super().__init__()
        self.cookies.set(name='over18', value='1')
        self.links = []

    def _get_links(self, url):
        try:
            res = self.get(url)
            dom = PyQuery(res.text)
            a_tags = dom(self._css_selector)
            self.links.extend([self._baseurl + a.attrib['href'] \
                for a in a_tags if re.match(r'^\[新聞]', a.text)])
        except:
            logger.error('GetLinksError at {} : {}'.\
                format(url, sys.exc_info()))

    def crawl_links(self, index, maxlinks, interval):
        a = index
        while index != -1:
            url = self._baseurl + self._url_fmt.format(a)
            try:
                self._get_links(url)
            except:
                logger.error('CrawlError at {} : {}'.\
                    format(url, sys.exc_info()))
            a -= 1
            if not len(self.links) % interval:
                time.sleep(2)
            if len(self.links) >= maxlinks:
                logger.debug('Crawling {} links'.format(len(self.links)))
                break

class Coder(Jieba):
    """
    Usage::
        content = '''
        LOPEN 計劃是台大語言學研究所語言處理與人文計算實驗室 (簡稱 LOPE) 所推動
        的一項中文語言與知識資源開放的計劃！
        我們相信，資源的開放可以促進經驗研究的重製，研究的創新與社會的進步？

        本計劃沒有經費可以給妳，我們有的是理想與熱情。
        如果妳是學生，歡迎來找我們討論專題計劃；
        如果妳是研究人員，歡迎洽談各種合作機會；
        如果妳是社會進步推動者，歡迎加入蘿蔔松來協助計劃。
        '''
        meta = dict(name='re', author='python3.5')
        sent_sep = ['。', '？', '！']

        coder = Coder()
        coder.print_vrt(content, meta, sent_sep, 'demo.vrt')
        coder.summary(content, 'demo.json')

    """
    def __init__(self, *args, **kwargs):
        super(Coder, self).__init__(*args, **kwargs)

    @staticmethod
    def multisplit(string, *delims, keep=0, maxsplit=0, flags=0):
        """Multisplit version of re.split. 
        A static method that providing spliting string with multiple delimiters
        and other features.

        Parameters
        ----------
        string : str
            String to split.
        *delims : str, list of str
            Different delimiters. All characters or strings will be treated as
            escaped characters. If you need to write your own regex, assign the
            first element to a ``True`` boolean value.
        keep : {0, 1, 2}
            Delimieter keeping level.
            `0` for splitting with removal.
            `1` for appending delimiters to previous element.
            `2` for concatenating delimiters into next element.
        maxsplit : int, default 0
            see :func:`re.split`
        flags : flags in regex , default 0
            see :mod:`re`

        Returns
        -------
        List of splitted strings.

        Examples
        --------
        Assumed having a string object like this::

            >>> string = '?How?? Good. "Wow! Cool!"'

        All delimiters escaped and keeped at level 1::

            >>> Coder.multisplit(string, '?', '!', keep=1)
            ['?', 'How?', '?', ' Good. "Wow!', ' Cool!', '"']

        Delimiters contained regex::

            >>> Coder.multisplit(string, True, '\?+', '\!"?', keep=1)
            ['?', 'How??', ' Good. "Wow!', ' Cool!"', '']

        Delimiters keeped at level 2 and containing regex::

            >>> Coder.multisplit(string, True, '\?+', '\!"?', keep=2)
            ['', '?How', '?? Good. "Wow', '! Cool', '!"']
        """

        if delims[0] is True:
            pattern = '|'.join(delims[1:])
        else:
            pattern = '|'.join([re.escape(s) for s in delims])

        if keep:
            pattern = '({})'.format(pattern)

        splitted = re.split(pattern, string, maxsplit, flags)

        if keep == 1:
            for i, d in enumerate(splitted):
                if d in delims or re.fullmatch(pattern, d):
                    splitted[i - 1] = splitted[i - 1] + splitted.pop(i)
        elif keep == 2:
            for i, d in enumerate(splitted):
                if d in delims or re.fullmatch(pattern, d):
                    splitted[i] = splitted[i] + splitted.pop(i + 1)

        return splitted

    def _generate_metatag(self, meta, file=None):
        if file:
            meta['id'] = os.path.basename(file)
        meta_tag = '<text {}>'.format(' '.join(['{}="{}"'.\
                format(k, v) for k, v in meta.items()]))

        return meta_tag

    def _seg_sentence(self, sentence, pos):
        seg_result = self.seg(re.sub('\n+', ' ', sentence), pos)
        sentence = '\n'.join(['\t'.join(token) for token in seg_result.raw])
        sentence_tag = '<s>\n{}\n</s>'.format(sentence)

        return sentence_tag

    def _split_sentence(self, content, sent_sep=None):
        if sent_sep:
            content = [self.multisplit(p, *sent_sep, keep=1) \
                    for p in re.split(r'\n\n+', content)]
        else:
            content = [p.splitlines() for p in re.split(r'\n\n+', content)]
        return content

    def print_vrt(self, content, meta, sent_sep=None, file=None):

        buffer = io.StringIO()
        buffer.write(self._generate_metatag(meta, file))
        buffer.write('\n')

        for paragraph in self._split_sentence(content, sent_sep):
            if paragraph:
                buffer.write('<p>\n')
                for sentence in paragraph:
                    if sentence.strip():
                        buffer.write(self._seg_sentence(sentence, True))
                        buffer.write('\n')
                buffer.write('</p>\n')

        buffer.write('</text>')

        if file:
            with open(file, 'w') as f:
                f.write(buffer.getvalue())
                logger.debug('Created vrt document at {}'.\
                    format(time.strftime('%Y-%m-%d %X')))
        else:
            return buffer.getvalue()

    def summary(self, content, file=None):
        tokens = self.seg(re.sub('\n+', ' ', content), False).raw
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
                json.dump(summary, f)
                logger.debug('Created json summary at {}'.\
                    format(time.strftime('%Y-%m-%d %X')))
        else:
            return summary
