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
from datetime import datetime
from operator import itemgetter

import requests
from jseg.jieba import Jieba
from pyquery import PyQuery

# logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class PttScraper(object):
    """A scraper for ptt news

    Examples
    --------
    # unformatted article::
        url = 'https://www.ptt.cc/bbs/Gossiping/M.1457406335.A.0BA.html'
        url = 'https://www.ptt.cc/bbs/Gossiping/M.1447465330.A.B9F.html'
        url = 'https://www.ptt.cc/bbs/Gossiping/M.1446024184.A.346.html'
        url = 'https://www.ptt.cc/bbs/Gossiping/M.1452096019.A.D0A.html'

    # well-formatted ariticle::
        url = 'https://www.ptt.cc/bbs/Gossiping/M.1452164857.A.979.html'
        url = 'http://www.ptt.cc/bbs/Gossiping/M.1452169410.A.DFD.html'

        p = PttScraper()
        p.fetch_html(url)
        p.extract_meta()
        p.extract_content()
        p.extract_news_meta()
        p.content = p.clean(p.content, tag=True, url=True, html_char=True)

    """

    _re_meta = re.compile(u"""
        meta-tag">(.*?)</span>
        (?:.|\s)+?meta-value">
        (.*?)</span>
        """, re.VERBOSE | re.UNICODE)
    _re_content = re.compile(u"""
        <div\sid="main-content".*meta-value">
        .*?</div>
        (.*?)
        (?:\n-+?\n.*?)?
        -+?\n.*?<span[^>]*>※\s發信站
        """, re.DOTALL | re.VERBOSE | re.UNICODE)
    _re_news_meta_in_content = re.compile(u"""
        \d\.媒體來源:                   (?P<media>.*)
        \d\.完整新聞標題:               (?P<news_title>.*)
        \d\.完整新聞內文:               (?P<news_content>.*)
        \d\.完整新聞連結\s\(或短網址\): (?P<news_url>.*?)
        (\d\.備註:                      (?P<note>.*))?$
        """, re.DOTALL | re.VERBOSE | re.UNICODE)

    def __init__(self):
        self.session = requests.Session()
        self.session.cookies.set(name='over18', value='1')
        self.url = None
        self.html = None
        self.meta = {}
        self.content = None

    def fetch_html(self, url):
        """
        url : URL to fetch
        """
        try:
            res = self.session.get(url)
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
                '看板': 'board',
                '標題': 'ptt_title',
                '時間': 'date',
            }[match[0]]
            self.meta[key] = match[1]

        author = self.meta.get('author')
        date = self.meta.get('date')
        self.meta.update({
            'author': re.sub(u'\s\(.*$', '', author if author else '', \
                flags=re.UNICODE),
            'date': datetime.strptime(date, '%a %b %d %X %Y').\
                strftime('%Y-%m-%d') if date else '',
            'article_type': 'news',
            'source': 'PTT',
            'gender': '',
            'age': '',
            'ptt_url': self.url,
        })
        return self.meta

    def extract_content(self):
        match = self._re_content.search(self.html)
        if match:
            self.content = match.group(1)
        else:
            self.content = ''
            logger.error('ExtractContentError at {}'.format(self.url))
        return self.content

    def extract_news_meta(self):
        matches = self._re_news_meta_in_content.search(self.content)
        if matches:
            for k, v in matches.groupdict().items():
                if v:
                    if k == 'news_url':
                        url = re.search(u'(?<=href=").*?(?=")', v, flags=re.U)
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
            u'&amp;': '&',
            u'&lt;': '<',
            u'&gt;': '>',
            u'&quot;': '"',
            u'&#39;': '\'',
        }

        if tag:
            content = re.sub(u'</?[^>]*>', '', content, flags=re.U)
        if url:
            content = re.sub(u'https?://\S+', '', content, flags=re.U)
        if html_char:
            for k, v in html_chars.items():
                content = content.replace(k, v)

        return content.strip()

class PttMongo(PttScraper):
    def __init__(self):
        super(PttMongo, self).__init__()
        self.meta = {
            'media': '',
            'news_title': '',
            'news_url': '',
            'note': '',
        }

    def extract_content(self, doc):
        self.content = doc.get('content', '')
        return self.content

    def extract_meta(self, doc):
        self.meta.update({
            'author': doc.get('author', ''),
            'date': doc['post_time'].strftime('%Y-%m-%d'),
            'ptt_url': doc.get('URL', ''),
            'ptt_title': doc.get('title', ''),
            'article_type': 'news',
            'board': 'Gossiping',
            'source': 'PTT',
            'gender': '',
            'age': '',
        })
        return self.meta

class PttConnector(requests.Session):
    """
    Usage::
        conn = PttConnector()
        conn.crawl_links(10000, 50000, 200, 3)

    """
    _baseurl = 'http://www.ptt.cc'
    _css_selector = 'div.r-ent > .title > a[href]'
    _url_fmt = '/bbs/Gossiping/index{}.html'

    def __init__(self):
        super(PttConnector, self).__init__()
        self.cookies.set(name='over18', value='1')
        self.links = []

    def _get_links(self, url):
        nlinks = 0
        try:
            res = self.get(url)
            dom = PyQuery(res.text)
            a_tags = dom(self._css_selector)
            links = [self._baseurl + a.attrib['href'] \
                for a in a_tags if re.match(u'^\[新聞]', a.text, re.U)]
            self.links.extend(links)
            nlinks = len(links)
        except:
            logger.error('GetLinksError at {} : {}'.\
                format(url, sys.exc_info()))
        return nlinks

    def crawl_links(self, index, maxlinks, interval, sleep_sec=2):
        _cum_nlinks = 0
        while index > 0:
            url = self._baseurl + self._url_fmt.format(index)
            try:
                nlinks = self._get_links(url)
                _cum_nlinks += nlinks
            except:
                logger.error('CrawlError at {} : {}'.\
                    format(url, sys.exc_info()))
            index -= 1

            if _cum_nlinks >= interval:
                logger.debug('Crawled {} links'.format(_cum_nlinks))
                _cum_nlinks = 0
                time.sleep(sleep_sec)

            if len(self.links) >= maxlinks or not index > 0:
                logger.debug('Totally crawled {} links'.\
                    format(len(self.links)))
                break

class Coder:
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
    def __init__(self, load_ptt_dict=False):
        self.jieba = Jieba(load_ptt_dict)

    @staticmethod
    def multisplit(string, delims, regex, keep, maxsplit=0, flags=0):
        """Multisplit version of re.split.
        A static method that providing spliting string with multiple delimiters
        and other features.

        Parameters
        ----------
        string : str
            String to split.
        delims : list of str
            Different delimiters. All characters or strings will be treated as
            escaped characters. 
        regex : bool
            ``True`` if you need to write your own regex.
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

            >>> Coder.multisplit(string, ['?', '!'], regex=False, keep=1)
            ['?', 'How?', '?', ' Good. "Wow!', ' Cool!', '"']

        Delimiters contained regex::

            >>> Coder.multisplit(string, ['\?+', '\!"?'], regex=True, keep=1)
            ['?', 'How??', ' Good. "Wow!', ' Cool!"', '']

        Delimiters keeped at level 2 and containing regex::

            >>> Coder.multisplit(string, ['\?+', '\!"?'], regex=True, keep=2)
            ['', '?How', '?? Good. "Wow', '! Cool', '!"']
        """

        pattern = u'|'.join(delims if regex else [re.escape(s) for s in delims])

        if keep:
            pattern = u'({})'.format(pattern)

        splitted = re.split(pattern, string, maxsplit, flags)

        if keep == 1:
            for i, d in enumerate(splitted):
                if re.match(u'{}\Z'.format(pattern), d, flags):
                    splitted[i - 1] = splitted[i - 1] + splitted.pop(i)
        elif keep == 2:
            for i, d in enumerate(splitted):
                if re.match(u'{}\Z'.format(pattern), d, flags):
                    splitted[i] = splitted[i] + splitted.pop(i + 1)

        return splitted

    def _generate_metatag(self, meta, file=None):
        if file:
            meta['id'] = os.path.basename(file)

        meta_tag = u'<text {}>'.format(u' '.join([u'{}="{}"'.\
            format(k, v) for k, v in meta.items()]))

        return meta_tag

    def _seg_sentence(self, sentence):
        seg_result = self.jieba.seg(re.sub(u'\n+', u' ', sentence, flags=re.U))
        sentence = u'\n'.join([u'\t'.join(token) for token in seg_result.raw])
        sentence_tag = u'<s>\n{}\n</s>'.format(sentence)

        return sentence_tag

    def _split_sentence(self, content, sent_sep=None):
        if sent_sep:
            content = [self.multisplit(p, sent_sep, regex=True, keep=1, \
                flags=re.U) for p in re.split(u'\n\n+', content, flags=re.U)]
        else:
            content = [p.splitlines() for p \
                in re.split(u'\n\n+', content, flags=re.U)]
        return content

    def print_vrt(self, content, meta, sent_sep=None, file=None):

        buffer = io.StringIO()
        buffer.write(self._generate_metatag(meta, file))
        buffer.write(u'\n')

        for paragraph in self._split_sentence(content, sent_sep):
            if paragraph:
                buffer.write(u'<p>\n')
                for sentence in paragraph:
                    if sentence.strip():
                        buffer.write(self._seg_sentence(sentence))
                        buffer.write(u'\n')
                buffer.write(u'</p>\n')
        buffer.write(u'</text>')

        if file:
            with open(file, 'w') as f:
                f.write(buffer.getvalue().encode('utf8'))
                logger.info('Created vrt document at {}'.\
                    format(os.path.basename(file)))
        else:
            return buffer.getvalue()

    def summary(self, content, file=None):
        if content:
            tokens = self.jieba.seg(re.sub\
                (u'\n+', ' ', content, flags=re.U)).raw
            tokens = [token[0] for token in tokens]
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
                    logger.info('Created json summary at "{}"'.\
                        format(os.path.basename(file)))
            else:
                return summary
