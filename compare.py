#!/usr/bin/env python
# -*- coding: utf-8 -*-
import json
import os
import re
from jseg.jieba import Jieba

OUTPUT_PATH = os.path.join(os.path.expanduser('~'), 'ckip', 'output')
files = (os.path.join(OUTPUT_PATH, f) for f in os.listdir(OUTPUT_PATH))

p = re.compile(u'(\S*?)\((.*?)\)', re.U)
j = Jieba()

CUR_PATH = os.path.dirname(os.path.abspath(__file__))
CMP_PATH = os.path.join(CUR_PATH, 'compare')
os.makedirs(CMP_PATH, 0755)

for f in files:
    print('Processing {}'.format(f))
    m_ckip = p.findall(open(f).read().decode('utf8'))
    m_jseg = j.seg(open(f.replace('output', 'input')).read().decode('utf16')).raw
    diff = set(m_jseg) - set(m_ckip)
    error = float(len(diff)) / len(m_jseg)
    if error >= 0.7:
        outname = os.path.join(CMP_PATH, os.path.basename(f))
        json.dump({'diff': list(diff), 'jseg': m_jseg}, open(outname, 'w'))
        print('Output file at {}'.format(outname))
