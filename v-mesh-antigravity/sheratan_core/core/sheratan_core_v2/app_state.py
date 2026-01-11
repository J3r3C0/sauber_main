from .webrelay_bridge import WebRelayBridge, WebRelaySettings
from .lcp_actions import LCPActionInterpreter
from . import storage

relay_settings = WebRelaySettings(
    relay_out_dir=storage.DATA_DIR.parent / "webrelay_out",
    relay_in_dir=storage.DATA_DIR.parent / "webrelay_in",
    session_prefix="core_v2"
)

bridge = WebRelayBridge(relay_settings)
lcp = LCPActionInterpreter(bridge=bridge)
