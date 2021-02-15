import json
import os
import re
import downloader
import traceback
import webbrowser
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from tkinter import filedialog


class GUI:
    def __init__(self):
        self.root = tk.Tk()
        self.new_setting = False
        self.data = None
        try:
            self.load_settings()
        except PermissionError:
            self.root.withdraw()
            messagebox.showerror(
                title='Permission Error',
                message='Permission denied'
            )
            return
        except Exception as expt:
            self.root.withdraw()
            messagebox.showerror(
                title='Settings Corrupted',
                message='Error: settings corrupted, consider deleting the settings file',
                detail=str(expt)
            )
            return

        # root
        self.root.title('Arca-downloader')
        self.root.geometry('510x300')
        self.root.option_add('*tearOff', tk.FALSE)
        self.root.bind('<<DownloadComplete>>', self.download_completion)

        # menu
        self.mnu_main = tk.Menu(self.root)

        self.dl_mode = tk.IntVar(value=self.data['dl_mode'])

        self.mnu_save = tk.Menu(self.mnu_main)
        self.mnu_save.add_radiobutton(label='/file.ext', variable=self.dl_mode, value=1, command=self.change_dl_mode)
        self.mnu_save.add_radiobutton(
            label='/<channel>/file.ext', variable=self.dl_mode, value=2, command=self.change_dl_mode
        )
        self.mnu_save.add_radiobutton(
            label='/<channel>/<category>/file.ext', variable=self.dl_mode, value=3, command=self.change_dl_mode
        )
        self.mnu_save.add_separator()
        self.mnu_save.add_command(label=self.data['dl_location'] or os.getcwd().replace('\\', '/'))
        self.mnu_save.add_command(label='change save location', command=self.change_dl_location)

        self.mnu_help = tk.Menu(self.mnu_main)
        self.mnu_help.add_command(
            label='Report issues', command=lambda: self.open_webpage('https://github.com/ostgor/arca-downloader/issues')
        )
        self.mnu_help.add_command(
            label='Github', command=lambda: self.open_webpage('https://github.com/ostgor/arca-downloader')
        )
        self.mnu_help.add_separator()
        self.mnu_help.add_command(label='About', command=self.about)

        # TODO: implement
        self.mnu_main.add_command(label='Channels')
        self.mnu_main.add_command(label='Settings', command=self.open_Settings)
        self.mnu_main.add_cascade(label='Save', menu=self.mnu_save)
        self.mnu_main.add_cascade(label='Help', menu=self.mnu_help)

        self.root['menu'] = self.mnu_main

        # frames
        self.fr_console = ttk.Frame(self.root)

        self.fr_download = ttk.Frame(self.root)

        self.fr_console.grid(column=0, row=0, sticky='nsew', pady=(5, 0), padx=(3, 0))
        self.fr_download.grid(column=1, row=0, sticky='new', padx=(8, 10), pady=(5, 0))

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        # console
        self.txt_console = tk.Text(self.fr_console, relief='flat', width=40, font=('Consolas', 10), wrap='word')
        self.log('[Arca-Downloader v2.0 by obstgor@github]\n')
        if self.new_setting:
            self.log('could not find settings, default settings created')
        else:
            self.log('settings loaded successfully')

        self.ent_console = ttk.Entry(self.fr_console)
        self.ent_console.bind('<Return>', self.entry_enter)

        self.scr_v = ttk.Scrollbar(self.fr_console, orient=tk.VERTICAL, command=self.txt_console.yview)
        self.txt_console['yscrollcommand'] = self.scr_v.set

        self.txt_console.grid(column=0, row=0, sticky='nsew')
        self.scr_v.grid(column=1, row=0, sticky='nsew')
        self.ent_console.grid(column=0, row=1, sticky='ew', pady=(3, 12))

        self.fr_console.columnconfigure(0, weight=1)
        self.fr_console.rowconfigure(0, weight=1)

        # download page input
        self.pg_valid = True

        self.fr_page = ttk.Frame(self.fr_download)

        lbl_page = ttk.Label(self.fr_page, text='Page')
        lbl_dash = ttk.Label(self.fr_page, text='-')
        # start and end pg can be flipped if starting page is bigger
        self.start_pg = tk.IntVar(value=1)
        self.end_pg = tk.IntVar(value=1)

        self.spb_start = ttk.Spinbox(
            self.fr_page, from_=1, to=999, increment=1, width=4, textvariable=self.start_pg, validate='key',
            validatecommand=(self.root.register(self.check_pg), '%P')
        )
        self.spb_end = ttk.Spinbox(
            self.fr_page, from_=1, to=999, increment=1, width=4, textvariable=self.end_pg, validate='key',
            validatecommand=(self.root.register(self.check_pg), '%P')
        )

        lbl_page.grid(column=0, row=0, padx=(0, 6))
        self.spb_start.grid(column=1, row=0)
        lbl_dash.grid(column=2, row=0, padx=(3, 3))
        self.spb_end.grid(column=3, row=0)

        # download
        self.btn_download = ttk.Button(self.fr_download, text='Download', command=self.download)
        self.btn_download.state(['disabled'])
        self.btn_folder = ttk.Button(self.fr_download, text='Open folder', command=self.open_folder)

        lbl_channel = ttk.Label(self.fr_download, text='Channel')
        lbl_category = ttk.Label(self.fr_download, text='Category')
        lbl_filter = ttk.Label(self.fr_download, text='Filter')

        self.ch_valid = False
        self.cat_list = None
        self.cat_name_list = None

        self.cbb_category = ttk.Combobox(self.fr_download)
        self.cbb_category.bind('<<ComboboxSelected>>', self.cat_selected)
        self.cbb_category.state(['readonly'])

        self.cbb_filter = ttk.Combobox(self.fr_download)
        self.cbb_filter.bind('<<ComboboxSelected>>', self.filter_mode_selected)
        self.cbb_filter['values'] = ('No filter', 'Use default filter', 'Use channel filter')
        self.cbb_filter.state(['readonly'])

        self.cbb_channel = ttk.Combobox(self.fr_download)
        self.cbb_channel.bind('<<ComboboxSelected>>', self.ch_selected)
        self.ch_list, self.ch_name_list = self.channel_list()
        if self.ch_name_list:
            self.cbb_channel['values'] = self.ch_name_list
            try:
                ch_index = self.ch_name_list.index(self.data['prev_ch'])
            except ValueError:
                self.cbb_channel.set('Select channel')
            else:
                self.cbb_channel.current(ch_index)
                self.cbb_channel.event_generate('<<ComboboxSelected>>')
        else:
            self.cbb_channel.set('Register a channel first')
        self.cbb_channel.state(['readonly'])

        lbl_channel.grid(column=0, row=0, sticky='w', pady=(3, 3))
        self.cbb_channel.grid(column=0, row=1)
        lbl_category.grid(column=0, row=2, sticky='w', pady=(3, 3))
        self.cbb_category.grid(column=0, row=3)
        lbl_filter.grid(column=0, row=4, sticky='w', pady=(3, 3))
        self.cbb_filter.grid(column=0, row=5)
        self.fr_page.grid(column=0, row=6, pady=(15, 0), sticky='w')
        self.btn_download.grid(column=0, row=7, pady=(15, 0))
        self.btn_folder.grid(column=0, row=8, pady=(8, 0))

        # mainloop
        self.root.mainloop()

    def load_settings(self):
        if os.path.exists('arca_downloader_settings.json'):
            with open('arca_downloader_settings.json', 'r') as f:
                self.data = json.load(f)
            verify_data(self.data)
        else:
            self.new_setting = True
            self.data = create_default()
            self.write_settings(log=False)

    def write_settings(self, log=True):
        try:
            with open('arca_downloader_settings.json', 'w') as f:
                json.dump(self.data, f, indent=4)
        except PermissionError:
            if log:
                self.log('settings not saved: type "save" to try again')
                self.log(traceback.format_exc())
            messagebox.showerror(
                title='Permission Error',
                message='Permission error: Could not save settings'
            )
            return
        except Exception as expt:
            if log:
                self.log('settings not saved: type "save" to try again')
                self.log(traceback.format_exc())
            messagebox.showerror(
                title='Settings Corrupted',
                message='Error: Could not save settings',
                detail=str(expt)
            )
            return
        if log:
            self.log('settings saved')

    def log(self, *args: str, sep=' ', end='\n'):
        self.txt_console['state'] = 'normal'
        self.txt_console.insert('end', sep.join(args) + end)
        self.txt_console['state'] = 'disabled'
        self.txt_console.see('end')

    def change_dl_mode(self):
        self.data['dl_mode'] = self.dl_mode.get()
        self.write_settings()

    def change_dl_location(self):
        newdir = filedialog.askdirectory(initialdir='.')
        if newdir == '':
            return
        self.data['dl_location'] = newdir
        self.write_settings()
        self.mnu_save.entryconfigure(4, label=newdir)

    def open_webpage(self, url):
        try:
            webbrowser.open(url)
        except Exception:
            self.log('could not open webpage:')
            self.log(traceback.format_exc())

    def open_folder(self):
        os.startfile(self.data['dl_location'] or '.')

    def about(self):
        self.log(
            '\n[About]\n',
            'How to use:\n',
            '1. Register a channel by using the channels menu',
            '2. Select the channel and its category to download',
            '3. You can use filters to avoid downloading downvoted articles or articles containing blacklisted words',
            '4. Manage filters by using the settings menu. You can use a filter specific to the channel you are trying'
            + ' to download, or use a default filter',
            '5. Input page number to download, then click download button to start. The download process is currently'
            + ' single threaded',
            '6. You can also download single articles by copy/pasting the article url to the text entry. Type "help"'
            + ' into the text entry for more information\n',
            'Made with Python 3.9 using tkinter.\nExternal module used: requests, bs4',
            sep='\n'
        )

    def check_pg(self, newval):
        if newval == '':
            self.pg_valid = False
            self.btn_download.state(['disabled'])
            return True
        elif re.search(r'^[0-9]+$', newval):
            self.pg_valid = True
            if self.ch_valid:
                self.btn_download.state(['!disabled'])
            return True
        else:
            return False

    def channel_list(self):
        favlist = []
        ch_list = []
        for dic in self.data['channels']:
            if dic['fav'] is True:
                favlist.append(dic)
            else:
                ch_list.append(dic)
        ch_list = favlist + sorted(ch_list, key=lambda x: x['dl_count'], reverse=True)
        ch_name_list = [ch['channel_name'] for ch in ch_list]
        return ch_list, ch_name_list

    def ch_selected(self, event):
        self.cbb_channel.selection_clear()
        self.ch_valid = True
        selected_ch = self.ch_list[self.cbb_channel.current()]
        # updating category cbb
        self.cat_list = selected_ch['channel_category']
        self.cat_name_list = [l[1] for l in self.cat_list]
        self.cbb_category['values'] = self.cat_name_list
        self.cbb_category.current(selected_ch['prev_category'])
        # updating filter cbb
        self.cbb_filter.current(selected_ch['filter'])
        if self.pg_valid:
            self.btn_download.state(['!disabled'])

    def cat_selected(self, event):
        self.cbb_channel.selection_clear()

    def filter_mode_selected(self, event):
        self.cbb_filter.selection_clear()

    def download(self):
        selected_ch = self.ch_list[self.cbb_channel.current()]
        selected_cat = self.cat_list[self.cbb_category.current()]
        filter_mode = self.cbb_filter.current()
        start_pg, end_pg = sorted((self.start_pg.get(), self.end_pg.get()))
        # set prev data before download
        self.data['prev_ch'] = selected_ch['channel_name']
        selected_ch['prev_category'] = self.cbb_category.current()
        selected_ch['filter'] = filter_mode
        selected_ch['dl_count'] += 1
        self.write_settings()
        # disable widgets
        self.btn_download.state(['disabled'])
        self.cbb_channel.state(['disabled'])
        self.cbb_category.state(['disabled'])
        self.cbb_filter.state(['disabled'])
        self.mnu_main.entryconfigure(0, state=tk.DISABLED)
        self.mnu_main.entryconfigure(1, state=tk.DISABLED)
        self.mnu_main.entryconfigure(2, state=tk.DISABLED)
        self.spb_start.state(['disabled'])
        self.spb_end.state(['disabled'])
        self.ent_console.state(['disabled'])
        # start download
        downloader.Downloader(self, selected_ch, selected_cat, start_pg, end_pg, filter_mode).start()

    # TODO: warn if users try to close app before download is finished
    def download_completion(self, event):
        # enable widgets
        self.btn_download.state(['!disabled'])
        self.cbb_channel.state(['!disabled'])
        self.cbb_category.state(['!disabled'])
        self.cbb_filter.state(['!disabled'])
        self.mnu_main.entryconfigure(0, state=tk.NORMAL)
        self.mnu_main.entryconfigure(1, state=tk.NORMAL)
        self.mnu_main.entryconfigure(2, state=tk.NORMAL)
        self.spb_start.state(['!disabled'])
        self.spb_end.state(['!disabled'])
        self.ent_console.state(['!disabled'])

    # TODO: route paste events to entry
    def entry_enter(self, event):
        command = self.ent_console.get().lower()
        match = re.search(r'https://arca.live/b/\w+/\d+', command)
        self.ent_console.delete(0, 'end')
        if match:
            downloader.PageDownloader(self, match.group(0)).start()
        elif command == 'help':
            self.log(
                '\n[console info]\n',
                '- input article url to download single article. example: "https://arca.live/b/live/000000"',
                '(images will be saved to arca_downloaded folder next to the application)\n',
                '- "clear": clears logging console\n',
                '- "save": save current settings. settings are automatically saved, so there is no reason to use this, '
                + 'except when trying again due to an error while saving\n',
                '- "help": prints this to the logging console',
                sep='\n'
            )
        elif command == 'save':
            self.write_settings()
        elif command == 'clear':
            self.txt_console['state'] = 'normal'
            self.txt_console.delete('3.0', 'end')
            self.txt_console.insert('end', '\n')
            self.txt_console['state'] = 'disabled'
        else:
            self.log('invalid command, type "help" for info')

    def open_Settings(self):
        SettingsPage(self)


class ChannelPage(GUI):
    def __init__(self, gui):
        self.data = gui.data
        self.txt_console = gui.txt_console


class SettingsPage(GUI):
    def __init__(self, gui):
        self.data = gui.data
        self.txt_console = gui.txt_console

        # TODO: override window close to save settings (should save when exiting, not when variables are changed)
        self.window = tk.Toplevel(gui.root)
        self.window.protocol('WM_DELETE_WINDOW', self.window_close)
        self.window.transient(gui.root)
        self.window.wait_visibility()
        self.window.grab_set()
        self.window.title('Settings')
        self.window.resizable(tk.FALSE, tk.FALSE)

        # settings
        self.selected_ch = None
        self.title = tk.BooleanVar()
        self.content = tk.BooleanVar()
        self.uploader = tk.BooleanVar()
        self.upvote = tk.BooleanVar()
        self.downvote = tk.BooleanVar()
        self.combined = tk.BooleanVar()
        self.category = tk.BooleanVar()
        self.fav = tk.BooleanVar()

        # frame
        lbl_channel = ttk.Label(self.window, text='Filter')
        labelframe = ttk.Labelframe(self.window, text='configure')

        # cbb_channel grid goes here
        lbl_channel.grid(column=0, row=0, padx=5, pady=(10, 5), sticky='e')
        labelframe.grid(column=0, row=1, columnspan=2, padx=(10, 10), pady=(0, 15))

        # content
        s = ttk.Style()
        s.configure('my.TCheckbutton', font=('helvetica', 10))

        chk_title = ttk.Checkbutton(
            labelframe, variable=self.title, text='Filter download by title blacklist', style='my.TCheckbutton',
            onvalue=True, offvalue=False
        )
        chk_content = ttk.Checkbutton(
            labelframe, variable=self.content, text='Filter download by content blacklist', style='my.TCheckbutton',
            onvalue=True, offvalue=False
        )
        chk_uploader = ttk.Checkbutton(
            labelframe, variable=self.uploader, text='Filter download by uploader', style='my.TCheckbutton',
            onvalue=True, offvalue=False
        )
        chk_upvote = ttk.Checkbutton(
            labelframe, variable=self.upvote, text='Filter download by upvotes', style='my.TCheckbutton',
            onvalue=True, offvalue=False
        )
        chk_downvote = ttk.Checkbutton(
            labelframe, variable=self.downvote, text='Filter download by downvotes', style='my.TCheckbutton',
            onvalue=True, offvalue=False
        )
        chk_combined = ttk.Checkbutton(
            labelframe, variable=self.combined, text='Filter download by combined votes', style='my.TCheckbutton',
            onvalue=True, offvalue=False
        )
        self.chk_category = ttk.Checkbutton(
            labelframe, variable=self.category, text='Filter download by channel category', style='my.TCheckbutton',
            onvalue=True, offvalue=False
        )
        self.chk_fav = ttk.Checkbutton(
            labelframe, variable=self.fav, text='Favorite (shows at top)', style='my.TCheckbutton',
            onvalue=True, offvalue=False
        )

        ToolTip(chk_upvote, text='Downloads article if upvote count is greater than or equal the setting count')
        ToolTip(chk_downvote, text='Downloads article if downvote count is less than or equal the setting count')
        ToolTip(chk_combined, text='Downloads article if combined count is greater than or equal the setting count')

        btn_title = ttk.Button(labelframe, text='Manage')
        btn_content = ttk.Button(labelframe, text='Manage')
        btn_uploader = ttk.Button(labelframe, text='Manage')
        self.btn_category = ttk.Button(labelframe, text='Manage')

        self.upvote_num = tk.IntVar()
        self.downvote_num = tk.IntVar()
        self.combined_num = tk.IntVar()

        spb_upvote = ttk.Spinbox(labelframe, width=4, textvariable=self.upvote_num, from_=0, to=999, increment=1)
        spb_upvote.state(['readonly'])
        spb_downvote = ttk.Spinbox(labelframe, width=4, textvariable=self.downvote_num, from_=0, to=999, increment=1)
        spb_downvote.state(['readonly'])
        spb_combined = ttk.Spinbox(labelframe, width=4, textvariable=self.combined_num, from_=-999, to=999, increment=1)
        spb_combined.state(['readonly'])

        ToolTip(spb_upvote, text='Downloads article if upvote count is greater than or equal the setting count')
        ToolTip(spb_downvote, text='Downloads article if downvote count is less than or equal the setting count')
        ToolTip(spb_combined, text='Downloads article if combined count is greater than or equal the setting count')

        spb_upvote.grid(column=1, row=6)
        spb_downvote.grid(column=1, row=8)
        spb_combined.grid(column=1, row=10)

        btn_title.grid(column=1, row=0, padx=(0, 10))
        btn_content.grid(column=1, row=2, padx=(0, 10))
        btn_uploader.grid(column=1, row=4, padx=(0, 10))
        self.btn_category.grid(column=1, row=12, padx=(0, 10))

        chk_title.grid(column=0, row=0, sticky='w', padx=(10, 5), pady=3)
        chk_content.grid(column=0, row=2, sticky='w', padx=(10, 5), pady=3)
        chk_uploader.grid(column=0, row=4, sticky='w', padx=(10, 5), pady=3)
        chk_upvote.grid(column=0, row=6, sticky='w', padx=(10, 5), pady=3)
        chk_downvote.grid(column=0, row=8, sticky='w', padx=(10, 5), pady=3)
        chk_combined.grid(column=0, row=10, sticky='w', padx=(10, 5), pady=3)
        self.chk_category.grid(column=0, row=12, sticky='w', padx=(10, 5), pady=3)
        self.chk_fav.grid(column=0, row=14, sticky='w', padx=(10, 5), pady=3)

        # channel combobox
        self.cbb_channel = ttk.Combobox(self.window)
        self.cbb_channel.bind('<<ComboboxSelected>>', self.filter_selected)

        self.ch_list, self.ch_name_list = self.channel_list()
        self.ch_list.insert(0, self.data['default'])
        self.ch_name_list.insert(0, 'Default filter')

        self.cbb_channel['values'] = self.ch_name_list
        try:
            ch_index = self.ch_name_list.index(self.data['prev_ch'])
        except ValueError:
            ch_index = 0
        self.cbb_channel.current(ch_index)
        self.cbb_channel.event_generate('<<ComboboxSelected>>')
        self.cbb_channel.state(['readonly'])

        self.cbb_channel.grid(column=1, row=0, padx=5, pady=(10, 5), sticky='w')

    def filter_selected(self, event):
        # TODO: save changes
        self.cbb_channel.selection_clear()
        self.selected_ch = self.ch_list[self.cbb_channel.current()]
        # if default filter
        if self.cbb_channel.current() == 0:
            self.chk_category.state(['disabled'])
            self.btn_category.state(['disabled'])
            self.chk_fav.state(['disabled'])
        else:
            self.chk_category.state(['!disabled'])
            self.btn_category.state(['!disabled'])
            self.chk_fav.state(['!disabled'])
        # update checkboxes
        self.title.set(self.selected_ch['title'])
        self.content.set(self.selected_ch['content'])
        self.uploader.set(self.selected_ch['uploader'])
        self.upvote.set(self.selected_ch['upvote'])
        self.downvote.set(self.selected_ch['downvote'])
        self.combined.set(self.selected_ch['combined'])
        self.category.set(self.selected_ch['category'])
        self.fav.set(self.selected_ch['fav'])
        self.upvote_num.set(self.selected_ch['upvote_num'])
        self.downvote_num.set(self.selected_ch['downvote_num'])
        self.combined_num.set(self.selected_ch['combined_num'])

    def window_close(self):
        # TODO: save
        self.window.grab_release()
        self.window.destroy()


class ToolTip:
    def __init__(self, widget, text):
        self.id = None
        self.widget = widget
        self.text = text
        self.hint_window = None
        self.widget.bind('<Enter>', self.on_enter)
        self.widget.bind('<Leave>', self.hide_hint)
        self.widget.bind('<Button-1>', self.hide_hint)

    def on_enter(self, event):
        self.id = self.widget.after(500, self.show_hint)

    def hide_hint(self, event):
        if self.hint_window:
            self.hint_window.destroy()
            self.hint_window = None
        self.widget.after_cancel(self.id)

    def show_hint(self):
        if not self.hint_window:
            # the mouse pointer cannot be above the created window as it registers as a leave event, destroying the window
            x = self.widget.winfo_pointerx() + 12
            y = self.widget.winfo_rooty() + self.widget.bbox('insert')[3] + 5
            self.hint_window = tk.Toplevel(self.widget)
            self.hint_window.overrideredirect(True)
            self.hint_window.geometry(f'+{x}+{y}')
            label = ttk.Label(
                self.hint_window, text=self.text, justify='left',
                background="#ffffff", relief=tk.SOLID, borderwidth=1,
                font=("tahoma", "8", "normal"), wraplength=180
            )
            label.pack(ipadx=1)
        else:
            return


def create_default():
    data = {
        'default': default_setting(),
        'channels': [],
        'dl_mode': 3,
        'dl_location': None,
        'prev_ch': None
    }
    return data


def verify_data(data):
    def verify_settings(data, is_channel):
        if type(data) is dict:
            for key in default_setting():
                if key not in data:
                    raise Exception(f'no <{key}> in settings')
            for key in (
                    'title', 'content', 'upvote', 'downvote', 'combined', 'uploader', 'fav', 'category'):
                if type(data[key]) is not bool:
                    raise Exception('not a boolean')
            for key in ('combined_num', 'downvote_num', 'upvote_num', 'dl_count', 'prev_category', 'filter'):
                if type(data[key]) is not int:
                    raise Exception('not an int')
            for key in ('channel_category',):
                if type(data[key]) is not list:
                    raise Exception('not a list')
            for key in ('category_bl', 'title_bl', 'content_bl', 'uploader_bl'):
                if type(data[key]) is not dict:
                    raise Exception('not a dict')
        else:
            raise Exception('data not a dict')
        if is_channel:
            if (type(data['channel_name']) is not str) or (type(data['channel_url']) is not str):
                raise Exception('channel name or url corrupted')
            elif len(data['channel_category']) == 0:
                raise Exception('no channel category')
            return
        else:
            return

    verify_settings(data['default'], False)
    for channel in data['channels']:
        verify_settings(channel, True)
    if type(data['dl_mode']) is not int:
        raise Exception('dl_mode not int')
    if 'dl_location' not in data:
        raise Exception('dl_location not in data')
    if 'prev_ch' not in data:
        raise Exception('prev_ch not in data')


def default_setting():
    df_setting = {
        'channel_name': None,
        'channel_url': None,
        'channel_category': [],
        'prev_category': 0,
        'filter': 0,
        'dl_count': 0,
        'fav': False,
        'category': False,
        'category_bl': {},
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












############################################ LEGACY CODE ###############################################################
def toggle(settings, attr: str):
    def inner(data):
        settings[attr] = not settings[attr]
        write_channels(data)
    return inner


# TODO: if modifying upvotes and downvotes they should be 0 or more
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


def blacklist(settings, attr: str):
    # column is set to 1 because korean language breaks ljust
    def blacklist_loop(data):
        bl_dict = settings[attr]
        page = 1
        print('Select an empty container to add, select an occupied one to delete')
        while True:
            elems_on_page = 10
            start = (page-1) * elems_on_page
            end = page * elems_on_page
            for i in range(start+1, end+1):
                print(f'{i}.'.rjust(4) + (bl_dict.get(str(i)) or ''))
            select = 11 if page == 1 else 1
            print(f' {select}. Go back  {select+1}. next  {select+2}. previous')
            try:
                userinput = int(input('Input: '))
            except ValueError:
                os.system('cls')
                print('Invalid input')
                continue
            if userinput in range(start+1, end+1):
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
    print(' 3. Use default filter'.ljust(50, '-') + f'[{ch_data["df_f"]}]')
    print(' 4. Use channel specific filter'.ljust(50, '-') + f'[{ch_data["ch_f"]}]')
    print(' 5. Go back')


def display_dl_location(data):
    print('[DOWNLOAD LOCATION]')
    print(f' current mode: {data["dl_mode"]}')
    print(' 1. "./<channel name>/file.ext"')
    print(' 2. "./<channel name>/<category name>/file.ext')
    print(' 3. "./arcalive_download/file.ext')
    print(f' 4. User defined - current: {data["dl_location"]}')
    print(' 5. Change user defined location')
    print(' 6. Go back')


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


def ch_blacklist(ch_settings, attr):
    def category_loop(data):
        category_bl = ch_settings[attr]
        page = 1
        print('Select an empty container to add, select an occupied one to delete')
        while True:
            elems_on_page = 10
            start = (page-1) * elems_on_page
            end = page * elems_on_page
            for i in range(start+1, end+1):
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
            if userinput in range(start+1, end+1):
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
    except Exception:
        return


def register_channel(data):
    ch_data = default_setting()
    print()
    url = input('Input channel url: ')
    url = url.strip()
    match = re.search(r'https://arca.live/b/\w+', url)
    if match:
        url = match.group(0)
        try:
            ch_data = downloader.ch_register(url, ch_data)
            os.system('cls')
            data['channels'].append(ch_data)
            write_channels(data)
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
        except Exception:
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
    cat_index = ch_data['prev_category']
    return ch_data['channel_category'][cat_index][1]


# TODO: implement warning if category to download is blacklisted
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
                print(f'Start download on page {startpage}-{endpage}?\n 1. Yes  2. No')
                if input('Input: ') != '1':
                    os.system('cls')
                    print()
                    break
                os.system('cls')
                print('Starting download...')
                try:
                    downloader.temp_download(ch_data, startpage, endpage, data)
                except Exception:
                    print('Failed download:')
                    traceback.print_exc()
                    try:
                        with open('exception_log.txt', 'a') as f:
                            traceback.print_exc(file=f)
                    except Exception as expt:
                        print('Failed to save exception:', expt)
                    input('Press enter to return')
                    os.system('cls')
                    print()
                    return
                # else
                input('Press enter')
                os.system('cls')
                ch_data['dl_count'] += 1
                write_channels(data)
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
                    ch_data['prev_category'] = userinput
                    write_channels(data)
                    break
                else:
                    print('Invalid index')
        # toggle default filter
        elif ans == '3':
            ch_data['df_f'] = not ch_data['df_f']
            if ch_data['df_f'] and ch_data['ch_f']:
                ch_data['ch_f'] = False
            write_channels(data)
        # toggle channel filter
        elif ans == '4':
            ch_data['ch_f'] = not ch_data['ch_f']
            if ch_data['df_f'] and ch_data['ch_f']:
                ch_data['df_f'] = False
            write_channels(data)
        elif ans == '5':
            print()
            return
        else:
            print('Invalid input')


if __name__ == '__main__':
    GUI()
