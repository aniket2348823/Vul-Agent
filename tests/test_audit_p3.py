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
class TestAI:
    def test_status(self,c): assert 'core_status' in c.get('/api/ai/status').json()
    def test_mutate(self,c): assert 'variants' in c.post('/api/ai/mutate',json={'url':'http://t','method':'GET'}).json()
    def test_mutate_bad(self,c): assert c.post('/api/ai/mutate',json={'method':'GET'}).status_code==400
    def test_auto(self,c): assert c.post('/api/ai/autonomous/engage',json={'url':'http://localhost:8000','method':'GET'}).json()['status']=='launched'
class TestReports:
    def test_list(self,c): assert isinstance(c.get('/api/reports/').json(),list)
    def test_pdf404(self,c): assert c.get('/api/reports/pdf/no-scan').status_code in(404,500)
    def test_dl404(self,c): assert c.get('/api/reports/download/no.pdf').status_code==404
    def test_live404(self,c): assert c.get('/api/reports/live/no-scan').status_code==404
    def test_diff404(self,c): assert c.get('/api/reports/diff/s1/s2').status_code==404
class TestData:
    def test_list(self,c): assert 'items' in c.get('/api/data').json()
    def test_create(self,c): assert 'id' in c.post('/api/data',json={'data':{'n':'t'},'owner':'u'}).json()
    def test_get(self,c):
        i=c.post('/api/data',json={'data':{},'owner':'u'}).json()['id']
        assert c.get(f'/api/data/{i}').status_code==200
    def test_rls_ok(self,c):
        i=c.post('/api/data',json={'data':{},'owner':'a'}).json()['id']
        assert c.get(f'/api/data/{i}',headers={'X-User-Id':'a'}).status_code==200
    def test_rls_fail(self,c):
        i=c.post('/api/data',json={'data':{},'owner':'a'}).json()['id']
        assert c.get(f'/api/data/{i}',headers={'X-User-Id':'b'}).status_code==403
    def test_update(self,c):
        i=c.post('/api/data',json={'data':{'v':1},'owner':'o'}).json()['id']
        assert c.put(f'/api/data/{i}',json={'data':{'v':2}}).json()['data']['v']==2
    def test_delete(self,c):
        i=c.post('/api/data',json={'data':{},'owner':'d'}).json()['id']
        assert c.delete(f'/api/data/{i}').json()['status']=='deleted'
    def test_get404(self,c): assert c.get('/api/data/nope').status_code==404
    def test_del404(self,c): assert c.delete('/api/data/nope').status_code==404
class TestCode:
    def test_safe(self,c): assert 'findings' in c.post('/api/analyze-code',json={'code':'print(1)','language':'python'}).json()
    def test_missing(self,c): assert c.post('/api/analyze-code',json={'language':'python'}).status_code==400
