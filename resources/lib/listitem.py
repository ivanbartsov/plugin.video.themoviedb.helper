import xbmc
import xbmcgui
import resources.lib.utils as utils
from resources.lib.plugin import ADDONPATH, PLUGINPATH
from resources.lib.tmdb import TMDb


class ListItem(object):
    def __init__(
            self, label=None, label2=None, path=None, library=None, is_folder=True, params=None, next_page=None,
            parent_params=None, kodi_db=None, infolabels=None, infoproperties=None, art=None, cast=None,
            context_menu=None, stream_details=None, unique_ids=None,
            **kwargs):
        self.label = label or ''
        self.label2 = label2 or ''
        self.path = path or PLUGINPATH
        self.params = params or {}
        self.parent_params = parent_params or {}
        self.library = library or 'video'
        self.is_folder = is_folder
        self.infolabels = infolabels or {}
        self.infoproperties = infoproperties or {}
        self.art = art or {}
        self.cast = cast or []
        self.context_menu = context_menu or []
        self.stream_details = stream_details or {}
        self.unique_ids = unique_ids or {}
        self.kodi_db = kodi_db
        self.set_as_next_page(next_page)

    def set_as_next_page(self, next_page=None):
        if not next_page:
            return
        self.label = xbmc.getLocalizedString(33078)
        self.art['thumb'] = '{}/resources/icons/tmdb/nextpage.png'.format(ADDONPATH)
        self.infoproperties['specialsort'] = 'bottom'
        self.params = self.parent_params.copy()
        self.params['page'] = next_page
        self.params.pop('update_listing', None)  # Just in case we updated the listing for search results
        self.path = PLUGINPATH
        self.is_folder = True

    def set_art_fallbacks(self):
        if not self.art.get('thumb'):
            self.art['thumb'] = '{}/resources/poster.png'.format(ADDONPATH)
        if not self.art.get('fanart'):
            self.art['fanart'] = '{}/fanart.jpg'.format(ADDONPATH)
        return self.art

    def get_kodi_dbid(self):
        if not self.kodi_db:
            return
        dbid = self.kodi_db.get_info(
            info='dbid',
            imdb_id=self.unique_ids.get('imdb'),
            tmdb_id=self.unique_ids.get('tmdb'),
            tvdb_id=self.unique_ids.get('tvdb'),
            originaltitle=self.infolabels.get('originaltitle'),
            title=self.infolabels.get('title'),
            year=self.infolabels.get('year'))
        if dbid:
            self.infolabels['dbid'] = dbid

    def get_details(self, cache_only=True):
        tmdb_type = self.infoproperties.get('tmdb_type')
        tmdb_id = self.infoproperties.get('tmdb_id')
        if not tmdb_type or not tmdb_id:
            return
        details = TMDb().get_details(tmdb_type, tmdb_id, cache_only=cache_only)
        if not details:
            return
        self.infolabels = utils.merge_two_dicts(details.get('infolabels', {}), self.infolabels)
        self.infoproperties = utils.merge_two_dicts(details.get('infoproperties', {}), self.infoproperties)
        self.art = utils.merge_two_dicts(details.get('art', {}), self.art)
        self.cast = self.cast or details.get('cast', [])

    def get_url(self):
        paramstring = '?{}'.format(utils.urlencode_params(**self.params)) if self.params else ''
        return '{}{}'.format(self.path, paramstring)

    def get_listitem(self):
        listitem = xbmcgui.ListItem(label=self.label, label2=self.label2, path=self.get_url())
        listitem.setLabel2(self.label2)
        listitem.setUniqueIDs(self.unique_ids)
        listitem.setInfo(self.library, self.infolabels)
        listitem.setProperties(self.infoproperties)
        listitem.setArt(self.set_art_fallbacks())
        listitem.setCast(self.cast)
        listitem.addContextMenuItems(self.context_menu)

        if self.stream_details:
            for k, v in self.stream_details.items():
                if not k or not v:
                    continue
                for i in v:
                    if not i:
                        continue
                    listitem.addStreamInfo(k, i)

        return listitem
