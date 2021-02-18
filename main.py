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

        # thread kill signal
        self.destroy = False

        # root
        self.root.title('Arca-downloader')
        self.root.geometry('510x300')
        self.root.option_add('*tearOff', tk.FALSE)
        self.root.protocol('WM_DELETE_WINDOW', self.window_close)
        self.root.bind('<<DownloadComplete>>', self.download_completion)
        self.root.bind('<<ChannelWindowClose>>', self.close_channels)
        # route paste event to entry
        self.root.bind('<<Paste>>', lambda e: self.ent_console.event_generate('<<Paste>>'))

        # menu
        self.mnu_main = tk.Menu(self.root)

        self.dl_mode = tk.IntVar(value=self.data['dl_mode'])
        self.log_mode = tk.IntVar(value=self.data['log_mode'])

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
        self.mnu_save.add_command(label='Change save location', command=self.change_dl_location)

        self.mnu_log = tk.Menu(self.mnu_main)
        self.mnu_log.add_radiobutton(
            label='Verbose: log all info ', variable=self.log_mode, value=0, command=self.change_log_mode
        )
        self.mnu_log.add_radiobutton(
            label='Silent: log essential info', variable=self.log_mode, value=1, command=self.change_log_mode
        )

        self.mnu_help = tk.Menu(self.mnu_main)
        self.mnu_help.add_command(
            label='Report issues', command=lambda: self.open_webpage('https://github.com/ostgor/arca-downloader/issues')
        )
        self.mnu_help.add_command(
            label='Github', command=lambda: self.open_webpage('https://github.com/ostgor/arca-downloader')
        )
        self.mnu_help.add_separator()
        self.mnu_help.add_command(label='About', command=self.about)

        self.mnu_main.add_command(label='Channels', command=lambda: ChannelPage(self))
        self.mnu_main.add_command(label='Settings', command=lambda: SettingsPage(self))
        self.mnu_main.add_cascade(label='Save', menu=self.mnu_save)
        self.mnu_main.add_cascade(label='Log', menu=self.mnu_log)
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
        self.log('[Arca-Downloader v2.0 by obstgor@github]\n', essential=True)
        if self.new_setting:
            self.log('could not find settings, default settings created', essential=True)
        else:
            self.log('settings loaded successfully', essential=True)

        self.ent_console = ttk.Entry(self.fr_console)
        self.ent_console.bind('<Return>', self.entry_enter)
        self.ent_console.bind('<<Paste>>', self.paste)

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

        self.downloading = False

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
                self.log('settings not saved: type "save" to try again', essential=True)
                self.log(traceback.format_exc(), essential=True)
            messagebox.showerror(
                title='Permission Error',
                message='Permission error: Could not save settings'
            )
            return
        except Exception as expt:
            if log:
                self.log('settings not saved: type "save" to try again', essential=True)
                self.log(traceback.format_exc(), essential=True)
            messagebox.showerror(
                title='Settings Corrupted',
                message='Error: Could not save settings',
                detail=str(expt)
            )
            return
        if log:
            self.log('settings saved', essential=True)

    def log(self, *args: str, sep=' ', end='\n', essential=False):
        if self.data['log_mode'] == 0 or essential:
            self.txt_console['state'] = 'normal'
            self.txt_console.insert('end', sep.join(args) + end)
            self.txt_console['state'] = 'disabled'
            self.txt_console.see('end')

    def change_dl_mode(self):
        self.data['dl_mode'] = self.dl_mode.get()
        self.write_settings()

    def change_log_mode(self):
        self.data['log_mode'] = self.log_mode.get()
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
            self.log('could not open webpage:', essential=True)
            self.log(traceback.format_exc(), essential=True)

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
            sep='\n', essential=True
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

    def paste(self, event):
        self.ent_console.insert('end', self.root.clipboard_get())
        return 'break'

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
        # clear console
        self.txt_console['state'] = 'normal'
        self.txt_console.delete('3.0', 'end')
        self.txt_console.insert('end', '\n')
        self.txt_console['state'] = 'disabled'

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
        self.downloading = True
        downloader.Downloader(self, selected_ch, selected_cat, start_pg, end_pg, filter_mode).start()

    def window_close(self):
        if not self.downloading:
            self.root.destroy()
        else:
            answer = messagebox.askyesno(
                title='Download in progress', message='Download still in progress! Do you still want to exit?'
            )
            if answer is False:
                return
            else:
                self.destroy = True
                messagebox.showinfo(title='Stopping...', message='Shutting down downloader thread')
                return

    def download_completion(self, event):
        if self.destroy:
            self.root.destroy()
            return
        self.downloading = False
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

    def entry_enter(self, event):
        command = self.ent_console.get().lower()
        match = re.search(r'https://.*arca.live/b/\w+/\d+', command)
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
                sep='\n', essential=True
            )
        elif command == 'save':
            self.write_settings()
        elif command == 'clear':
            self.txt_console['state'] = 'normal'
            self.txt_console.delete('3.0', 'end')
            self.txt_console.insert('end', '\n')
            self.txt_console['state'] = 'disabled'
        else:
            self.log('invalid command, type "help" for info', essential=True)

    def close_channels(self, event):
        # reset comboboxes
        self.ch_list, self.ch_name_list = self.channel_list()
        self.cbb_channel['values'] = self.ch_name_list
        if self.ch_name_list:
            self.cbb_channel.set('Select channel')
        else:
            self.cbb_channel.set('Register a channel first')
        self.cbb_category['values'] = []
        self.cbb_category.set('')
        self.cbb_filter.set('')
        self.ch_valid = False
        self.btn_download.state(['disabled'])


class ChannelPage(GUI):
    def __init__(self, gui):
        self.gui = gui
        self.data = gui.data
        self.txt_console = gui.txt_console

        # new window
        self.window = tk.Toplevel(gui.root)
        self.window.geometry(f'+{gui.root.winfo_rootx()}+{gui.root.winfo_rooty()}')
        self.window.title('Manage Channel')
        self.window.resizable(tk.FALSE, tk.FALSE)
        self.window.protocol('WM_DELETE_WINDOW', self.window_close)
        self.window.transient(gui.root)
        self.window.wait_visibility()
        self.window.grab_set()

        # blacklist
        self.list_variable = tk.StringVar(value=[x['channel_name'] for x in self.data['channels']])

        self.ent_url = ttk.Entry(self.window, width=30)
        self.ent_url.focus()
        self.ent_url.bind('<Return>', lambda e: self.register_channel())

        btn_register = ttk.Button(self.window, text='Register', command=self.register_channel)
        self.btn_delete = ttk.Button(self.window, text='Delete', command=self.delete_channel)
        self.btn_delete.state(['disabled'])

        self.lst_channels = tk.Listbox(self.window, height=15, width=25, relief='flat', listvariable=self.list_variable)
        self.lst_channels.bind('<<ListboxSelect>>', self.listbox_select)

        scr_listbox = ttk.Scrollbar(self.window, orient=tk.VERTICAL, command=self.lst_channels.yview)
        self.lst_channels['yscrollcommand'] = scr_listbox.set

        ttk.Style().configure('warn.TLabel', foreground='red')
        self.lbl_warning = ttk.Label(self.window, style='warn.TLabel', wrap=100)

        self.ent_url.grid(column=2, row=0, padx=15, sticky='s')
        btn_register.grid(column=2, row=1)
        self.lst_channels.grid(column=0, row=0, rowspan=5, pady=10, padx=(10, 0))
        scr_listbox.grid(column=1, row=0, rowspan=5, sticky='wns', pady=10)
        self.btn_delete.grid(column=2, row=2, sticky='n')
        self.lbl_warning.grid(column=2, row=3)

    def listbox_select(self, event):
        if self.lst_channels.curselection():
            self.btn_delete.state(['!disabled'])

    def delete_channel(self):
        ans = messagebox.askyesno(
            title='Confirmation',
            message=f'Are you sure you want to delete {self.lst_channels.get(self.lst_channels.curselection()[0])}?'
        )
        if not ans:
            return
        del self.data['channels'][self.lst_channels.curselection()[0]]
        self.write_settings()
        self.list_variable.set([x['channel_name'] for x in self.data['channels']])
        if not self.lst_channels.curselection():
            self.btn_delete.state(['disabled'])

    def register_channel(self):
        ch_url = self.ent_url.get()
        self.ent_url.delete(0, 'end')
        ch_url.strip()
        match = re.search(r'https://.*arca.live/b/\w+', ch_url)
        if not match:
            self.warn('URL not valid')
            return
        ch_url = match.group(0)
        ch_data = default_setting()
        try:
            ch_data = downloader.ch_register(ch_url, ch_data)
        except Exception as expt:
            messagebox.showerror(
                title='Failed to get channel information',
                message=traceback.format_exc()
            )
            return
        self.data['channels'].append(ch_data)
        self.write_settings()

        self.list_variable.set([x['channel_name'] for x in self.data['channels']])
        if not self.lst_channels.curselection():
            self.btn_delete.state(['disabled'])
        self.lst_channels.see(self.lst_channels.size() - 1)

    def warn(self, text):
        self.lbl_warning['text'] = text
        self.window.after(3000, lambda: self.lbl_warning.configure(text=''))

    def window_close(self):
        self.gui.root.event_generate('<<ChannelWindowClose>>')
        self.window.grab_release()
        self.window.destroy()


class SettingsPage(GUI):
    def __init__(self, gui):
        self.data = gui.data
        self.txt_console = gui.txt_console

        self.window = tk.Toplevel(gui.root)
        self.window.geometry(f'+{gui.root.winfo_rootx()}+{gui.root.winfo_rooty()}')
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
        labelframe = ttk.Labelframe(self.window, text='Filter active/inactive')

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

        btn_title = ttk.Button(labelframe, text='Manage', command=lambda: BlackList(self, 'title_bl'))
        btn_content = ttk.Button(labelframe, text='Manage', command=lambda: BlackList(self, 'content_bl'))
        btn_uploader = ttk.Button(labelframe, text='Manage', command=lambda: BlackList(self, 'uploader_bl'))
        self.btn_category = ttk.Button(labelframe, text='Manage', command=lambda: CategoryBlackList(self))

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
        # check if previous channel existed and if so save previous channel
        if self.selected_ch is not None:
            self.update_data()
            self.write_settings()

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
        self.update_data()
        self.write_settings()
        self.window.grab_release()
        self.window.destroy()

    def update_data(self):
        self.selected_ch['title'] = self.title.get()
        self.selected_ch['content'] = self.content.get()
        self.selected_ch['uploader'] = self.uploader.get()
        self.selected_ch['upvote'] = self.upvote.get()
        self.selected_ch['downvote'] = self.downvote.get()
        self.selected_ch['combined'] = self.combined.get()
        self.selected_ch['category'] = self.category.get()
        self.selected_ch['fav'] = self.fav.get()
        self.selected_ch['upvote_num'] = self.upvote_num.get()
        self.selected_ch['downvote_num'] = self.downvote_num.get()
        self.selected_ch['combined_num'] = self.combined_num.get()


class BlackList(SettingsPage):
    def __init__(self, settings, attr: str):
        self.data = settings.data
        self.bl_list = settings.selected_ch[attr]
        self.txt_console = settings.txt_console

        # new window
        self.window = tk.Toplevel(settings.window)
        self.window.geometry(f'+{settings.window.winfo_rootx()}+{settings.window.winfo_rooty()}')
        self.window.title('Manage Blacklist')
        self.window.resizable(tk.FALSE, tk.FALSE)
        self.window.protocol('WM_DELETE_WINDOW', self.window_close)
        self.window.transient(settings.window)
        self.window.wait_visibility()
        self.window.grab_set()

        # blacklist
        self.list_variable = tk.StringVar(value=self.bl_list)

        ttk.Style().configure('warn.TLabel', foreground='red')
        self.lbl_warning = ttk.Label(self.window, style='warn.TLabel', wrap=100)

        self.ent_blacklist = ttk.Entry(
            self.window, width=15, validate='key', validatecommand=(self.window.register(self.check_entry), '%P')
        )
        self.ent_blacklist.focus()
        self.ent_blacklist.bind('<Return>', lambda e: self.add_blacklist())

        self.btn_add = ttk.Button(self.window, text='Add', command=self.add_blacklist)
        self.btn_add.state(['disabled'])
        self.btn_delete = ttk.Button(self.window, text='Delete', command=self.delete_blacklist)

        self.lst_blacklist = tk.Listbox(self.window, height=15, relief='flat', listvariable=self.list_variable)
        self.lst_blacklist.bind('<<ListboxSelect>>', self.listbox_select)
        if self.bl_list:
            self.lst_blacklist.selection_set(0)
        else:
            self.btn_delete.state(['disabled'])
        scr_listbox = ttk.Scrollbar(self.window, orient=tk.VERTICAL, command=self.lst_blacklist.yview)
        self.lst_blacklist['yscrollcommand'] = scr_listbox.set

        self.ent_blacklist.grid(column=2, row=0, padx=15, sticky='s')
        self.btn_add.grid(column=2, row=1)
        self.lst_blacklist.grid(column=0, row=0, rowspan=5, pady=10, padx=(10, 0))
        scr_listbox.grid(column=1, row=0, rowspan=5, sticky='wns', pady=10)
        self.btn_delete.grid(column=2, row=2, sticky='n')
        self.lbl_warning.grid(column=2, row=3)

    def check_entry(self, newval):
        if newval == '':
            self.btn_add.state(['disabled'])
        else:
            self.btn_add.state(['!disabled'])
        return True

    def listbox_select(self, event):
        if self.lst_blacklist.curselection():
            self.btn_delete.state(['!disabled'])

    def delete_blacklist(self):
        del self.bl_list[self.lst_blacklist.curselection()[0]]
        self.write_settings()
        self.list_variable.set(self.bl_list)
        if not self.lst_blacklist.curselection():
            self.btn_delete.state(['disabled'])

    def add_blacklist(self):
        word = self.ent_blacklist.get()
        self.ent_blacklist.delete(0, 'end')
        if word == '':
            self.warn('Empty strings are not accepted!')
            return
        self.bl_list.append(word)
        self.list_variable.set(self.bl_list)
        self.write_settings()
        self.lst_blacklist.see(len(self.bl_list) - 1)

    def warn(self, text):
        self.lbl_warning['text'] = text
        self.window.after(3000, lambda: self.lbl_warning.configure(text=''))

    def window_close(self):
        self.window.grab_release()
        self.window.destroy()


class CategoryBlackList(SettingsPage):
    def __init__(self, settings):
        self.data = settings.data
        self.selected_ch = settings.selected_ch
        self.bl_list = self.selected_ch['category_bl']
        self.txt_console = settings.txt_console

        # new window
        self.window = tk.Toplevel(settings.window)
        self.window.geometry(f'+{settings.window.winfo_rootx()}+{settings.window.winfo_rooty()}')
        self.window.title('Manage Blacklist')
        self.window.resizable(tk.FALSE, tk.FALSE)
        self.window.protocol('WM_DELETE_WINDOW', self.window_close)
        self.window.transient(settings.window)
        self.window.wait_visibility()
        self.window.grab_set()

        # blacklist
        self.list_variable = tk.StringVar(value=self.bl_list)

        self.cbb_blacklist = ttk.Combobox(
            self.window, width=15,
            values=[x[1] for x in self.selected_ch['channel_category'] if x[1] not in self.bl_list][1:]
        )
        self.cbb_blacklist.set('Select category')
        self.cbb_blacklist.bind('<<ComboboxSelected>>', self.combobox_select)
        self.cbb_blacklist.state(['readonly'])

        self.btn_add = ttk.Button(self.window, text='Add', command=self.add_blacklist)
        self.btn_add.state(['disabled'])
        self.btn_delete = ttk.Button(self.window, text='Delete', command=self.delete_blacklist)

        self.lst_blacklist = tk.Listbox(self.window, height=15, relief='flat', listvariable=self.list_variable)
        # listboxselect is also generated when selection is removed (selecting a combobox when listbox is selected)
        self.lst_blacklist.bind('<<ListboxSelect>>', self.listbox_select)
        if self.bl_list:
            self.lst_blacklist.selection_set(0)
        else:
            self.btn_delete.state(['disabled'])
        scr_listbox = ttk.Scrollbar(self.window, orient=tk.VERTICAL, command=self.lst_blacklist.yview)
        self.lst_blacklist['yscrollcommand'] = scr_listbox.set

        self.cbb_blacklist.grid(column=2, row=0, padx=15, sticky='s')
        self.btn_add.grid(column=2, row=1)
        self.lst_blacklist.grid(column=0, row=0, rowspan=5, pady=10, padx=(10, 0))
        scr_listbox.grid(column=1, row=0, rowspan=5, sticky='wns', pady=10)
        self.btn_delete.grid(column=2, row=2, sticky='n')

    def combobox_select(self, event):
        self.cbb_blacklist.selection_clear()
        self.btn_add.state(['!disabled'])
        self.btn_delete.state(['disabled'])

    def listbox_select(self, event):
        if self.lst_blacklist.curselection():
            self.btn_delete.state(['!disabled'])

    def add_blacklist(self):
        self.bl_list.append(self.cbb_blacklist.get())
        self.cbb_blacklist.set('Select category')
        self.btn_add.state(['disabled'])
        self.cbb_blacklist.configure(
            values=[x[1] for x in self.selected_ch['channel_category'] if x[1] not in self.bl_list][1:]
        )
        self.list_variable.set(self.bl_list)
        self.write_settings()
        self.lst_blacklist.see(len(self.bl_list) - 1)

    def delete_blacklist(self):
        del self.bl_list[self.lst_blacklist.curselection()[0]]
        self.write_settings()
        self.list_variable.set(self.bl_list)
        # refresh combobox
        self.cbb_blacklist.configure(
            values=[x[1] for x in self.selected_ch['channel_category'] if x[1] not in self.bl_list][1:]
        )
        self.cbb_blacklist.set('Select category')
        self.btn_add.state(['disabled'])

        if not self.lst_blacklist.curselection():
            self.btn_delete.state(['disabled'])

    def window_close(self):
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
            y = self.widget.winfo_rooty() + self.widget.winfo_height()
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
        'prev_ch': None,
        'log_mode': 0
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
            for key in ('channel_category', 'category_bl', 'title_bl', 'content_bl', 'uploader_bl'):
                if type(data[key]) is not list:
                    raise Exception('not a list')
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
    if type(data['log_mode']) is not int:
        raise Exception('log_mode not int')
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
        'category_bl': [],
        'title': False,
        'title_bl': [],
        'content': False,
        'content_bl': [],
        'upvote': False,
        'upvote_num': 0,
        'downvote': False,
        'downvote_num': 0,
        'combined': False,
        'combined_num': 0,
        'uploader': False,
        'uploader_bl': []
    }
    return df_setting


# TODO: implement warning if category to download is blacklisted
if __name__ == '__main__':
    GUI()
