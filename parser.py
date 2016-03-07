#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
from pprint import pprint

import requests
from jseg.jieba import Jieba

class PttScraper(requests.Session):

    """ Docstring of PttScraper

        Usage:

        url = 'https://www.ptt.cc/bbs/Gossiping/M.1457154873.A.188.html'
        ptt = PttScraper()
        ptt.fetch_html(url)
        ptt.extract_meta()
        ptt.extract_article()

    """

    _re_meta = re.compile(r'meta-tag">(.*?)</span>(?:.|\s)+?meta-value">(.*?)</span>')
    _re_article_raw = re.compile(r'<div id="main-content".*</div>(.*?)※ 發信站: 批踢踢實業坊', re.S)

    def __init__(self):
        super().__init__()
        self.cookies.set(name='over18', value='1')
        self.html = None

    def fetch_html(self, url):
        res = self.get(url)
        self.html = res.text

    def extract_meta(self):
        matches = self._re_meta.findall(self.html)
        return matches

    def extract_article(self):
        matches_raw = self._re_article_raw.search(self.html)
        matches = re.sub(r'</?span.*?>', '', matches_raw.group(1))
        return matches


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

