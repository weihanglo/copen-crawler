#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import glob
import logging
import os
import sys
import time

import scraper

CUR_PATH = os.path.dirname(os.path.abspath(__file__))
PREFIX = 'PTT_News'

CORPUS_PATH = os.path.join(CUR_PATH, PREFIX)
os.makedirs(CORPUS_PATH, exist_ok=True)

fh = logging.FileHandler(os.path.join(CORPUS_PATH, PREFIX + '.log'))
fh.setLevel(logging.DEBUG)

def main():
    conn = scraper.PttConnector()
    conn.crawl_links(7803, 30, 10)
    parser = scraper.PttScraper()

    coder = scraper.Coder()
    with open(os.path.join(CUR_PATH, 'idioms_4word.txt')) as f:
        idioms = f.read().splitlines()
    coder.add_guaranteed_wordlist(idioms)
    sent_sep = [True, '。」?', '？」?', '！」?']

    count = len(glob.glob(os.path.join(CORPUS_PATH, PREFIX + '*.vrt')))

    for url in conn.links:
        count += 1
        file = os.path.join(CORPUS_PATH, PREFIX + '{:05d}.vrt'.format(count))

        parser.fetch_html(url)
        parser.extract_meta()
        parser.extract_content()
        parser.extract_news_meta()
        parser.content = parser.clean(parser.content, True, True, True)

        found = False
        for idiom in idioms:
            if parser.content.find(idiom) != -1:
                found = True
                break

        if found:
            coder.print_vrt(parser.content, parser.meta, sent_sep, file)
            coder.summary(parser.content, file.replace('.vrt', '.json'))
        else:
            count -= 1

if __name__ == '__main__':
    logger = logging.getLogger()
    logger.addHandler(fh)
    logger.debug('Started at {}'.format(time.strftime('%Y-%m-%d %X')))
    main()
    logger.debug('Finished at {}'.format(time.strftime('%Y-%m-%d %X')))
