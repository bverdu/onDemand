# encoding: utf-8
'''
Created on 1 avr. 2015

@author: babe
'''
import os
import collections
from mimetypes import guess_type
# import xml.etree.cElementTree as et
from lxml import etree as et
from twisted.internet import reactor, defer
from kivy.logger import Logger
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.screenmanager import Screen
from kivy.properties import ObjectProperty, StringProperty, ListProperty,\
    DictProperty, BooleanProperty, NumericProperty
from kivy.adapters.dictadapter import DictAdapter
from kivy.uix.listview import ListItemButton
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.dropdown import DropDown
from kivy.uix.popup import Popup
from kivy.uix.bubble import Bubble
from kivy.uix.modalview import ModalView
from kivy.animation import Animation
from kivy.uix.button import Button
from kivy.uix.treeview import TreeViewLabel, TreeViewNode
from kivy.uix.tabbedpanel import TabbedPanelItem
from kivy.uix.image import AsyncImage, Image
from onDemand import config, utils
from upnpy_spyne.utils import didl_decode, id_array_decode, XmlDictConfig

CDS = 'urn:schemas-upnp-org:service:ContentDirectory:1'
PLAYLIST = 'urn:av-openhome-org:service:Playlist:1'
VOLUME = 'urn:av-openhome-org:service:Volume:1'
TIME = 'urn:av-openhome-org:service:Time:1'

Track = collections.namedtuple(
    'Track',
    'artist title album genre url id arturl color duration is_selected')


class MediaPlayer(Screen):

    server = None
    track_list = ListProperty([])
    server_list = ListProperty([])
    renderer_list = ListProperty([])
#     action = StringProperty('>')
    bgimg = StringProperty('data/icons/background_icon2.png')
#     bgimg = StringProperty(
#         'http://www.gqmagazine.fr/uploads/images/thumbs/201445/83/' +
#         '2001__l_odyss__e_de_l_espace_5047.jpeg_north_780x_white.jpg')
    track_list = ListProperty([])
    track_dict = DictProperty()
    time_ = StringProperty('0:00:00')
    renderer_event = DictProperty({})
    server_event = DictProperty({})
    info = StringProperty()
    active_device = 'local'
    active_server = 'local'
    server_tabs = []
    libraries = []
    trees = {}
    _idarray = ''
    idlist = ListProperty()
    tracks_info = DictProperty({})
    lasttrack = 0
    selected = NumericProperty(-1)
    done_selected = False
    pending = []
    playing = BooleanProperty(False)
    volume = NumericProperty(0)
    volume_steps = NumericProperty(100)
    desired_vol = 0
    vol_scheduled = False
    repeat = BooleanProperty(False)
    shuffle = BooleanProperty(False)
    timer = NumericProperty(0)
    _timer = None
    timerevent = True
    duration = NumericProperty(0)
    transportstate = 'Stopped'
    main_ui = None
    sorted_tracks = []
    pop = False
    lists = {}
    device = None
    subscriptions = []
    list_tracks = ObjectProperty()

    def args_converter(idx, inst, val):  # @NoSelf
        return {'text': val.title,
                'id': val.id,
                'img': val.arturl,
                'size_hint_y': None,
                #  'height': 40,
                'artist': val.artist,
                'duration': val.duration,
                'select': val.color}
#     args_converter = lambda idx, inst, val: {'text': val.title,
#                                              'id': val.id,
#                                              'img': val.arturl,
#                                              'size_hint_y': None,
# #                                              'height': 40,
#                                              'artist': val.artist,
#                                              'duration': val.duration,
#                                              'select': val.color}

    def __init__(self, **kwargs):
        if 'controller' in kwargs:
            self.controller = kwargs['controller']
            kwargs['controller'] = None
            del kwargs['controller']
        if 'main_ui' in kwargs:
            self.main_ui = kwargs['main_ui']
            kwargs['main_ui'] = None
            del kwargs['main_ui']
        super(MediaPlayer, self).__init__(**kwargs)
        self.track_list = []
#         print(type(self.track_list))
        self.list_tracks = DictAdapter(
            data=self.tracks_info,
            sorted_keys=self.sorted_tracks,
            args_converter=self.args_converter,
            template='CustomListItem', selection_mode='single',
            propagate_selection_to_data=True, allow_empty_selection=True)
        self.ids['trackslist'].adapter = self.list_tracks
        self.register_server('ti')

    def on_enter(self):
        if self.controller:
            uid = self.controller.current_device['uid']
            if self.active_device != uid:
                self.popup = WaitingPopup(
                    img=Image(source='data/icons/wait.zip'),
                    size_hint=(.4, .4),
                    background='data/icons/empty.png',
                    opacity=0.8)
                self.popup.open()
                self.pop = True
                while len(self.subscriptions) > 0:
                    self.controller.unsubscribe(self.subscriptions.pop())
                self.device = {uid: self.controller.parent.devices[uid]}
                self.register_renderer(uid)
                if self.controller.cloud:
                    self.update_time(True)
            else:
                self.controller.subscribe(
                    {uid: self.controller.parent.devices[uid]},
                    'urn:av-openhome-org:service:Playlist:1',
                    'TransportState',
                    self.on_oh_tstate)
                if self.pop:
                    self.popup.dismiss()
            for server in self.controller.parent.mediaservers:
                if server not in self.server_list:
                    self.server_list.append(server)
#             d = self.controller.call(
#                 self.device,
#                 PLAYLIST,
#                 'Id')
#             d.addCallback(self.on_id)
            d = self.controller.call(
                self.device,
                PLAYLIST,
                'TransportState')
            d.addCallback(self.on_oh_tstate)
            dd = self.controller.call(
                self.device,
                PLAYLIST,
                'Id')
            dd.addCallback(self.on_id)
#             d.addCallback(lambda res: self.on_id(res.Value))

    def update_time(self, repeat):
#         print('update time')
        def on_time(res):
#             print('time result: %s' % res)
            self.on_track_duration(res.Duration)
            self._timer.set(res.Seconds)
        if not self._timer:
            self._timer = Timer(self.on_seconds)
        d = self.controller.call(
            self.device,
            TIME,
            'Time')
        d.addCallback(on_time)
        if self.playing:
            if not self._timer.running:
                self._timer.start()
        if repeat:
            reactor.callLater(10, self.update_time, True)  # @UndefinedVariable

    def show(self, v):
        print(v)
        print(dir(v))

    def on_pre_leave(self):
        if self._timer:
            self._timer.stop()
        if self.pop:
            self.popup.dismiss()

    def on_selected(self, instance, value):
        if value > 0:
            if self.selected in self.tracks_info:
                s = self.tracks_info[self.selected]
                if s.arturl != 'data/image-loading.gif':
                    self.bgimg = s.arturl
            else:
                self.generate_empty_dict([value])
                s = self.tracks_info[self.selected]
            self.tracks_info.update({self.selected: Track(
                artist=s.artist, title=s.title, album=s.album,
                genre=s.genre, url=s.url, id=s.id,
                arturl=s.arturl, color=(.7, .7, .7, .8),
                duration=s.duration, is_selected=False)})
            self.info = s.title
            idx = self.idlist.index(value)
            if idx > 3 and len(self.idlist) > 8:
                self.ids.trackslist.scroll_to(idx-3)
                Logger.debug('scroll to %s' % str(idx - 3))
            else:
                self.ids.trackslist.scroll_to(0)
                Logger.debug('scroll to 0')

    def on_idlist(self, instance, value):
        self.list_tracks.sorted_keys = value
        try:
            self.lasttrack = value[-1]
        except IndexError:
            self.lasttrack = 0

    def on_tracks_info(self, instance, value):
        self.list_tracks.data = value

    def on_server_list(self, instance, value):
#         print('server')
        for item in value:
            if item in self.server_tabs or item == 'Local':
                continue
            self.server_tabs.append(item)
#             print(item)
            ti = ServerItem()
            ti.text = item
#             print(self.controller.parent.mediaservers)
            ti.id = self.controller.parent.mediaservers[item]['uid']
            self.trees.update({item: ti.ids.tree})
            if len(item) > 6:
                ti.size_hint_y = None
                ti.text_size = ti.width, None
                ti.height = ti.texture_size[1]
            self.ids.library.add_widget(ti)
            ti.ids.tree.root_options = {'text': item, 'is_open': False}
            ti.ids.tree.root.populated = False
            ti.ids.tree.root.browsable = True
            ti.ids.tree.bind(on_node_expand=self.get_childs)
            ti.ids.tree.bind(on_node_collapse=self.remove_childs)

    def remove_childs(self, instance, value):
        br = False
        while len(value.nodes) > 0:
            br = True
            instance.remove_node(value.nodes[0])
        value.populated = False
        if br:
            instance.add_node(TreeViewLabel(text='fake'), value)

    def get_childs(self, instance, value):
        if value.populated:
            return
        if value.id is None:
            value.id = '0'
        while len(value.nodes) > 0:
            instance.remove_node(value.nodes[0])
        d = self.controller.call(
            self.server,
            CDS,
            'Browse',
            (value.id, 'BrowseDirectChildren', '*', 0, 0, ''))
        d.addCallback(get_titles)
        d.addCallback(populate_tree, instance, value)

    def on_renderer_list(self, instance, value):
        self.main_ui.ids['active_renderer'].values = ['local'] + value

    def on_idarray(self, value):
#         print('IdArray: %s' % value)
        if value != self._idarray:
#             print('call update tracklist')
            self.update_tracklist(value)

    def on_id(self, value):
        print('Id: %s' % value)
        v = int(value)
        if v in (0, self.selected):
            return
        if v in self.idlist:
            if self.selected != -1:
                s = self.tracks_info[self.selected]
                self.tracks_info.update(
                    {self.selected: Track(
                        artist=s.artist, title=s.title,
                        album=s.album,
                        genre=s.genre, url=s.url, id=s.id,
                        arturl=s.arturl,
                        color=(.5, .5, .5, .5),
                        duration=s.duration,
                        is_selected=False)})
            self.selected = v
        else:
            if self._idarray == '':
                d = self.controller.call(
                    self.device,
                    PLAYLIST,
                    'IdArray')
                d.addCallback(lambda res: self.on_idarray(res.Array))
            if v != 0:
                reactor.callLater(  # @UndefinedVariable
                    1,
                    self.on_id,
                    v)

    def on_seconds(self, value):
        if self.duration != 0:
            self.timer = int(value)
            self.timerevent = True
            self.time_ = '-' + utils.mpdtime_to_upnptime(
                str(self.duration - int(value)), self.transportstate)
        else:
            self.time_ = utils.mpdtime_to_upnptime(
                value, self.transportstate)

    def on_oh_tstate(self, value):
        if value != self.transportstate:
            print('State: %s' % value)
            self.transportstate = value
            if value == 'Stopped':
    #             self.ids.playerstatus.animate_stop()
                self.playing = False
                if 'state' in self.controller.parent.devices[self.active_device]:
                    self.controller.parent.devices[
                        self.active_device]['state'] = False
                else:
                    self.controller.parent.devices[self.active_device].update(
                        {'state': False})
    #             self.action = '>'
                self.time = '0:00:00'
                if self._timer:
                    self._timer.set(0)
            elif value == 'Playing':
    #             self.ids.playerstatus.animate_play()
                self.playing = True
                if 'state' in self.controller.parent.devices[self.active_device]:
                    self.controller.parent.devices[
                        self.active_device]['state'] = True
                else:
                    self.controller.parent.devices[self.active_device].update(
                        {'state': True})
                if self._timer:
                    self._timer.start()
    #             self.action = 'II'
            elif value == 'Paused':
    #             self.ids.playerstatus.animate_pause()
                self.playing = False
                if 'state' in self.controller.parent.devices[self.active_device]:
                    self.controller.parent.devices[
                        self.active_device]['state'] = False
                else:
                    self.controller.parent.devices[self.active_device].update(
                        {'state': False})
    #             self.action = '>'
                if self._timer:
                    self._timer.stop()

    def on_metadata(self, value):
#         print('Metadata: %s' % value)
        if value:
            if self.selected in self.tracks_info:
                info = update_trackinfo(didl_decode(value)[0])
                self.tracks_info.update({self.selected: Track(
                    artist=info['artist'], title=info['title'],
                    album=info['album'], genre=info['genre'],
                    url=info['url'], id=self.selected, arturl=info['arturl'],
                    color=(.7, .7, .7, .8),
                    duration=(info['duration'] if 'duration' in info.keys()
                              else '0:00:00'),
                    is_selected=False)})
                self.info = info['title']
                self.bgimg = info['arturl']
                if self.pop:
                    self.popup.dismiss()
                    self.pop = False
            else:
                reactor.callLater(2,  # @UndefinedVariable
                                  self.on_metadata,
                                  value)

    def on_volume_(self, value):
#         print('volume: %s' % value)
        if int(value) != self.volume:
            self.volume = int(value)

    def on_volume_steps_(self, value):
#         print('volume steps: %s' % value)
        if int(value) != self.volume_steps:
            self.volume_steps = int(value)

    def on_repeat_(self, value):
#         print('repeat: %s' % value)
        if self.repeat != bool(value):
            self.repeat = bool(value)

    def on_shuffle_(self, value):
#         print('shuffle: %s' % value)
        if self.shuffle != bool(value):
            self.shuffle = bool(value)

    def on_track_duration(self, value):
#         print('duration: %s' % value)
        if int(value) != self.duration:
            self.duration = int(value)
            if self._timer:
                self._timer.set(0)

#     def on_server_update(self, update_id):
#         print('update on server: %s' % update_id)

#     def on_server_event(self, instance, value):
#         if 'changed' in value:
# #             print('updated: %s' % value['changed'])
#             if value['changed'] == self.active_server:
# #                 print('update on active server')

    def register_renderer(self, uid):
        if uid != self.active_device:
#             if uid != 'local':
# #                 self.bgimg = 'data/icons/wait2.gif'
            self.lists.update({self.active_device: (self._idarray, self.idlist, self.tracks_info)})
            self.tracks_info = {}
            self._idarray = ''
            self.idlist = []
            self.bgimg = 'data/icons/background_icon2.png'
            self.selected = -1
            self.ids.trackslist.scroll_to(0)
            self.active_device = uid
            if uid == 'local':
                if self.pop:
                    self.popup.dismiss()
#                 print('Local Renderer')
            else:
                if uid in self.lists:
                    self._idarray, self.idlist, self.tracks_info = self.lists[uid]
                    self.popup.dismiss()
                    self.pop = False
#                 if self.realparent.current_device['type'] == 'oh':
                Logger.debug(str(self.controller.parent.devices[uid]['services']))
                for svc in  self.controller.parent.devices[uid]['services'].values():
                    d = None
                    if 'Playlist' in svc['serviceType']:
                        d = self.controller.subscribe(
                            {uid: self.controller.parent.devices[uid]},
                            'urn:av-openhome-org:service:Playlist:1',
                            'IdArray',
                            self.on_idarray)
                        self.controller.subscribe(
                            {uid: self.controller.parent.devices[uid]},
                            'urn:av-openhome-org:service:Playlist:1',
                            'Id',
                            self.on_id)
                        self.controller.subscribe(
                            {uid: self.controller.parent.devices[uid]},
                            'urn:av-openhome-org:service:Playlist:1',
                            'TransportState',
                            self.on_oh_tstate)
                        self.controller.subscribe(
                            {uid: self.controller.parent.devices[uid]},
                            'urn:av-openhome-org:service:Playlist:1',
                            'Shuffle',
                            self.on_shuffle_)
                        self.controller.subscribe(
                            {uid: self.controller.parent.devices[uid]},
                            'urn:av-openhome-org:service:Playlist:1',
                            'Repeat',
                            self.on_repeat_)
                    elif 'Time' in svc['serviceType']:
                        d = self.controller.subscribe(
                            {uid: self.controller.parent.devices[uid]},
                            'urn:av-openhome-org:service:Time:1',
                            'Duration',
                            self.on_track_duration)

                        if not self.controller.cloud:
                            self.controller.subscribe(
                                {uid: self.controller.parent.devices[uid]},
                                'urn:av-openhome-org:service:Time:1',
                                'Seconds',
                                self.on_seconds)
                        
                    elif 'Info' in svc['serviceType']:
                        d = self.controller.subscribe(
                            {uid: self.controller.parent.devices[uid]},
                            'urn:av-openhome-org:service:Info:1',
                            'Metadata',
                            self.on_metadata)
                    elif 'Volume' in svc['serviceType']:
                        d = self.controller.subscribe(
                            {uid: self.controller.parent.devices[uid]},
                            'urn:av-openhome-org:service:Volume:1',
                            'Volume',
                            self.on_volume_)
                        self.controller.subscribe(
                            {uid: self.controller.parent.devices[uid]},
                            'urn:av-openhome-org:service:Volume:1',
                            'VolumeSteps',
                            self.on_volume_steps_)
                    if d:
                        d.addCallbacks(
                            self.register_subscription, lambda ignored: self.popup.dismiss())
#                 self.controller.subscribe(
#                     name, self.renderer_event,
#                     'renderer')
    def register_subscription(self, res):
        if res is None:
            return
        self.subscriptions.append(res)

    def register_server(self, uid):
        if uid != self.active_server:
            self.controller.unsubscribe(self.active_server)
            self.active_server = uid
            if uid == 'ti':
                if len(self.ids.treeLocal.children) == 1:
                    populate_local_tree(
                        self.ids.treeLocal, config.shared_dirs[0])
            else:
                self.server = {uid: self.controller.parent.devices[uid]}
                self.controller.subscribe(
                    {uid: self.controller.parent.devices[uid]},
                    CDS,
                    'SystemUpdateID',
                    self.on_server_update)
                name = self.controller.parent.devices[uid]['name']
                if len(self.trees[name].children) == 1:
                    n = self.trees[name].add_node(TreeViewLabel(text='fake'))
                    n.id = 'fake'
                    n.browsable = False
                    n.populated = False
                    for tree in self.trees:
                        if tree == uid:
                            continue
                        if self.trees[tree].root.is_open:
                            self.trees[tree].toggle_node(self.trees[tree].root)

    def get_tracks_info(self, tracks):
#         print('tracksinfo')
        def got_info(res, tracks):
#             print('res from server')

            if isinstance(tracks, int):
#                 print(res.Metadata)
                info = didl_decode(res.Metadata)
                if len(info) > 1:
                    print('bad response')
                    return
                info = info[0]
#                 print(info)
                info = update_trackinfo(info)
                if tracks in self.tracks_info:
                    col = self.tracks_info[tracks].color
                else:
                    col = (.5, .5, .5, .5)
                self.tracks_info.update({tracks: Track(
                    artist=info['artist'], title=info['title'],
                    album=info['album'], genre=info['genre'],
                    url=info['url'], id=tracks, arturl=info['arturl'],
                    color=col, duration=info['duration'],
                    is_selected=False)})
                if tracks == self.selected:
                    self.info = info['title']
                    self.bgimg = info['arturl']
            else:
#                 print(res)
#                 print(res.decode('utf-8'))
#                 root = et.XML(res.decode('utf-8'))
                try:
                    root = et.fromstring(res)
                except Exception as e:
                    print('bad data from server %s' % e)
                    root = et.fromstring(res.encode('utf-8', errors='ignore'))
                dic = XmlDictConfig(root)
#                 print(dic)
                try:
                    tl = dic['Entry']
                except KeyError:
                    print('bad response from renderer: %s' % res)
                else:
                    if len(tl) != len(tracks):
                        print(
                            'server returned %d result instead of %d'
                            % (len(tl), len(tracks)))
                    for track in tl:
                        Id = int(track['Id'])
                        info = didl_decode(
                            track['Metadata'].encode('utf-8'))[0]
                        info = update_trackinfo(info)
#                         print(info)
                        if Id in self.tracks_info:
                            col = self.tracks_info[Id].color
                        else:
                            col = (.5, .5, .5, .5)
                        self.tracks_info.update({Id: Track(
                            artist=info['artist'], title=info['title'],
                            album=info['album'], genre=info['genre'],
                            url=info['url'], id=Id, arturl=info['arturl'],
                            color=col, duration=(
                                info['duration'] if 'duration' in info
                                else '00:00:00'),
                            is_selected=False)})
                        if Id == self.selected:
                            self.info = info['title']
                            self.bgimg = info['arturl']
#                         self.lasttrack = Id
                if self.pop:
                    self.popup.dismiss()
                    self.pop = False

        if len(tracks) == 1:
            d = self.controller.call(
                self.device, PLAYLIST,
                'Read', str(tracks[0]))
            d.addCallback(got_info, tracks[0])
        else:
            d = self.controller.call(
                self.device, PLAYLIST,
                'ReadList', ' '.join(str(tr) for tr in tracks))
            d.addCallback(got_info, tracks)
        return d

    def generate_empty_dict(self, l):
        t = Track(artist='', title='updating...', album='', genre='',
                  url='', id=0, arturl='data/image-loading.gif',
                  color=(.5, .5, .5, .5), duration='0:00:00',
                  is_selected=False)
        self.tracks_info.update({i: t for i in l})

    def update_tracklist(self, idarray):
        def updated(res, l):
#             print('track_list updated')
            self.pending.remove('tracksinfo')
            if self.selected > -1:
                i = l.index(self.selected)
                if i > 3:
                    self.ids.trackslist.scroll_to(i-3)
                else:
                    self.ids.trackslist.scroll_to(0)
        #  print('update: %s' % idarray)
        if 'tracksinfo' in self.pending:
#             print('cancelled')
            return
        #  print('ok')
        self.pending.append('tracksinfo')
        if len(idarray) > 3:
            nl = id_array_decode(idarray)
            if self._idarray == '':
                self.generate_empty_dict(nl)
            self._idarray = idarray
            s = set(nl)
            removelist = [i for i in self.idlist if i not in s]
            querylist = sorted(list(s.difference(self.idlist)))
            self.idlist = nl
            for t in removelist:
                try:
                    del self.tracks_info[t]
                except KeyError:
                    continue
            if len(querylist) > 11:
                dlist = []
                newlist = []
                for trackid in querylist:
                    newlist.append(trackid)
                    if len(newlist) % 12 == 0:
                        dlist.append(self.get_tracks_info(newlist))
                        newlist = []
                if len(newlist) > 0:
                    dlist.append(self.get_tracks_info(newlist))
                d = defer.DeferredList(dlist)
            else:
                d = self.get_tracks_info(querylist)
            d.addBoth(updated, nl)
        else:
            self.idlist = []

    def append_track(self, url, md):
        def appended(res):
#             print('appended: %s, id: %s' % (url, res))
            return res
        d = self.controller.call(
            self.device, PLAYLIST,
            'Insert', (str(self.lasttrack), url, md.decode('utf-8')))
        d.addCallback(appended)
        return d
#         self.track_list.append(url)

    def replace_tracks(self, url, md):
#         print('replace: %s' % url)
        d = self.controller.call(
            self.device, PLAYLIST,
            'DeleteAll')
        d.addCallback(
            lambda ignored: self.append_track(url, md))
        d.addCallback(self.play_id)
        return d

    def play_id(self, trackid):
#         print('play %s' % trackid)
        d = self.controller.call(
            self.device,
            PLAYLIST,
            'SeekId', str(trackid))
        self.on_id(trackid)
        return d

    def play(self):
        d = self.controller.call(
            self.device, PLAYLIST,
            'Play')
        return d

    def pause(self):
        d = self.controller.call(
            self.device, PLAYLIST,
            'Pause')
        return d

    def playpause(self):
        if self.playing:
            return self.pause()
        else:
            return self.play()

    def next(self):
        d = self.controller.call(
            self.device,
            PLAYLIST,
            'Next')
        return d

    def previous(self):
        d = self.controller.call(
            self.device,
            PLAYLIST,
            'Previous')
        return d

    def seek(self, pos):

        if self.device:
            #  print('seek to %s' % pos)
            d = self.controller.call(
                self.device,
                PLAYLIST,
                'SeekSecondAbsolute',
                int(pos))
            return d

    def remove_track(self, trackid):
        d = self.controller.call(
            self.device, PLAYLIST,
            'DeleteId', trackid)
        return d

    def volpopup(self):
        popup = VolPopUp(media=self)
#         popup.parent = self
        popup.open()

    def volup(self):
        d = self.controller.call(
            self.device, VOLUME,
            'VolumeInc')
        return d

    def voldown(self):
        d = self.controller.call(
            self.device, VOLUME,
            'VolumeDec')
        return d

    def setvol(self, value):
        self.desired_vol = value
        if not self.vol_scheduled:
            self.vol_scheduled = True
            Clock.schedule_once(self.remote_set_vol, .5)

    def remote_set_vol(self, ignored):
        self.vol_scheduled = False
        d = self.controller.call(
            self.device, VOLUME,
            'SetVolume', str(self.desired_vol))
        return d
        

    def call(self, fct, trackid):
        if fct == 'play':
            self.play_id(trackid)
        elif fct == 'remove':
            self.remove_track(trackid)
        else:
            print(fct, trackid)


class ButtonPlayPause(Image):
    state = BooleanProperty(False)
    play = ObjectProperty(None)
    source = StringProperty(
        'atlas://data/images/defaulttheme/media-playback-start')

    def on_touch_down(self, touch):
        '''.. versionchanged:: 1.4.0'''
        if self.collide_point(*touch.pos):
            self.state = not self.state
            return self.play()
            return True

    def on_state(self, instance, state):
        if state:
            self.source = 'atlas://data/images/defaulttheme/'\
                + 'media-playback-pause'
        else:
            self.source = 'atlas://data/images/defaulttheme/'\
                + 'media-playback-start'
        self.state = state


class ButtonRepeat(Image):
    state = BooleanProperty(False)
    media = ObjectProperty(None)
    source = StringProperty('data/icons/repeat_disabled.png')

    def on_touch_down(self, touch):
        '''.. versionchanged:: 1.4.0'''
        if self.collide_point(*touch.pos):
            self.state = not self.state
            if self.state:
                self.media.controller.call(
                    self.media.device,
                    PLAYLIST,
                    'SetRepeat',
                    True)
            else:
                self.media.controller.call(
                    self.media.device,
                    PLAYLIST,
                    'SetRepeat',
                    False)
            return True

    def on_state(self, instance, state):
        if state:
            self.source = 'data/icons/repeat_enabled.png'
        else:
            self.source = 'data/icons/repeat_disabled.png'
        self.state = state


class ButtonShuffle(Image):
    state = BooleanProperty(False)
    media = ObjectProperty(None)
    source = StringProperty('data/icons/shuffle_disabled.png')

    def on_touch_down(self, touch):
        '''.. versionchanged:: 1.4.0'''
        if self.collide_point(*touch.pos):
            self.state = not self.state
            if self.state:
                self.media.controller.call(
                    self.media.device,
                    PLAYLIST,
                    'SetShuffle',
                    True)
            else:
                self.media.controller.call(
                    self.media.device,
                    PLAYLIST,
                    'SetShuffle',
                    False)
            return True

    def on_state(self, instance, state):
        if state:
            self.source = 'data/icons/shuffle_enabled.png'
        else:
            self.source = 'data/icons/shuffle_disabled.png'
        self.state = state


class ButtonNext(Image):
    next = ObjectProperty(None)

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self.next()
            return True


class ButtonPrev(Image):
    previous = ObjectProperty(None)

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self.previous()
            return True


class ButtonVolume(Image):
    popup = ObjectProperty(None)
    volume = NumericProperty(0)
    max_vol = NumericProperty(0)
    source = StringProperty(
        'atlas://data/images/defaulttheme/audio-volume-low')

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self.popup()
            return True

#     def on_max_vol(self, instance, value):
#         print('vol max: %s' % value)

    def on_volume(self, instance, volume):
#         print(self.max_vol)
        if volume < self.max_vol/3:
            self.source = 'atlas://data/images/defaulttheme/audio-volume-low'
        elif volume < self.max_vol * 0.66:
            self.source = 'atlas://data/images/defaulttheme/audio-volume-medium'
        else:
            self.source = 'atlas://data/images/defaulttheme/audio-volume-high'


class TreeViewMedia(BoxLayout, TreeViewNode):
    text = StringProperty()
    img = StringProperty()
    metadata = StringProperty()


class TrackListDropDown(DropDown):
    pass

class TrackListPopUp(BoxLayout):
    button = ObjectProperty()


class TrackListBubble(Bubble):

    def __init__(self, pos, size, **kwargs):
        super(TrackListBubble, self).__init__(**kwargs)
        width = dp(size/5)
        self.pos = (pos[0] + size - width, pos[1] + dp(40))
        self.size = (width, dp(80))


class WaitingPopup(ModalView):
    img = ObjectProperty(None)
#     img = Image(source='data/icons/wait2.gif')


class MyLib(ListItemButton):
    selected_color = ListProperty([1., 0., 0., 1])
    deselected_color = ListProperty([.5, .5, .5, .3])
#     size_hint: (None, .15)
    fake = BooleanProperty(False)
    img = StringProperty('data/image-loading.gif')
    title = StringProperty('')
    artist = StringProperty('')
    trackid = NumericProperty(0)
    menu_open = False
    scheduled = None

    def __init__(self, *args, **kwargs):
#         kwargs.update({'always_release': False})
        super(MyLib, self).__init__(*args, **kwargs)
        self.bind(on_release=self.release)

    def select(self, *args, **kwargs):
        self.is_selected = True
        return True

    def release(self, *args, **kwargs):
#         print('release')
        if self.scheduled:
            self.scheduled.cancel()
            self.scheduled = None

    def on_touch_down(self, touch):

        if self.collide_point(*touch.pos):
            self.scheduled = Clock.schedule_once(self.show_menu, 1)
            super(MyLib, self).on_touch_down(touch)


#     def on_touch_down(self, touch):
#         if super(MyLib, self).on_touch_down(touch):
#             return
#         if self.collide_point(*touch.pos):
#             return
#         if self.menu_open:
#             self.menu.dismiss()
#             self.menu_open = False
#             return True

    def show_menu(self, *args, **kwargs):
        self.scheduled = None
        callback = self.close_menu
        Clock.schedule_once(callback, 5)
#         if not hasattr(self, 'menu'):
#         self.menu = menu = TrackListDropDown()
        self.menu = menu = Popup(
            content=TrackListPopUp(button=self),
            title=self.title,
            size_hint=(.2, .3))
#         self.add_widget(menu)
        menu.open()
#         menu.open(self)
#         else:
#             self.menu.open(self)
        self.menu_open = True
    
    def define_size(self, size):
        print(size)
        if size[0] < 120:
            print('resize1 !')
            self.menu.size_hint = self.menu.size_hint[0] * 1.5,\
                self.menu.size_hint[1] * 1.5


    def close_menu(self, ignored):
#         print('close %s' % ignored)
#         print(self.menu_open)
        if self.menu_open:
            self.menu_open = False
            self.menu.dismiss()


class ArtistImage(AsyncImage):
    pass


class ArtistImageTree(AsyncImage):
    pass


class ServerItem(TabbedPanelItem):
    pass

class VolPopUp(Popup):
    media = ObjectProperty()

class AnimatedTextButton(Button):
    _label = ObjectProperty(None)
    sometext = StringProperty('')
    current = None

    def animate_play(self):
        if self.current:
            self.current.stop(self._label)
#         left = Animation(x=0)
#         right = Animation(center_x=self.width, duration=4.)
#         anim = left + right
#         anim.repeat = True
#         anim.start(self._label)
#         self.current = anim

    def animate_pause(self):
        if self.current:
            self.current.stop(self._label)
        left = Animation(x=self.width/2 - self._label.width/2)
        left.bind(on_complete=self.blink)
        right = Animation(x=self.width/2 - self._label.width/2, duration=.1)
        anim = left + right
        anim.repeat = True
        anim.start(self._label)
        self.current = anim
        
    def animate_stop(self):
        if self.current:
            self.current.repeat = False
            self.current.stop(self._label)
            self.current = None
            self._label.text = self.sometext
            self._label.x = self.width/2 - self._label.width/2

    def blink(self, *args, **kwargs):
        if self._label.text == '':
            self._label.text = self.sometext
        else:
            self._label.text = ''


class Timer(object):
    seconds = 0
    running = False

    def __init__(self, clbk):
        self.callback = clbk
        self.seconds = 0
        self.running = False
#         reactor.callLater(5, self.event)  # @UndefinedVariable

    def set(self, value):
        self.seconds = int(value)
        if not self.running:
            self.callback(self.seconds)

    def start(self):
#         print('start')
        self.running = True
        reactor.callLater(1, self.event)  # @UndefinedVariable

    def stop(self):
#         print('stop')
        self.running = False

    def event(self):
        # print(self.seconds)
        if self.running:
            self.seconds += 1
            self.callback(self.seconds)
            reactor.callLater(1, self.event)  # @UndefinedVariable

def update_trackinfo(d):
#     print(d)
    if 'class' in d:
            if 'audio' in d['class']:
                cat = 'audio'
                img = 'data/icons/audio.png'
            elif 'video' in d['class']:
                cat = 'video'
                img = 'data/icons/movie.png'
            else:
                cat = 'none'
                img = 'data/icons/icon.png'
    else:
        img = 'data/icons/icon.png'
    if 'albumArtURI' in d:
        if isinstance(d['albumArtURI'], str):
            img = d['albumArtURI']
        elif 'text' in d['albumArtURI']:
                img = d['albumArtURI']['text']
    elif 'res1' in d:
        if 'image' in d['res1']['protocolInfo']:
            img = d['res1']['text']
    d.update({
        'arturl': img,
        'artist': (d['artist'] if 'artist' in d and cat == 'audio' else ''),
        'album': (d['album'] if 'album' in d else ''),
        'genre': (d['genre'] if 'genre' in d else '')})
    return d


def get_titles(res):
    t = []
    if res.Result:
        for r in didl_decode(res.Result.encode('utf-8')):
            browsable = False
            if 'object.container' in r['class']:
                if 'childCount' in r:
                    if int(r['childCount']) < 1:
                        continue
#                 browsable = True
                node = TreeViewLabel(
                    text=r['title'][:32],
                    id=r['id'])
                node.browsable = True
                node.populated = False
            else:
                img = None
                if 'albumArtURI' in r:
                    if 'text' in r['albumArtURI']:
                        img = r['albumArtURI']['text']
                if not img:
                    if 'res1' in r:
                        if 'image' in r['res1']['protocolInfo']:
                            img = r['res1']['text']
                if not img:
                    if 'video' in r['class']:
                        img = 'data/icons/movie.png'
                    elif 'audio' in r['class']:
                        img = 'data/icons/audio.png'
                    else:
                        img = 'data/icons/icon.png'
                node = TreeViewMedia(
                    text=r['title'][:32])
                node.img = img
                node.url = r['url']
                node.metadata = r['metadata']
                node.browsable = False
                node.populated = True
            t.append(node)
    return t


def populate_tree(nodes, rootnode, parent=None):
        if parent is not None:
            for node in nodes:
                new = rootnode.add_node(node, parent)
                new.id = node.id
                new.browsable = node.browsable
                new.populated = node.populated
                if new.browsable:
                    rootnode.add_node(TreeViewLabel(text='fake'), new)
        else:
            for node in nodes:
                new = rootnode.add_node(node)
                new.id = node.id
                new.browsable = node.browsable
                new.populated = node.populated
                if new.browsable:
                    rootnode.add_node(TreeViewLabel(text='fake'), new)


def populate_local_tree(node, path):
    filedict = {}
    tree = collections.OrderedDict()
    for root, dirs, files in os.walk(path.encode('utf-8')):
        if root.startswith('.') or '/.' in root:
            continue
        show = False
        top = False
        for name in files:
            t = guess_type(name)[0]
#             print(t)
            if t:
                if 'audio' in t or 'video' in t:
                    root = root.strip('/')
#                     print(root + '/' + name)
                    if root in filedict:
                        filedict[root].append(root + '/' + name)
                    else:
                        filedict.update({root: [root + '/' + name]})
                    show = True
        if show:
            path = path.strip('/')
#             print('folder: %s' % root)
            if root == path:
#                 print('top')
                top = True
            r = root.split('/')
            for i, name in enumerate(r):
                p = '/'.join(r[:i+1])
                try:
                    parent = tree[i-1][root.split('/')[i-1]][p[:-(len(
                        name)+1)]]
                except KeyError:
                    parent = None
                if i in tree:
                    if name in tree[i]:
                        if p in tree[i][name]:
                            continue
                        else:
                            new = node.add_node(
                                TreeViewLabel(text=name, is_open=False),
                                parent)
                            tree[i][name].update({p: new})
                    else:
                        if name == root.split('/')[-1]:
                            if parent is not None:
                                new = node.add_node(
                                    TreeViewLabel(
                                        text=name,
                                        is_open=False),
                                    parent)
                            else:
                                new = node.add_node(
                                    TreeViewLabel(
                                        text=name,
                                        is_open=False))
                            tree[i].update({name: {p: new}})
                            for f in filedict[root]:
                                nf = node.add_node(
                                    TreeViewLabel(text=f.split('/')[-1]), new)
                                nf.filepath = f
                        else:
                            if top:
                                tree[i].update({name: {p: None}})
                                continue
                            new = node.add_node(
                                TreeViewLabel(text=name, is_open=False),
                                parent)
                            tree[i].update({name: {p: new}})
#                             print('append to dict: %s %s' % (name, tree[i]))
                else:
                    if name == root.split('/')[-1]:
                        if parent is not None:
                            new = node.add_node(
                                TreeViewLabel(
                                    text=name,
                                    is_open=False),
                                parent)
                        else:
                            new = node.add_node(
                                TreeViewLabel(
                                    text=name,
                                    is_open=False))
                        tree[i] = {name: {p: new}}
#                         print('append to dict: %s %s' % (name, tree[i]))
                        if top:
                            tree['root'] = new
                            continue
                        for f in filedict[root]:
                            nf = node.add_node(
                                TreeViewLabel(text=f.split('/')[-1]), new)
                            nf.filepath = f
#                             print('level: %s - %s' %(i, f))
                    else:
                        if top:
                            tree[i] = {name: {p: None}}
#                             print('append to dict: %s %s' % (i, name))
                            continue
                        new = node.add_node(
                            TreeViewLabel(
                                text=name, is_open=False), parent)
#                         print('append to dict: %s %s' % (i, name))
                        tree[i] = {name: {p: new}}
    for f in filedict[path.strip('/')]:
        nf = node.add_node(
            TreeViewLabel(text=f.split('/')[-1]), tree['root'])
        nf.filepath = f

        