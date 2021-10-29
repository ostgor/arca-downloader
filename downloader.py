import requests
import bs4
import re
import time
import os.path
import threading
import traceback


NAME_RE = re.compile(r'/b/(\w+)/(\d+)')


class Downloader(threading.Thread):
    def __init__(self, gui, selected_ch, selected_cat, startpg: int, endpg: int, filter_mode: int, best: bool):
        threading.Thread.__init__(self)
        self.gui = gui
        self.s = requests.Session()
        self.selected_ch = selected_ch
        self.selected_cat = selected_cat
        self.startpg = startpg
        self.endpg = endpg
        self.filter_mode = filter_mode
        self.best = best
        self.articles = set(selected_ch['articles'])

    def run(self):
        try:
            self.temp_download()
        except Exception:
            self.gui.log('failed download:', essential=True)
            self.gui.log(traceback.format_exc(), essential=True)
        self.gui.root.event_generate('<<DownloadComplete>>')

    def temp_download(self):
        s = time.perf_counter()
        # set filter
        if self.filter_mode == 0:
            _filter = {}
        elif self.filter_mode == 1:
            _filter = self.gui.data['default']
        else:
            _filter = self.selected_ch

        ch_url, cat_url = self.selected_ch['channel_url'], self.selected_cat[0]

        # configure download location
        dl_path = build_dl_path(
            self.gui.data['dl_mode'],
            self.gui.data['dl_location'],
            self.selected_ch['channel_name'],
            self.selected_cat[1]
        )
        if not os.path.exists(dl_path):
            os.makedirs(dl_path)

        # log
        self.gui.log(
            '\n--------------new download--------------\n',
            f'channel: {self.selected_ch["channel_name"]}\ncategory: {self.selected_cat[1]}',
            f'page: {self.startpg}-{self.endpg}',
            '\n----------begin page download-----------\n',
            sep='\n', essential=True
        )

        # page download
        article_list = []
        for page in range(self.startpg, self.endpg + 1):
            # check if stop
            if self.gui.destroy:
                raise Exception('thread stopped')
            self.gui.log(f'requesting page {page}')
            url = build_url(ch_url, cat_url, page, best=self.best)
            self.page_scrape(url, _filter, article_list)

        self.gui.log('\n---------begin article download---------', essential=True)
        # article download
        for article_url in article_list:
            if self.gui.destroy:
                raise Exception('thread stopped')
            self.get_article('https://arca.live' + article_url, _filter, dl_path)
        e = time.perf_counter()
        self.gui.log(f'\ndownload complete in {e - s}s\n', essential=True)

    def page_scrape(self, url, settings: dict, output_list):
        r = self.s.get(url, cookies={'allow_sensitive_media': 'true'})
        soup = bs4.BeautifulSoup(r.text, 'html.parser')
        for tag in soup.select('[class=vrow]'):
            title = tag.select_one('.title').getText()
            self.gui.log(f'\nanalyzing: {title}')

            # duplicate article check
            article_url = tag['href']
            match = NAME_RE.search(article_url)
            if not match:
                self.gui.log('WARNING: failed to match url regex on url: ' + article_url, essential=True)
            elif match.group(2) in self.articles:
                self.gui.log('skip: previously downloaded')
                continue

            if not tag.select_one('.vrow-preview'):
                self.gui.log('skip: no image')
                continue
            if settings.get('combined'):
                combined = int(tag.select_one('.col-rate').getText())
                if combined < settings['combined_num']:
                    self.gui.log(f'skip: combined votes {combined} < {settings["combined_num"]}')
                    continue
            if settings.get('title'):
                match = False
                for word in settings['title_bl']:
                    if word in title:
                        match = True
                        break
                if match:
                    self.gui.log(f'skip: {word} in title: {title}')
                    continue
            if settings.get('category'):
                category = tag.select_one('.badge').get_text()
                if category in settings['category_bl']:
                    self.gui.log(f'skip: category {category}')
                    continue
            if settings.get('uploader'):
                # not yet implemented
                self.gui.log(str(tag.select_one('.user-info')))
            # if True:
            #     print(tag.select_one('time')['datetime'])
            self.gui.log('appending to queue')
            output_list.append(article_url)

    def get_article(self, article_url, settings: dict, dl_path):
        self.gui.log('getting article:', article_url)
        r = self.s.get(article_url)
        soup = bs4.BeautifulSoup(r.text, 'html.parser')
        head = soup.select_one('head title').get_text()
        self.gui.log(f'\narticle: {head}')
        if '⚠️ 제한된 콘텐츠' == head:
            raise Exception('version update needed: ⚠️ 제한된 콘텐츠')
        if settings.get('content'):
            content = soup.select_one('.article-content').get_text()
            for string in settings['content_bl']:
                if string in content:
                    self.gui.log(f'skip: {string} in contents')
                    return
        if settings.get('upvote'):
            upvote = int(soup.select_one('.article-info .body:nth-child(2)').get_text())
            if upvote < settings['upvote_num']:
                self.gui.log(f'skip: upvote {upvote} < {settings["upvote_num"]}')
                return
        if settings.get('downvote'):
            downvote = int(soup.select_one('.article-info .body:nth-child(5)').get_text())
            if downvote > settings['downvote_num']:
                self.gui.log(f'skip: downvote {downvote} > {settings["downvote_num"]}')
                return
        src_list = []
        for img in soup.select('.article-content img'):
            img_url = img.get('src')
            src_list.append(img_url if img_url.startswith('https:') else 'https:' + img_url)
        for video in soup.select('.article-content video'):
            vid_url = video.get('src')
            src_list.append(vid_url if vid_url.startswith('https:') else 'https:' + vid_url)
        match = NAME_RE.search(article_url)
        # Does not add article number if not matched
        prefix = None
        if match:
            prefix = f'{match.group(1)}-{match.group(2)}-'
            self.gui.article_list.append(match.group(2))
        for i, src in enumerate(src_list):
            self.gui.log(f'downloading: {src}')
            r = self.s.get(src)
            ext = os.path.splitext(src)[1]
            filename = prefix + str(i) + ext if prefix else os.path.basename(src)
            with open(dl_path + filename, 'wb') as f:
                f.write(r.content)


def build_dl_path(mode, user_path, ch_name, cat_name):
    dirpath = './' if user_path is None else user_path + '/'
    if mode == 1:
        return dirpath
    elif mode == 2:
        return dirpath + ch_name + '/'
    else:
        return dirpath + ch_name + '/' + cat_name + '/'


C_RE = re.compile(r'\?(category=.+)')


def build_url(ch_url, category_url, page, best=False):
    match = C_RE.search(category_url)
    if match:
        category_url = '&' + match.group(1)
    else:
        category_url = ''
    return ch_url + f'?p={page}' + category_url + ('&mode=best' if best else '')


# Page downloader does not add article to downloaded articles
class PageDownloader(threading.Thread):
    def __init__(self, gui, url):
        threading.Thread.__init__(self)
        self.gui = gui
        self.s = requests.Session()
        self.url = url

    def run(self):
        try:
            self.page_download()
        except Exception:
            self.gui.log('failed download:', essential=True)
            self.gui.log(traceback.format_exc(), essential=True)

    def page_download(self):
        # dl path
        dl_path = './arca_downloaded/'
        if not os.path.exists(dl_path):
            os.makedirs(dl_path)

        self.gui.log('\ngetting article:', self.url, essential=True)
        r = self.s.get(self.url)
        soup = bs4.BeautifulSoup(r.text, 'html.parser')
        head = soup.select_one('head title').get_text()
        self.gui.log(f'article: {head}\n')
        if '⚠️ 제한된 콘텐츠' == head:
            raise Exception('version update needed: ⚠️ 제한된 콘텐츠')
        src_list = []
        for img in soup.select('.article-content img'):
            img_url = img.get('src')
            src_list.append(img_url if img_url.startswith('https:') else 'https:' + img_url)
        for video in soup.select('.article-content video'):
            vid_url = video.get('src')
            src_list.append(vid_url if vid_url.startswith('https:') else 'https:' + vid_url)
        # filename prefix
        match = NAME_RE.search(self.url)
        prefix = f'{match.group(1)}-{match.group(2)}-' if match else None
        for i, src in enumerate(src_list):
            self.gui.log(f'downloading: {src}')
            r = self.s.get(src)
            ext = os.path.splitext(src)[1]
            filename = prefix + str(i) + ext if prefix else os.path.basename(src)
            with open(dl_path + filename, 'wb') as f:
                f.write(r.content)
        self.gui.log('\ndownload complete', essential=True)


def ch_register(ch_url, ch_data):
    r = requests.get(ch_url)
    r.raise_for_status()
    soup = bs4.BeautifulSoup(r.text, 'html.parser')
    ch_data['channel_name'] = soup.select_one('.board-title > a:last-of-type').get_text()
    if not ch_data['channel_name']:
        raise Exception('no channel name found')
    for tag in soup.select('.board-category a'):
        ch_data['channel_category'].append([tag['href'], tag.get_text()])
    ch_data['channel_url'] = ch_url
    return ch_data
