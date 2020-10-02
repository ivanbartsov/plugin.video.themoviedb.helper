import xbmcgui
import requests
import resources.lib.utils as utils
import xml.etree.ElementTree as ET
import resources.lib.cache as cache


class RequestAPI(object):
    def __init__(self, cache_short=None, cache_long=None, req_api_url=None, req_api_key=None, req_api_name=None, timeout=None):
        self.req_api_url = req_api_url or ''
        self.req_api_key = req_api_key or ''
        self.req_api_name = req_api_name or ''
        self.req_connect_err_prop = 'TMDbHelper.ConnectionError.{}'.format(self.req_api_name)
        self.req_connect_err = utils.try_parse_float(xbmcgui.Window(10000).getProperty(self.req_connect_err_prop)) or 0
        self.cache_long = 14 if not cache_long or cache_long < 14 else cache_long
        self.cache_short = 1 if not cache_short or cache_short < 1 else cache_short
        self.headers = None
        self.timeout = timeout or 10

    def translate_xml(self, request):
        if request:
            request = ET.fromstring(request.content)
            request = utils.dictify(request)
        return request

    def get_api_request_json(self, request=None, postdata=None, headers=None):
        request = self.get_api_request(request=request, postdata=postdata, headers=headers)
        return request.json() if request else {}

    def get_simple_api_request(self, request=None, postdata=None, headers=None):
        try:
            if not postdata:
                return requests.get(request, headers=headers, timeout=self.timeout)
            return requests.post(request, data=postdata, headers=headers)
        except Exception as err:
            self.req_connect_err = utils.set_timestamp()
            xbmcgui.Window(10000).setProperty(self.req_connect_err_prop, str(self.req_connect_err))
            utils.kodi_log(u'ConnectionError: {}\nSuppressing retries for 1 minute'.format(err), 1)

    def get_api_request(self, request=None, postdata=None, headers=None):
        """
        Make the request to the API by passing a url request string
        """
        # Connection error in last minute for this api so don't keep trying
        if utils.get_timestamp(self.req_connect_err):
            return

        # Get response
        response = self.get_simple_api_request(request, postdata, headers)
        if not response:
            return

        # Some error checking
        if not response.status_code == requests.codes.ok and utils.try_parse_int(response.status_code) >= 400:  # Error Checking
            if response.status_code == 401:  # Invalid API Key
                utils.kodi_log(u'HTTP Error Code: {0}\nRequest: {1}\nPostdata: {2}\nHeaders: {3}\nResponse: {4}'.format(response.status_code, request, postdata, headers, response), 1)
            elif response.status_code == 500:
                self.req_connect_err = utils.set_timestamp()
                xbmcgui.Window(10000).setProperty(self.req_connect_err_prop, str(self.req_connect_err))
                utils.kodi_log(u'HTTP Error Code: {0}\nRequest: {1}\nSuppressing retries for 1 minute'.format(response.status_code, request), 1)
            elif utils.try_parse_int(response.status_code) > 400:  # Don't write 400 error to log
                utils.kodi_log(u'HTTP Error Code: {0}\nRequest: {1}'.format(response.status_code, request), 1)
            return

        # Return our response
        return response

    def get_request_url(self, *args, **kwargs):
        """
        Creates a url request string:
        https://api.themoviedb.org/3/arg1/arg2?api_key=foo&kwparamkey=kwparamvalue
        """
        request = self.req_api_url
        for arg in args:
            if arg:  # Don't add empty args
                request = u'{0}/{1}'.format(request, arg)
        sep = '?' if '?' not in request else '&'
        request = u'{0}{1}{2}'.format(request, sep, self.req_api_key) if self.req_api_key else request
        for key, value in kwargs.items():
            if value:  # Don't add empty kwargs
                sep = '?' if '?' not in request else ''
                request = u'{0}{1}&{2}={3}'.format(request, sep, key, value)
        return request

    def get_request_sc(self, *args, **kwargs):
        """ Get API request using the short cache """
        kwargs['cache_days'] = self.cache_short
        return self.get_request(*args, **kwargs)

    def get_request_lc(self, *args, **kwargs):
        """ Get API request using the long cache """
        kwargs['cache_days'] = self.cache_long
        return self.get_request(*args, **kwargs)

    def get_request(self, *args, **kwargs):
        """ Get API request from cache (or online if no cached version) """
        cache_days = kwargs.pop('cache_days', 0)  # Number of days to cache retrieved object if not already in cache.
        cache_name = kwargs.pop('cache_name', '')  # Affix to standard cache name.
        cache_only = kwargs.pop('cache_only', False)  # Only retrieve object from cache.
        cache_force = kwargs.pop('cache_force', False)  # Force retrieved object to be saved in cache. Use int to specify cache_days for fallback object.
        cache_fallback = kwargs.pop('cache_fallback', False)  # Object to force cache if no object retrieved.
        cache_refresh = kwargs.pop('cache_refresh', False)  # Ignore cached timestamps and retrieve new object.
        cache_combine_name = kwargs.pop('cache_combine_name', False)  # Combine given cache_name with auto naming via args/kwargs
        headers = kwargs.pop('headers', None) or self.headers  # Optional override to default headers.
        postdata = kwargs.pop('postdata', None)  # Postdata if need to POST to a RESTful API.
        request_url = self.get_request_url(*args, **kwargs)
        return cache.use_cache(
            self.get_api_request_json, request_url,
            headers=headers,
            postdata=postdata,
            cache_refresh=cache_refresh,
            cache_days=cache_days,
            cache_name=cache_name,
            cache_only=cache_only,
            cache_force=cache_force,
            cache_fallback=cache_fallback,
            cache_combine_name=cache_combine_name)
