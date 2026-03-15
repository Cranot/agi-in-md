# From: https://github.com/psf/requests/blob/main/src/requests/sessions.py
# The core of the most-downloaded Python package (requests library)
# Stripped docstrings for brevity. Full file is 834 lines.

import os, sys, time
from collections import OrderedDict
from datetime import timedelta

class SessionRedirectMixin:
    def get_redirect_target(self, resp):
        if resp.is_redirect:
            location = resp.headers["location"]
            location = location.encode("latin1")
            return to_native_string(location, "utf8")
        return None

    def should_strip_auth(self, old_url, new_url):
        old_parsed = urlparse(old_url)
        new_parsed = urlparse(new_url)
        if old_parsed.hostname != new_parsed.hostname:
            return True
        if (old_parsed.scheme == "http" and old_parsed.port in (80, None)
            and new_parsed.scheme == "https" and new_parsed.port in (443, None)):
            return False
        changed_port = old_parsed.port != new_parsed.port
        changed_scheme = old_parsed.scheme != new_parsed.scheme
        default_port = (DEFAULT_PORTS.get(old_parsed.scheme, None), None)
        if (not changed_scheme and old_parsed.port in default_port
            and new_parsed.port in default_port):
            return False
        return changed_port or changed_scheme

    def resolve_redirects(self, resp, req, stream=False, timeout=None,
                          verify=True, cert=None, proxies=None,
                          yield_requests=False, **adapter_kwargs):
        hist = []
        url = self.get_redirect_target(resp)
        previous_fragment = urlparse(req.url).fragment
        while url:
            prepared_request = req.copy()
            hist.append(resp)
            resp.history = hist[1:]
            try:
                resp.content
            except (ChunkedEncodingError, ContentDecodingError, RuntimeError):
                resp.raw.read(decode_content=False)
            if len(resp.history) >= self.max_redirects:
                raise TooManyRedirects(f"Exceeded {self.max_redirects} redirects.", response=resp)
            resp.close()
            if url.startswith("//"):
                parsed_rurl = urlparse(resp.url)
                url = ":".join([to_native_string(parsed_rurl.scheme), url])
            parsed = urlparse(url)
            if parsed.fragment == "" and previous_fragment:
                parsed = parsed._replace(fragment=previous_fragment)
            elif parsed.fragment:
                previous_fragment = parsed.fragment
            url = parsed.geturl()
            if not parsed.netloc:
                url = urljoin(resp.url, requote_uri(url))
            else:
                url = requote_uri(url)
            prepared_request.url = to_native_string(url)
            if resp.status_code not in (codes.temporary_redirect, codes.permanent_redirect):
                purged_headers = ("Content-Length", "Content-Type", "Transfer-Encoding")
                for header in purged_headers:
                    prepared_request.headers.pop(header, None)
                prepared_request.body = None
            headers = prepared_request.headers
            try:
                del headers["Cookie"]
            except KeyError:
                pass
            extract_cookies_to_jar(prepared_request._cookies, req, resp.raw)
            merge_cookies(prepared_request._cookies, self.cookies)
            prepared_request.prepare_cookies(prepared_request._cookies)
            proxies = self.rebuild_proxies(prepared_request, proxies)
            self.rebuild_auth(prepared_request, resp)
            rewind_body(prepared_request)
            req = prepared_request
            if yield_requests:
                yield req
            else:
                resp = self.send(prepared_request, stream=stream, timeout=timeout,
                                verify=verify, cert=cert, proxies=proxies,
                                allow_redirects=False, **adapter_kwargs)
                extract_cookies_to_jar(self.cookies, prepared_request, resp.raw)
                url = self.get_redirect_target(resp)
                yield resp

    def rebuild_auth(self, prepared_request, response):
        headers = prepared_request.headers
        url = prepared_request.url
        if "Authorization" in headers:
            original_parsed = urlparse(response.request.url)
            redirect_parsed = urlparse(url)
            if (original_parsed.hostname != redirect_parsed.hostname) or self.should_strip_auth(response.request.url, url):
                del headers["Authorization"]
        new_auth = get_netrc_auth(url) if self.trust_env else None
        if new_auth is not None:
            prepared_request.prepare_auth(new_auth)

    def rebuild_proxies(self, prepared_request, proxies):
        proxies = proxies if proxies is not None else {}
        headers = prepared_request.headers
        scheme = urlparse(prepared_request.url).scheme
        new_proxies = resolve_proxies(prepared_request, proxies, self.trust_env)
        if "Proxy-Authorization" in headers:
            del headers["Proxy-Authorization"]
        try:
            username, password = get_auth_from_url(new_proxies[scheme])
        except KeyError:
            username, password = None, None
        if username and password:
            headers["Proxy-Authorization"] = _basic_auth_str(username, password)
        return new_proxies


def merge_setting(request_setting, session_setting, dict_class=OrderedDict):
    if session_setting is None:
        return request_setting
    if request_setting is None:
        return session_setting
    if not (isinstance(session_setting, Mapping) and isinstance(request_setting, Mapping)):
        return request_setting
    merged_setting = dict_class(to_key_val_list(session_setting))
    merged_setting.update(to_key_val_list(request_setting))
    none_keys = [k for (k, v) in merged_setting.items() if v is None]
    for key in none_keys:
        del merged_setting[key]
    return merged_setting


def merge_hooks(request_hooks, session_hooks, dict_class=OrderedDict):
    if session_hooks is None or session_hooks.get("response") == []:
        return request_hooks
    if request_hooks is None or request_hooks.get("response") == []:
        return session_hooks
    return merge_setting(request_hooks, session_hooks, dict_class)


class Session(SessionRedirectMixin):
    __attrs__ = ["headers", "cookies", "auth", "proxies", "hooks", "params",
                 "verify", "cert", "adapters", "stream", "trust_env", "max_redirects"]

    def __init__(self):
        self.headers = default_headers()
        self.auth = None
        self.proxies = {}
        self.hooks = default_hooks()
        self.params = {}
        self.stream = False
        self.verify = True
        self.cert = None
        self.max_redirects = DEFAULT_REDIRECT_LIMIT
        self.trust_env = True
        self.cookies = cookiejar_from_dict({})
        self.adapters = OrderedDict()
        self.mount("https://", HTTPAdapter())
        self.mount("http://", HTTPAdapter())

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def prepare_request(self, request):
        cookies = request.cookies or {}
        if not isinstance(cookies, cookielib.CookieJar):
            cookies = cookiejar_from_dict(cookies)
        merged_cookies = merge_cookies(merge_cookies(RequestsCookieJar(), self.cookies), cookies)
        auth = request.auth
        if self.trust_env and not auth and not self.auth:
            auth = get_netrc_auth(request.url)
        p = PreparedRequest()
        p.prepare(
            method=request.method.upper(), url=request.url, files=request.files,
            data=request.data, json=request.json,
            headers=merge_setting(request.headers, self.headers, dict_class=CaseInsensitiveDict),
            params=merge_setting(request.params, self.params),
            auth=merge_setting(auth, self.auth),
            cookies=merged_cookies,
            hooks=merge_hooks(request.hooks, self.hooks),
        )
        return p

    def request(self, method, url, params=None, data=None, headers=None,
                cookies=None, files=None, auth=None, timeout=None,
                allow_redirects=True, proxies=None, hooks=None, stream=None,
                verify=None, cert=None, json=None):
        req = Request(method=method.upper(), url=url, headers=headers, files=files,
                      data=data or {}, json=json, params=params or {},
                      auth=auth, cookies=cookies, hooks=hooks)
        prep = self.prepare_request(req)
        proxies = proxies or {}
        settings = self.merge_environment_settings(prep.url, proxies, stream, verify, cert)
        send_kwargs = {"timeout": timeout, "allow_redirects": allow_redirects}
        send_kwargs.update(settings)
        resp = self.send(prep, **send_kwargs)
        return resp

    def send(self, request, **kwargs):
        kwargs.setdefault("stream", self.stream)
        kwargs.setdefault("verify", self.verify)
        kwargs.setdefault("cert", self.cert)
        if "proxies" not in kwargs:
            kwargs["proxies"] = resolve_proxies(request, self.proxies, self.trust_env)
        if isinstance(request, Request):
            raise ValueError("You can only send PreparedRequests.")
        allow_redirects = kwargs.pop("allow_redirects", True)
        stream = kwargs.get("stream")
        hooks = request.hooks
        adapter = self.get_adapter(url=request.url)
        start = preferred_clock()
        r = adapter.send(request, **kwargs)
        elapsed = preferred_clock() - start
        r.elapsed = timedelta(seconds=elapsed)
        r = dispatch_hook("response", hooks, r, **kwargs)
        if r.history:
            for resp in r.history:
                extract_cookies_to_jar(self.cookies, resp.request, resp.raw)
        extract_cookies_to_jar(self.cookies, request, r.raw)
        if allow_redirects:
            gen = self.resolve_redirects(r, request, **kwargs)
            history = [resp for resp in gen]
        else:
            history = []
        if history:
            history.insert(0, r)
            r = history.pop()
            r.history = history
        if not allow_redirects:
            try:
                r._next = next(self.resolve_redirects(r, request, yield_requests=True, **kwargs))
            except StopIteration:
                pass
        if not stream:
            r.content
        return r

    def merge_environment_settings(self, url, proxies, stream, verify, cert):
        if self.trust_env:
            no_proxy = proxies.get("no_proxy") if proxies is not None else None
            env_proxies = get_environ_proxies(url, no_proxy=no_proxy)
            for k, v in env_proxies.items():
                proxies.setdefault(k, v)
            if verify is True or verify is None:
                verify = (os.environ.get("REQUESTS_CA_BUNDLE")
                          or os.environ.get("CURL_CA_BUNDLE") or verify)
        proxies = merge_setting(proxies, self.proxies)
        stream = merge_setting(stream, self.stream)
        verify = merge_setting(verify, self.verify)
        cert = merge_setting(cert, self.cert)
        return {"proxies": proxies, "stream": stream, "verify": verify, "cert": cert}

    def get_adapter(self, url):
        for prefix, adapter in self.adapters.items():
            if url.lower().startswith(prefix.lower()):
                return adapter
        raise InvalidSchema(f"No connection adapters were found for {url!r}")

    def close(self):
        for v in self.adapters.values():
            v.close()

    def mount(self, prefix, adapter):
        self.adapters[prefix] = adapter
        keys_to_move = [k for k in self.adapters if len(k) < len(prefix)]
        for key in keys_to_move:
            self.adapters[key] = self.adapters.pop(key)
