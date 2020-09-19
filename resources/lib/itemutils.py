import resources.lib.rpc as rpc
import resources.lib.utils as utils
from resources.lib.traktapi import TraktAPI
from resources.lib.tmdb import TMDb


class ItemUtils(object):
    def __init__(self, ftv_api=None, kodi_db=None):
        self.trakt_watched_movies = {}
        self.trakt_watched_tvshows = {}
        self.ftv_api = ftv_api
        self.kodi_db = kodi_db
        self.trakt_api = TraktAPI()
        self.tmdb_api = TMDb()

    def set_trakt_watched(self):
        self.trakt_watched_movies = self.get_trakt_watched('movies')
        self.trakt_watched_tvshows = self.get_trakt_watched('tvshows')

    def get_trakt_watched(self, container_content):
        if container_content == 'movies':
            return self.trakt_api.get_sync_watched('movie', quick_list=True) or {}
        if container_content in ['tvshows', 'seasons', 'episodes']:
            return self.trakt_api.get_sync_watched('show', quick_list=True) or {}
        return {}

    def get_ftv_details(self, listitem):
        """ merges art with fanarttv art - must pass through fanarttv api object """
        if not self.ftv_api:
            return
        return {'art': self.ftv_api.get_all_artwork(listitem.get_ftv_id(), listitem.get_ftv_type())}

    def get_external_ids(self, listitem):
        unique_id = None
        trakt_type = None
        if listitem.infolabels.get('mediatype') == 'movie':
            unique_id = listitem.unique_ids.get('tmdb')
            trakt_type = 'movie'
        elif listitem.infolabels.get('mediatype') == 'tvshow':
            unique_id = listitem.unique_ids.get('tmdb')
            trakt_type = 'show'
        elif listitem.infolabels.get('mediatype') in ['season', 'episode']:
            unique_id = listitem.unique_ids.get('tvshow.tmdb')
            trakt_type = 'show'
        if not unique_id or not trakt_type:
            return
        return {'unique_ids': {
            'trakt': self.trakt_api.get_id(id_type='tmdb', unique_id=unique_id, trakt_type=trakt_type, output_type='trakt'),
            'slug': self.trakt_api.get_id(id_type='tmdb', unique_id=unique_id, trakt_type=trakt_type, output_type='slug'),
            'imdb': self.trakt_api.get_id(id_type='tmdb', unique_id=unique_id, trakt_type=trakt_type, output_type='imdb'),
            'tvdb': self.trakt_api.get_id(id_type='tmdb', unique_id=unique_id, trakt_type=trakt_type, output_type='tvdb')}}

    def get_tmdb_details(self, listitem, cache_only=True):
        return TMDb().get_details(
            tmdb_type=listitem.get_tmdb_type(),
            tmdb_id=listitem.unique_ids.get('tmdb'),
            season=listitem.infolabels.get('season') if listitem.infolabels.get('mediatype') in ['season', 'episode'] else None,
            episode=listitem.infolabels.get('episode') if listitem.infolabels.get('mediatype') == 'episode' else None,
            cache_only=cache_only)

    def get_kodi_dbid(self, listitem):
        if not self.kodi_db:
            return
        dbid = self.kodi_db.get_info(
            info='dbid',
            imdb_id=listitem.unique_ids.get('imdb'),
            tmdb_id=listitem.unique_ids.get('tmdb'),
            tvdb_id=listitem.unique_ids.get('tvdb'),
            originaltitle=listitem.infolabels.get('originaltitle'),
            title=listitem.infolabels.get('title'),
            year=listitem.infolabels.get('year'))
        return dbid

    def get_kodi_details(self, listitem):
        dbid = self.get_kodi_dbid(listitem)
        if not dbid:
            return
        if listitem.infolabels.get('mediatype') == 'movie':
            return rpc.get_movie_details(dbid)
        elif listitem.infolabels.get('mediatype') == 'tv':
            return rpc.get_tvshow_details(dbid)
        # TODO: Add episode details need to also merge TV

    def get_episode_playcount(self, seasons, season=None, episode=None):
        for i in seasons:
            if i.get('number', -1) != season:
                continue
            for j in i.get('episodes', []):
                if j.get('number', -1) == episode:
                    return j.get('plays', 1)

    def get_episode_watchedcount(self, seasons, season=None):
        count = 0
        for i in seasons:
            if season and i.get('number', -1) != season:
                continue
            count += len(i.get('episodes', []))
        return count

    def get_playcount_from_trakt(self, listitem):
        if listitem.infolabels.get('mediatype') == 'movie':
            tmdb_id = utils.try_parse_int(listitem.unique_ids.get('tmdb'))
            return self.trakt_watched_movies.get(tmdb_id, {}).get('plays')
        if listitem.infolabels.get('mediatype') == 'episode':
            tmdb_id = utils.try_parse_int(listitem.unique_ids.get('tvshow.tmdb'))
            return self.get_episode_playcount(
                seasons=self.trakt_watched_tvshows.get(tmdb_id, {}).get('seasons', []),
                season=listitem.infolabels.get('season') or -2,
                episode=listitem.infolabels.get('episode') or -2)
        if listitem.infolabels.get('mediatype') == 'tvshow':
            tmdb_id = utils.try_parse_int(listitem.unique_ids.get('tmdb'))
            return self.get_episode_watchedcount(
                seasons=self.trakt_watched_tvshows.get(tmdb_id, {}).get('seasons', []))
        if listitem.infolabels.get('mediatype') == 'season':
            tmdb_id = utils.try_parse_int(listitem.unique_ids.get('tvshow.tmdb'))
            return self.get_episode_watchedcount(
                seasons=self.trakt_watched_tvshows.get(tmdb_id, {}).get('seasons', []),
                season=listitem.infolabels.get('season') or -2)
