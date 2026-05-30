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
class TestAttack:
    def _f(self,c,url='http://localhost:8000/api/health',**kw):
        return c.post('/api/attack/fire',json={'target_url':url,'method':'GET','duration':2,**kw})
    def test_fire(self,c):
        r=self._f(c); assert r.status_code==200 and 'scan_id' in r.json()
    def test_private(self,c): assert self._f(c,'http://192.168.1.1:8080/t').status_code==200
    def test_aws(self,c): assert self._f(c,'http://169.254.169.254/x').status_code==403
    def test_file(self,c): assert self._f(c,'file:///etc/passwd').status_code in(400,403)
    def test_ftp(self,c): assert self._f(c,'ftp://e.com/x').status_code in(400,403)
    def test_public(self,c): assert self._f(c,'http://google.com').status_code==403
    def test_missing(self,c): assert c.post('/api/attack/fire',json={'method':'GET'}).status_code==400
    def test_empty(self,c): assert c.post('/api/attack/fire',content=b'').status_code in(400,422)
    def test_modules(self,c): assert self._f(c,modules=['The Tycoon']).status_code==200
    def test_example(self,c): assert self._f(c,'http://example.com').status_code==200
    def test_replay404(self,c): assert c.post('/api/attack/replay/no-vuln').status_code==404
class TestRecon:
    def test_ingest(self,c): assert c.post('/api/recon/ingest',json={'url':'http://t','method':'GET','headers':{},'timestamp':time.time()}).status_code==200
    def test_scanner(self,c): assert c.post('/api/recon/ingest',json={'url':'http://t','method':'POST','headers':{'x-scanner':'v12-engine'},'body':{'findings':[{'description':'f'}]},'timestamp':time.time()}).status_code==200
    def test_bad(self,c): assert c.post('/api/recon/ingest',json={'url':'http://t'}).status_code==400
    def test_keyring(self,c): assert isinstance(c.get('/api/recon/keyring').json(),list)
    def test_keys(self,c): assert c.post('/api/recon/keys',json={'url':'http://t','keys':{'k':'v'},'timestamp':time.time()}).json()['status']=='archived'
    def test_keys_bad(self,c): assert c.post('/api/recon/keys',json={'url':'x'}).status_code==400
class TestDefense:
    def test_get(self,c): assert c.get('/api/defense/analyze').json()['status']=='ready'
    def test_empty(self,c): assert c.post('/api/defense/analyze',content=b'').status_code==500
    def test_badjson(self,c): assert c.post('/api/defense/analyze',content=b'{bad').status_code==500
    def test_block(self,c): assert c.post('/api/defense/analyze',json={'agent_id':'agent_prism','content':{'text':'test injection'},'url':'http://t'}).json()['verdict']=='BLOCK'
    def test_idle(self,c): assert c.post('/api/defense/analyze',json={'agent_id':'agent_unknown','content':{'text':'safe'},'url':'http://t'}).json()['verdict']=='IDLE'
