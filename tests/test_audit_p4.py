import pytest
class TestGuardLayer:
    def test_empty(self):
        from backend.core.guard_layer import GuardLayer; assert GuardLayer().filter([])==[]
    def test_no_resp(self):
        from backend.core.guard_layer import GuardLayer; assert len(GuardLayer().filter([{'url':'t','validation':'VALID','confidence':0.9}]))==0
    def test_valid(self):
        from backend.core.guard_layer import GuardLayer
        assert len(GuardLayer().filter([{'url':'t','response':'d','validation':'VALID','gi5_match':True,'confidence':0.9}]))==1
    def test_low_conf(self):
        from backend.core.guard_layer import GuardLayer
        assert len(GuardLayer().filter([{'url':'t','response':'d','validation':'VALID','gi5_match':True,'confidence':0.01}]))==0
    def test_dedup(self):
        from backend.core.guard_layer import GuardLayer; g=GuardLayer()
        f={'url':'t','response':'d','validation':'VALID','gi5_match':True,'confidence':0.9,'type':'X'}
        assert len(g.filter([f,f.copy()]))==1
    def test_cluster(self):
        from backend.core.guard_layer import GuardLayer
        fs=[{'url':'http://a','type':'XSS','confidence':0.8,'payload':'1'},{'url':'http://a','type':'XSS','confidence':0.9,'payload':'2'},{'url':'http://b','type':'S','confidence':0.7,'payload':'3'}]
        assert len(GuardLayer().cluster_findings(fs))==2
class TestCVSS:
    def test_basic(self):
        from backend.reporting.cvss_engine import CVSSCalculator
        s,v=CVSSCalculator(success_count=1).calculate(); assert s>0 and 'CVSS:3.1' in v
    def test_zero(self):
        from backend.reporting.cvss_engine import CVSSCalculator
        assert CVSSCalculator(success_count=0).calculate()[0]==0.0
    def test_token(self):
        from backend.reporting.cvss_engine import CVSSCalculator
        s,v=CVSSCalculator(success_count=1,body_content='token leaked').calculate(); assert 'C:H' in v
    def test_vector(self):
        from backend.reporting.cvss_engine import CVSSCalculator
        assert len(CVSSCalculator(success_count=1).calculate()[1].split('/'))==9
class TestGraph:
    def test_node(self):
        from backend.core.unified_knowledge_graph import GraphEngine; g=GraphEngine(); g.nodes.clear(); g.edges.clear()
        assert g._add_or_update_node('XSS','/a').type=='XSS'
    def test_chain_ok(self):
        from backend.core.unified_knowledge_graph import GraphEngine; assert GraphEngine().can_chain('SQL_INJECTION','BROKEN_AUTH')
    def test_chain_bad(self):
        from backend.core.unified_knowledge_graph import GraphEngine; assert not GraphEngine().can_chain('XSS','SQL_INJECTION')
    def test_eq(self):
        from backend.core.unified_knowledge_graph import VulnNode; assert VulnNode('A','/x')==VulnNode('A','/x')
class TestProtocol:
    def test_pri(self):
        from backend.core.protocol import TaskPriority; assert TaskPriority.CRITICAL=='CRITICAL'
    def test_aid(self):
        from backend.core.protocol import AgentID; assert AgentID.OMEGA=='agent_omega'
    def test_tgt(self):
        from backend.core.protocol import TaskTarget; assert TaskTarget(url='http://t').method=='GET'
    def test_vln(self):
        from backend.core.protocol import Vulnerability; assert Vulnerability(name='V',severity='H',description='D',evidence='E').remediation is None
class TestConfig:
    def test_set(self):
        from backend.core.config import settings; assert settings.PROJECT_ROOT!=''
    def test_sin(self):
        from backend.core.config import ConfigManager; assert ConfigManager() is ConfigManager()
    def test_mask(self):
        from backend.core.config import ConfigManager; assert ConfigManager().get_all()['supabase']['key']=='MASKED'
class TestBase:
    def test_ok(self):
        from backend.core.base import BaseArsenalModule; assert BaseArsenalModule.safe_json_parse('{"k":"v"}')['k']=='v'
    def test_bad(self):
        from backend.core.base import BaseArsenalModule; assert 'error' in BaseArsenalModule.safe_json_parse('bad{')
    def test_deep(self):
        from backend.core.base import BaseArsenalModule
        assert 'error' in BaseArsenalModule.safe_json_parse('{"a":'*150+'"x"'+'}'*150)
class TestSocket:
    def test_low(self):
        from backend.api.socket_manager import get_display_limit; assert get_display_limit(100)==100
    def test_high(self):
        from backend.api.socket_manager import get_display_limit; assert get_display_limit(1000)==400
    def test_emit(self):
        from backend.api.socket_manager import should_emit; assert should_emit({},500) is True
class TestSchemas:
    def test_atk(self):
        from backend.schemas.payloads import AttackPayload; assert AttackPayload(target_url='http://t',method='G').velocity==50
    def test_rec(self):
        from backend.schemas.payloads import ReconPayload; assert ReconPayload(url='t',method='G',headers={},timestamp=1.0).body is None
class TestURL:
    def _v(self,u):
        from backend.api.endpoints.attack import validate_target_url; return validate_target_url(u)[0]
    def test_local(self): assert self._v('http://localhost:8000')
    def test_aws(self): assert not self._v('http://169.254.169.254/x')
    def test_file(self): assert not self._v('file:///etc/passwd')
    def test_pub(self): assert not self._v('http://google.com')
    def test_port(self): assert self._v('http://custom.io:9090')
