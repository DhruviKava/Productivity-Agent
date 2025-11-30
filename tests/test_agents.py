import json
from src.tools.mcp_tools import MCP
from src.agents.collector_agent import CollectorAgent

def test_collector(tmp_path):
    p = tmp_path/"removed_tasksjson"
    p.write_text(json.dumps([{"title":"t1","effort":1}]))
    mcp = MCP()
    c = CollectorAgent(mcp=mcp)
    tasks = c.collect(str(p))
    assert isinstance(tasks,list)
