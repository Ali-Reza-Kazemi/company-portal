import json
import os
import urllib.request
import urllib.parse
import http.cookiejar

def run():
    jar=http.cookiejar.CookieJar()
    client=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    base='http://portal.localhost:8000'
    # Service resolves itself through localhost; preserve the configured site Host.
    base='http://127.0.0.1:8000'
    def request(path,data=None):
        headers={'Host':'portal.localhost'}
        if data is not None:
            data=urllib.parse.urlencode(data).encode()
        return client.open(urllib.request.Request(base+path,data=data,headers=headers))
    request('/api/method/login',{'usr':'Administrator','pwd':os.environ['ADMIN_PASSWORD']}).read()
    html=request('/portal').read().decode()
    assert '<html lang="fa" dir="rtl">' in html
    assert 'ثبت اقدام کاری' in html and 'نتایج شاخص‌های عملکرد' in html
    assert 'is_demo' in html
    data=json.loads(request('/api/method/saein_portal.api.dashboard').read())['message']
    assert len(data['domains'])==3
    assert all(not row['is_demo'] for row in data['actions'])
    request('/portal-import').read()
    assert request('/assets/saein_portal/js/calendar.js').status==200
    return {'authenticated_dashboard':'passed','rtl_markup':'passed','three_domains':'passed','demo_separation':'passed','import_page':'passed','calendar_asset':'passed'}
