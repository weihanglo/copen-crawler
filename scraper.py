#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re

import requests
from jseg.jieba import Jieba

class PttScraper(requests.Session):
    # TODO :: matches = re.sub(r'</?span.*?>', '', matches_raw.group(1))
    """ Docstring of PttScraper

    Usage:

        url = 'https://www.ptt.cc/bbs/Gossiping/M.1457406335.A.0BA.html'
        ---> unformatted article

        url = 'https://www.ptt.cc/bbs/Gossiping/M.1457404523.A.DAD.html'
        ---> formatted ariticle

        ptt = PttScraper()
        ptt.fetch_html(url)
        ptt.extract_meta()
        ptt.extract_content()
        ptt.extract_meta_in_content()

    """

    _re_meta = re.compile(r"""
        meta-tag">(.*?)</span>
        (?:.|\s)+?meta-value">
        (.*?)</span>
        """, re.VERBOSE)
    _re_article_raw = re.compile(r"""
        <div\sid="main-content".*meta-value">
        .*?</div>
        (.*?)
        ※\s發信站:\s批踢踢實業坊
        """, re.DOTALL | re.VERBOSE)
    _re_meta_in_content = re.compile(r"""
        (?:\d\.)?媒體來源:(?P<media>.*?)
        (?:\d\.)?完整新聞標題:(?P<news_title>.*?)
        (?:\d\.)?完整新聞內文:(?P<news_content>.*?)
        (?:\d\.)?完整新聞連結\s\(或短網址\):(?P<news_url>.*?)
        (?:\d\.)?備註:?(?P<note>.*?)
        """, re.DOTALL | re.VERBOSE)

    def __init__(self):
        super().__init__()
        self.cookies.set(name='over18', value='1')
        self.html = None
        self.content = None

    def fetch_html(self, url):
        res = self.get(url)
        self.html = res.text

    def extract_meta(self):
        matches = self._re_meta.findall(self.html)
        match_dict = {}
        for match in matches:
            key = {
                '作者': 'author',
                '看板': 'board',
                '標題': 'ptt_title',
                '時間': 'date',
            }[match[0]]
            match_dict[key] = match[1]
            author = match_dict.get('author')
        match_dict.update({
            'author': re.sub(r'\s\(.*$', '', author if author else '')})
        return match_dict

    def extract_content(self):
        matches = self._re_article_raw.search(self.html)
        self.content = matches.group(1)
        return self.content

    def extract_meta_in_content(self):
        matches = self._re_meta_in_content.search(self.content)
        return matches.groupdict()


class Coder(Jieba):
    """ Docstring of Coder

        None

    """

    def __init__(self, *args, **kwargs):
        super(Coder, self).__init__(*args, **kwargs)
        self.seg_result = None
        self.add_guaranteed_wordlist([line.rstrip('\n') \
                for line in open('idioms_4word.txt', 'r')])

    def seg_as_vrt(self, *args, **kwargs):
        self.seg_result = self.seg(*args, **kwargs)
        result = '\n'.join(['\t'.join(token) for token in self.seg_result.raw])
        sentence_tag = '<s>\n {}\n</s>'.format(result)
        return sentence_tag

    def generate_meta_tag(self, **kwargs):
        attributes = ['{}="{}"'.format(k, v) for k, v in kwargs.items()]
        meta_tag = '<text {}>'.format(' '.join(attributes))
        return meta_tag

    def types(self):
        return set(self.seg_result.nopos)

    def tokens(self):
        return self.seg_result.nopos

