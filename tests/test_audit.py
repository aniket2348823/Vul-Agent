import pytest,httpx,time
B='http://localhost:8000';T=15.0
@pytest.fixture(scope='session')
def c():
    with httpx.Client(base_url=B,timeout=T) as cl:
        try:
            cl.get('/api/health')
        except httpx.ConnectError:
            pytest.skip('backend server not running on localhost:8000', allow_module_level=False)
        yield cl
class TestHealth:
    def test_ok(self,c): assert c.get('/api/health').json()['status']=='online'
    def test_404(self,c): assert c.get('/api/nonexistent').status_code in(404,405)
class TestDashboard:
    def test_stats(self,c): assert 'metrics' in c.get('/api/dashboard/stats').json()
    def test_stats_keys(self,c):
        m=c.get('/api/dashboard/stats').json()['metrics']
        for k in['total_scans','active_scans','vulnerabilities','critical']: assert k in m
    def test_bad_auth(self,c): assert c.get('/api/dashboard/stats',headers={'Authorization':'Bearer invalidtoken123'}).status_code==401
    def test_scans(self,c): assert isinstance(c.get('/api/dashboard/scans').json(),list)
    def test_settings(self,c): assert '2fa_enabled' in c.get('/api/dashboard/settings').json()
    def test_update(self,c): assert c.post('/api/dashboard/settings',json={}).json()['status']=='success'
    def test_auth(self,c): assert '2fa_required' in c.get('/api/dashboard/auth/status').json()
    def test_wrong(self,c): assert c.post('/api/dashboard/auth/login',json={'username':'wronguser','totp_code':'x'}).status_code==401
    def test_bad_totp(self,c): assert c.post('/api/dashboard/auth/login',json={'username':'a','totp_code':'000000'}).status_code==401
    def test_logout(self,c): assert c.post('/api/dashboard/auth/logout').json()['status']=='success'
    def test_2fa(self,c): assert 'secret' in c.post('/api/dashboard/settings/2fa/generate').json()
    def test_2fa_bad(self,c):
        c.post('/api/dashboard/settings/2fa/generate')
        assert c.post('/api/dashboard/settings/2fa/verify',json={'totp_code':'000000'}).status_code==401
    def test_reset(self,c): assert c.post('/api/dashboard/reset').json()['status']=='success'
