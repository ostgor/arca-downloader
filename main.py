import json
import os
import sys
import bs4
import requests
import re
import downloader


def main():
    try:
        data = load_channels()
    except Exception as expt:
        print('Error: settings corrupted, consider deleting the settings file')
        print(expt)
        input('Press enter to exit')
        return

    # main loop
    print()
    while True:
        choices = display_main()
        action = get_next_action(choices)
        if action == 'break':
            return
        else:
            os.system('cls')
            action(data)


def get_next_action(choices: dict):
    def invalid(_):
        print('Invalid input')
        return
    # get user input
    userinput = input('Input: ')
    if userinput in choices:
        return choices[userinput]
    else:
        return invalid


# settings related
def load_channels():
    if os.path.exists('arca_downloader_settings.json'):
        try:
            with open('arca_downloader_settings.json', 'r') as f:
                data = json.load(f)
        except PermissionError:
            print('Permission denied: Close other applications that might be using the folder')
            input('Press enter to exit')
            sys.exit()

        verify_data(data)
        return data
    else:
        print('*** Could not read settings, default settings created ***')
        data = create_default()
        return data


def verify_data(data):
    def verify_settings(data, is_channel):
        if type(data) == dict:
            for key in default_setting():
                if key not in data:
                    raise Exception(f'no <{key}> in settings')
            for key in ('title', 'content', 'upvote', 'downvote', 'combined', 'uploader', 'fav', 'category'):
                if type(data[key]) != bool:
                    raise Exception('not a boolean')
            for key in ('combined_num', 'downvote_num', 'upvote_num', 'dl_mode', 'dl_count'):
                if type(data[key]) != int:
                    raise Exception('not an int')
            for key in ('channel_category',):
                if type(data[key]) != list:
                    raise Exception('not a list')
            for key in ('category_bl', 'prev', 'title_bl', 'content_bl', 'uploader_bl'):
                if type(data[key]) != dict:
                    raise Exception('not a dict')
        else:
            raise Exception('data not a dict')
        if is_channel:
            if (type(data['channel_name']) != str) or (type(data['channel_url']) != str):
                raise Exception('channel name or url corrupted')
            elif len(data['channel_category']) == 0:
                raise Exception('no channel category')
            elif 'category' not in data['prev'] or 'df_f' not in data['prev'] or 'ch_f' not in data['prev']:
                raise Exception('prev does not contain category/df_f/ch_f')
            return
        else:
            return

    verify_settings(data['default'], False)
    for channel in data['channels']:
        verify_settings(channel, True)


def create_default():
    data = {
        'default': default_setting(),
        'channels': []
    }
    write_channels(data)
    return data


def default_setting():
    df_setting = {
        'channel_name': None,
        'channel_url': None,
        'channel_category': [],
        'prev': {
            'category': 0,
            'df_f': False,
            'ch_f': False
        },
        'dl_count': 0,
        'fav': False,
        'dl_mode': 0,
        'category': False,
        'category_bl': {},
        'download_location': None,
        'title': False,
        'title_bl': {},
        'content': False,
        'content_bl': {},
        'upvote': False,
        'upvote_num': 0,
        'downvote': False,
        'downvote_num': 0,
        'combined': False,
        'combined_num': 0,
        'uploader': False,
        'uploader_bl': {}
    }
    return df_setting


def write_channels(data):
    while True:
        try:
            print('saving settings...')
            with open('arca_downloader_settings.json', 'w') as f:
                json.dump(data, f, indent=4)
            return
        except PermissionError:
            print('Permission denied: Close other applications that might be using the folder')
            if input('try again? y/n: ') == 'n':
                raise Exception('failed to save due to PermissionError')
        except Exception as expt:
            print('Failed to save:', expt)
            input('Press enter to quit')
            sys.exit()


def toggle(settings, attr: str):
    def inner(data):
        settings[attr] = not settings[attr]
        write_channels(data)
    return inner


def modify(settings, attr: str):
    def mod_loop(data):
        while True:
            print('Current count:', settings[attr])
            num = input('Input count: ')
            os.system('cls')
            try:
                num = int(num)
                settings[attr] = num
                write_channels(data)
                return
            except ValueError:
                print('not a valid number')
    return mod_loop


def default_filter(data):
    print()
    while True:
        choices = display_df_filter(data['default'])
        action = get_next_action(choices)
        os.system('cls')
        if action == 'break':
            print()
            return
        else:
            action(data)


def blacklist(settings, attr: str):
    # column is set to 1 because korean lang breaks ljust
    def blacklist_loop(data):
        bl_dict = settings[attr]
        page = 1
        print('Select an empty container to add, select an occupied one to delete')
        while True:
            elems_on_page = 10
            start = (page - 1) * elems_on_page
            end = page * elems_on_page
            for i in range(start + 1, end + 1):
                print(f'{i}.'.rjust(4) + (bl_dict.get(str(i)) or ''))
            select = 11 if page == 1 else 1
            print(f' {select}. Go back  {select+1}. next  {select+2}. previous')
            try:
                userinput = int(input('Input: '))
            except ValueError:
                os.system('cls')
                print()
                continue
            if userinput in range(start + 1, end + 1):
                if bl_dict.get(str(userinput)):
                    os.system('cls')
                    del bl_dict[str(userinput)]
                    write_channels(data)
                else:
                    new = input('Add: ')
                    os.system('cls')
                    if new:
                        bl_dict[str(userinput)] = new
                        write_channels(data)
                    else:
                        print('Empty strings are not accepted')
            elif userinput == select:
                os.system('cls')
                print()
                return
            elif userinput == select + 1:
                page += 1
                os.system('cls')
                print()
            elif userinput == select + 2:
                os.system('cls')
                if page == 1:
                    print('This is the first page')
                else:
                    page -= 1
                    print()
            else:
                os.system('cls')
                print('Invalid input')
    return blacklist_loop


# display related
def display_main():
    print('[ARCALIVE DOWNLOADER v1]')
    print(' 1. Download')
    print(' 2. Register a channel')
    print(' 3. Delete a channel')
    print(' 4. Configure channel specific filter')
    print(' 5. Configure default filter')
    print(' 6. Change default download location')
    print(' 7. Quit')
    choices = {
        '1': download, '2': register_channel,
        '3': delete_channel, '4': specific_filter,
        '5': default_filter, '6': change_dl_location,
        '7': 'break'
    }
    return choices


def display_ch_filter(ch_data):
    print(f'[CHANNEL SETTINGS: {ch_data["channel_name"]}]')
    print(' 1. Filter download by title blacklist'.ljust(50, '-') + f'[{ch_data["title"]}]')
    print(' 2. Manage title blacklist', end='\n\n')
    print(' 3. Filter download by content blacklist'.ljust(50, '-') + f'[{ch_data["content"]}]')
    print(' 4. Manage content blacklist', end='\n\n')
    print(' 5. Filter download by uploader'.ljust(50, '-') + f'[{ch_data["uploader"]}]')
    print(' 6. Manage uploader blacklist (not yet implemented)', end='\n\n')
    print(' 7. Filter download by up-votes'.ljust(50, '-') + f'[{ch_data["upvote"]}]')
    print(' 8. Manage upvote count ' + f'(download if {ch_data["upvote_num"]} or more)', end='\n\n')
    print(' 9. Filter download by down-votes'.ljust(50, '-') + f'[{ch_data["downvote"]}]')
    print('10. Manage downvote count ' + f'(download if {ch_data["downvote_num"]} or less)', end='\n\n')
    print('11. Filter download by combined votes'.ljust(50, '-') + f'[{ch_data["combined"]}]')
    print('12. Manage combined vote count ' + f'(download if {ch_data["combined_num"]} or more)', end='\n\n')
    print('13. Filter download by CHANNEL CATEGORY'.ljust(50, '-') + f'[{ch_data["category"]}]')
    print('14. Manage channel category blacklist', end='\n\n')
    print('15. Favorite (shows at the top when selecting)'.ljust(50, '-') + f'[{ch_data["fav"]}]')
    print('16. Go back')
    choices = {
        '1': toggle(ch_data, 'title'), '2': blacklist(ch_data, 'title_bl'),
        '3': toggle(ch_data, 'content'), '4': blacklist(ch_data, 'content_bl'),
        '5': toggle(ch_data, 'uploader'), '6': blacklist(ch_data, 'uploader_bl'),
        '7': toggle(ch_data, 'upvote'), '8': modify(ch_data, 'upvote_num'),
        '9': toggle(ch_data, 'downvote'), '10': modify(ch_data, 'downvote_num'),
        '11': toggle(ch_data, 'combined'), '12': modify(ch_data, 'combined_num'),
        '13': toggle(ch_data, 'category'), '14': ch_blacklist(ch_data, 'category_bl'),
        '15': toggle(ch_data, 'fav'), '16': 'break'
    }
    return choices


def display_df_filter(df_data):
    print('[DEFAULT SETTINGS]')
    print(' 1. Filter download by title blacklist'.ljust(50, '-') + f'[{df_data["title"]}]')
    print(' 2. Manage title blacklist', end='\n\n')
    print(' 3. Filter download by content blacklist'.ljust(50, '-') + f'[{df_data["content"]}]')
    print(' 4. Manage content blacklist', end='\n\n')
    print(' 5. Filter download by uploader'.ljust(50, '-') + f'[{df_data["uploader"]}]')
    print(' 6. Manage uploader blacklist (not yet implemented)', end='\n\n')
    print(' 7. Filter download by up-votes'.ljust(50, '-') + f'[{df_data["upvote"]}]')
    print(' 8. Manage upvote count ' + f'(download if {df_data["upvote_num"]} or more)', end='\n\n')
    print(' 9. Filter download by down-votes'.ljust(50, '-') + f'[{df_data["downvote"]}]')
    print('10. Manage downvote count ' + f'(download if {df_data["downvote_num"]} or less)', end='\n\n')
    print('11. Filter download by combined votes'.ljust(50, '-') + f'[{df_data["combined"]}]')
    print('12. Manage combined vote count ' + f'(download if {df_data["combined_num"]} or more)', end='\n\n')
    print('13. Go back')
    choices = {
        '1': toggle(df_data, 'title'), '2': blacklist(df_data, 'title_bl'),
        '3': toggle(df_data, 'content'), '4': blacklist(df_data, 'content_bl'),
        '5': toggle(df_data, 'uploader'), '6': blacklist(df_data, 'uploader_bl'),
        '7': toggle(df_data, 'upvote'), '8': modify(df_data, 'upvote_num'),
        '9': toggle(df_data, 'downvote'), '10': modify(df_data, 'downvote_num'),
        '11': toggle(df_data, 'combined'), '12': modify(df_data, 'combined_num'),
        '13': 'break'
    }
    return choices


def display_download(ch_data):
    print(f'[DOWNLOAD CHANNEL: {ch_data["channel_name"]}]')
    print(' 1. Start download')
    print(f' 2. Download category: {last_downloaded_category(ch_data)}')
    print(' 3. Use default filter'.ljust(50, '-') + f'[{ch_data["prev"]["df_f"]}]')
    print(' 4. Use channel specific filter'.ljust(50, '-') + f'[{ch_data["prev"]["ch_f"]}]')
    print(' 5. Go back')


# channel maintaining
def specific_filter(data):
    ch_data = select_channel(data)
    os.system('cls')
    if ch_data is None:
        print('Register a channel first')
        return
    print()
    while True:
        choices = display_ch_filter(ch_data)
        action = get_next_action(choices)
        os.system('cls')
        if action == 'break':
            print()
            return
        else:
            action(data)


def select_channel(data) -> "channel's settings(dict)":
    if len(data['channels']) == 0:
        return None
    favlist = []
    ch_list = []
    for dic in data['channels']:
        if dic['fav'] is True:
            favlist.append(dic)
        else:
            ch_list.append(dic)
    ch_list = favlist + sorted(ch_list, key=lambda x: x['dl_count'], reverse=True)
    print()
    while True:
        for i in range(len(ch_list)):
            print(f'{i+1}.'.rjust(3) + ch_list[i]['channel_name'])
        ans = input('Select channel: ')
        try:
            ans = int(ans) - 1
            return ch_list[ans]
        except:
            os.system('cls')
            print('Invaild input')


def ch_blacklist(ch_settings, attr):
    def category_loop(data):
        category_bl = ch_settings[attr]
        page = 1
        print('Select an empty container to add, select an occupied one to delete')
        while True:
            elems_on_page = 10
            start = (page - 1) * elems_on_page
            end = page * elems_on_page
            for i in range(start + 1, end + 1):
                print(f'{i}.'.rjust(4) + (category_bl.get(str(i))[1] if category_bl.get(str(i)) else ''))
            select = 11 if page == 1 else 1
            print(f' {select}. Go back  {select+1}. next  {select+2}. previous')
            try:
                userinput = int(input('Input: '))
            except ValueError:
                os.system('cls')
                print('Invalid input')
                continue
            os.system('cls')
            if userinput in range(start + 1, end + 1):
                if category_bl.get(str(userinput)):
                    del category_bl[str(userinput)]
                    write_channels(data)
                else:
                    ct_choice = category_select(ch_settings['channel_category'], category_bl)
                    os.system('cls')
                    if ct_choice:
                        category_bl[str(userinput)] = ct_choice
                        write_channels(data)
                    else:
                        print('Invalid input')
            elif userinput == select:
                print()
                return
            elif userinput == select + 1:
                page += 1
                print()
            elif userinput == select + 2:
                if page == 1:
                    print('This is the first page')
                else:
                    page -= 1
                    print()
            else:
                print('Invalid input')
    return category_loop


def category_select(category_list, category_bl):
    display_list = [x for x in category_list if x not in category_bl.values()]
    # print the name out
    for i in range(0, len(display_list)):
        print(f'{i+1}.'.rjust(3) + display_list[i][1])
    try:
        userinput = int(input('Add: '))
        return display_list[userinput - 1]
    except:
        return


# TODO: move to downloader
def register_channel(data):
    ch_data = default_setting()
    url = input('Input channel url: ')
    url = url.strip()
    match = re.search(r'https://arca.live/b/\w+', url)
    if match:
        url = match.group(0)
        try:
            r = requests.get(url)
            r.raise_for_status()
            soup = bs4.BeautifulSoup(r.text, 'html.parser')
            ch_data['channel_name'] = soup.select_one('.board-title > a:nth-child(2)').getText()
            if not ch_data['channel_name']:
                raise Exception('no channel name found')
            for tag in soup.select('.board-category a'):
                ch_data['channel_category'].append([tag['href'], tag.getText()])
            ch_data['channel_url'] = url
            os.system('cls')
            data['channels'].append(ch_data)
            write_channels(data)
            return
        except Exception as expt:
            print('failed to register:', expt)
    else:
        os.system('cls')
        print('URL not valid')
        return


def delete_channel(data):
    if len(data['channels']) == 0:
        os.system('cls')
        print('Register a channel first')
        return
    print()
    while True:
        for i, dic in enumerate(data['channels']):
            print(f'{i+1}.'.rjust(3) + dic['channel_name'])
        ans = input('Select channel: ')
        try:
            ans = int(ans) - 1
            ch_name = data['channels'][ans]['channel_name']
            break
        except:
            os.system('cls')
            print('Invaild input')
    os.system('cls')
    print(f'Are you sure you want to delete {ch_name}?')
    print(' 1. Yes  2. No')
    usrinput = input('Input: ')
    os.system('cls')
    if usrinput == '1':
        del data['channels'][ans]
        write_channels(data)
    else:
        print('Channel deletion aborted')


def last_downloaded_category(ch_data):
    cat_index = ch_data['prev']['category']
    return ch_data['channel_category'][cat_index][1]


# TODO: implement
def download(data):
    ch_data = select_channel(data)
    os.system('cls')
    if ch_data is None:
        print('Register a channel first')
        return
    print()
    while True:
        display_download(ch_data)
        ans = input('Input: ')
        os.system('cls')
        # download
        if ans == '1':
            print('Input page number')
            while True:
                try:
                    startpage = int(input('Starting page: '))
                    endpage = int(input('Ending page: '))
                except ValueError:
                    os.system('cls')
                    print('Invalid input')
                    continue
                if startpage <= 0 or endpage < startpage:
                    os.system('cls')
                    print('Enter valid starting page and ending page')
                    continue
                os.system('cls')
                print('Starting download...')
                downloader.temp_download(ch_data, startpage, endpage)
                input('Press enter')
                os.system('cls')
                print()
                return
        # select category
        elif ans == '2':
            print()
            while True:
                for i, category_name in enumerate((x[1] for x in ch_data['channel_category'])):
                    print(f'{i+1}.'.rjust(3) + category_name)
                try:
                    userinput = int(input('Input: ')) - 1
                except ValueError:
                    os.system('cls')
                    print('Invalid input')
                    continue
                os.system('cls')
                if userinput in range(len(ch_data['channel_category'])):
                    ch_data['prev']['category'] = userinput
                    write_channels(data)
                    break
                else:
                    print('Invalid index')
        # toggle default filter
        elif ans == '3':
            ch_data['prev']['df_f'] = not ch_data['prev']['df_f']
            if ch_data['prev']['df_f'] and ch_data['prev']['ch_f']:
                ch_data['prev']['ch_f'] = False
            write_channels(data)
        # toggle channel filter
        elif ans == '4':
            ch_data['prev']['ch_f'] = not ch_data['prev']['ch_f']
            if ch_data['prev']['df_f'] and ch_data['prev']['ch_f']:
                ch_data['prev']['df_f'] = False
            write_channels(data)
        elif ans == '5':
            print()
            return
        else:
            print('Invalid input')


def change_dl_location(data):
    pass


if __name__ == '__main__':
    main()
