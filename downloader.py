import requests
import bs4
import re
import time
import os.path


def log(*args: str):
    with open('download_log.txt', 'a', encoding='utf-8') as f:
        f.write(' '.join(args) + '\n')


def temp_download(ch_data, startpage, endpage, df_data):
    s = time.perf_counter()
    # set filter
    if ch_data['df_f']:
        _filter = df_data
    elif ch_data['ch_f']:
        _filter = ch_data
    else:
        _filter = {}
    cat_index = ch_data['prev_category']
    ch_url, cat_url = ch_data['channel_url'], ch_data['channel_category'][cat_index][0]
    article_list = []
    log('-------------------new download----------------------\n')
    log(f'channel: {ch_data["channel_name"]}\ncategory: {ch_data["channel_category"][cat_index][1]}')
    log(f'page: {startpage}-{endpage}')
    log('\n----------------begin page download------------------')
    # page download
    for page in range(startpage, endpage+1):
        print(f'Analyzing page...{page}', end='\r')
        url = build_url(ch_url, cat_url, page)
        page_scrape(url, _filter, article_list)
    print('Analyzing page...complete')
    log('\n----------------begin article download---------------')
    # article download
    for article_url in article_list:
        get_article('https://arca.live' + article_url, _filter)
    e = time.perf_counter()
    log(f'\nfinished in {e-s}\n')
    print(f'\nDownload complete in {e-s}s')


c_re = re.compile(r'\?(category=.+)')


def build_url(ch_url, category_url, page, best=False):
    match = c_re.search(category_url)
    if match:
        category_url = '&' + match.group(1)
    else:
        category_url = ''
    return ch_url + f'?p={page}' + category_url + ('&mode=best' if best else '')


def page_scrape(url, settings: dict, output_list):
    r = requests.get(url, cookies={'allow_sensitive_media': 'true'})
    soup = bs4.BeautifulSoup(r.text, 'html.parser')
    for tag in soup.select('[class=vrow]'):
        title = tag.select_one('.title').getText()
        log(f'\nanalyzing: {title}')
        if not tag.select_one('.vrow-preview'):
            log('skip: no image')
            continue
        if settings.get('combined'):
            combined = int(tag.select_one('.col-rate').getText())
            if combined < settings['combined_num']:
                log(f'skip: combined votes {combined} < {settings["combined_num"]}')
                continue
        if settings.get('title'):
            match = False
            for word in settings['title_bl'].values():
                if word in title:
                    match = True
                    break
            if match:
                log(f'skip: {word} in title: {title}')
                continue
        if settings.get('category'):
            category = tag.select_one('.badge').get_text()
            if category in map(lambda x: x[1], settings['category_bl'].values()):
                log(f'skip: category {category}')
                continue
        if settings.get('uploader'):
            # not yet implemented
            log(str(tag.select_one('.user-info')))
        # if True:
        #     print(tag.select_one('time')['datetime'])
        log('appending to queue')
        output_list.append(tag['href'])


def get_article(article_url, settings: dict):
    print('Getting article...' + article_url, end='\r')
    r = requests.get(article_url)
    soup = bs4.BeautifulSoup(r.text, 'html.parser')
    head = soup.select_one('head title').get_text()
    log(f'\narticle: {head}')
    if '⚠️ 제한된 콘텐츠' == head:
        raise Exception('version update needed: ⚠️ 제한된 콘텐츠')
    if settings.get('content'):
        content = soup.select_one('.article-content').get_text()
        for string in settings['content_bl'].values():
            if string in content:
                log(f'skip: {string} in contents')
                return
    if settings.get('upvote'):
        upvote = int(soup.select_one('.article-info .body:nth-child(2)').get_text())
        if upvote < settings['upvote_num']:
            log(f'skip: upvote {upvote} < {settings["upvote_num"]}')
            return
    if settings.get('downvote'):
        downvote = int(soup.select_one('.article-info .body:nth-child(5)').get_text())
        if downvote > settings['downvote_num']:
            log(f'skip: downvote {downvote} > {settings["downvote_num"]}')
            return
    src_list = []
    for img in soup.select('.article-content img'):
        src_list.append(img.get('src'))
    for i, src in enumerate(src_list):
        print('Downloading...' + src, end='\r')
        log(f'downloading: {src}')
        r = requests.get('https:' + src)
        with open('./dl/' + os.path.basename(src), 'wb') as f:
            f.write(r.content)
    print()


def ch_register(ch_url, ch_data):
    r = requests.get(ch_url)
    r.raise_for_status()
    soup = bs4.BeautifulSoup(r.text, 'html.parser')
    ch_data['channel_name'] = soup.select_one('.board-title > a:nth-child(2)').get_text()
    if not ch_data['channel_name']:
        raise Exception('no channel name found')
    for tag in soup.select('.board-category a'):
        ch_data['channel_category'].append([tag['href'], tag.get_text()])
    ch_data['channel_url'] = ch_url
    return ch_data
