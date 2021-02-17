import requests
import bs4
import re
import time
import os.path
import threading
import traceback


class Downloader(threading.Thread):
    def __init__(self, gui, selected_ch, selected_cat, startpg: int, endpg: int, filter_mode: int):
        threading.Thread.__init__(self)
        self.gui = gui
        self.selected_ch = selected_ch
        self.selected_cat = selected_cat
        self.startpg = startpg
        self.endpg = endpg
        self.filter_mode = filter_mode

    def run(self):
        try:
            self.temp_download()
        except Exception:
            self.gui.log('failed download:')
            self.gui.log(traceback.format_exc())
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
            sep='\n'
        )

        # page download
        article_list = []
        for page in range(self.startpg, self.endpg + 1):
            self.gui.log(f'requesting page {page}')
            url = build_url(ch_url, cat_url, page)
            self.page_scrape(url, _filter, article_list)

        self.gui.log('\n---------begin article download---------')
        # article download
        for article_url in article_list:
            self.get_article('https://arca.live' + article_url, _filter, dl_path)
        e = time.perf_counter()
        self.gui.log(f'\ndownload complete in {e - s}s\n')

    def page_scrape(self, url, settings: dict, output_list):
        r = requests.get(url, cookies={'allow_sensitive_media': 'true'})
        soup = bs4.BeautifulSoup(r.text, 'html.parser')
        for tag in soup.select('[class=vrow]'):
            title = tag.select_one('.title').getText()
            self.gui.log(f'\nanalyzing: {title}')
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
            output_list.append(tag['href'])

    def get_article(self, article_url, settings: dict, dl_path):
        self.gui.log('getting article:', article_url)
        r = requests.get(article_url)
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
            src_list.append(img.get('src'))
        for i, src in enumerate(src_list):
            self.gui.log(f'downloading: {src}')
            r = requests.get('https:' + src)
            with open(dl_path + os.path.basename(src), 'wb') as f:
                f.write(r.content)


def build_dl_path(mode, user_path, ch_name, cat_name):
    dirpath = './' if user_path is None else user_path + '/'
    if mode == 1:
        return dirpath
    elif mode == 2:
        return dirpath + ch_name + '/'
    else:
        return dirpath + ch_name + '/' + cat_name + '/'


c_re = re.compile(r'\?(category=.+)')


# TODO: add download best mode
def build_url(ch_url, category_url, page, best=False):
    match = c_re.search(category_url)
    if match:
        category_url = '&' + match.group(1)
    else:
        category_url = ''
    return ch_url + f'?p={page}' + category_url + ('&mode=best' if best else '')


class PageDownloader(threading.Thread):
    def __init__(self, gui, url):
        threading.Thread.__init__(self)
        self.gui = gui
        self.url = url

    def run(self):
        try:
            self.page_download()
        except Exception:
            self.gui.log('failed download:')
            self.gui.log(traceback.format_exc())

    def page_download(self):
        # dl path
        dl_path = './arca_downloaded/'
        if not os.path.exists(dl_path):
            os.makedirs(dl_path)

        self.gui.log('\ngetting article:', self.url)
        r = requests.get(self.url)
        soup = bs4.BeautifulSoup(r.text, 'html.parser')
        head = soup.select_one('head title').get_text()
        self.gui.log(f'article: {head}\n')
        if '⚠️ 제한된 콘텐츠' == head:
            raise Exception('version update needed: ⚠️ 제한된 콘텐츠')
        src_list = []
        for img in soup.select('.article-content img'):
            src_list.append(img.get('src'))
        for i, src in enumerate(src_list):
            self.gui.log(f'downloading: {src}')
            r = requests.get('https:' + src)
            with open(dl_path + os.path.basename(src), 'wb') as f:
                f.write(r.content)
        self.gui.log('\ndownload complete')


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
