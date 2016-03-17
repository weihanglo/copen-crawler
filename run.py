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

logger = logging.getLogger()
logger.addHandler(fh)

def unique(seq):
    seen = set()
    seen_add = seen.add
    return [x for x in seq if not (x in seen or seen_add(x))]

def main():
    conn = scraper.PttConnector()
    conn.crawl_links(8000, 99999999, 20, 3.5)
    with open(os.path.join(CORPUS_PATH, PREFIX + '.links'), 'a') as f:
        for link in conn.links:
            print(link, file=f)

    parser = scraper.PttScraper()
    coder = scraper.Coder()

    with open(os.path.join(CUR_PATH, 'idioms_4word.txt')) as f:
        idioms = f.read().splitlines()
    coder.add_guaranteed_wordlist(idioms)
    sent_sep = [True, '。」?', '？」?', '！」?']

    count = len(glob.glob(os.path.join(CORPUS_PATH, PREFIX + '*.vrt')))

    for url in conn.links:
        if not count % 20:
            time.sleep(6)
        count += 1
        file = os.path.join(CORPUS_PATH, PREFIX + '{:06d}.vrt'.format(count))

        try:
            parser.fetch_html(url)
            parser.extract_meta()
            parser.extract_content()
            parser.extract_news_meta()
            parser.content = parser.clean(parser.content, True, True, True)
        except:
            logger.error('Unexpected error while parsing: {}'.\
                format(sys.exc_info()))

        found = False
        for idiom in idioms:
            if parser.content.find(idiom) != -1:
                found = True
                break

        if found:
            try:
                coder.print_vrt(parser.content, parser.meta, sent_sep, file)
                coder.summary(parser.content, file.replace('.vrt', '.json'))
            except:
                logger.error('Unexpected error while coding: {}'.\
                    format(sys.exc_info()))
        else:
            count -= 1

if __name__ == '__main__':
    logger.debug('Started at {}'.format(time.strftime('%Y-%m-%d %X')))
    main()
    logger.debug('Finished at {}'.format(time.strftime('%Y-%m-%d %X')))
