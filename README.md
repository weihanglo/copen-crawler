copen-crawler
=============
A crawler collects articles containing Chinese idioms.

TODO
----
- [ ] scraper: social media (Facebook, mobile01, ...)
- [x] multisplit of sentences
- [x] connector: PTT Gossiping
- [x] scraper: **PTTscraper** (for news in Gossiping board)
- [x] coder: a summrizing method
- [x] coder: a general formatter method for vrt format

### VRT format spec:
#### general meta
- id
- source
- article\_type
- date
- author
- gender
- age

#### sub type meta: news in ptt
- ptt\_url
- ptt\_board
- ptt\_title
- news\_url
- news\_title
- media
- note

#### Separator (in regex syntax)
- paragraph 
    - \n\n+
- sentence
    - ！」?
    - ？」?
    - 。」?

Dependency
----------
- [requests](http://docs.python-requests.org/en/master)
- [jseg3](https://github.com/amigcamel/Jseg/tree/jseg3)
- [pyquery](https://github.com/gawel/pyquery)

*Weihang Lo*
