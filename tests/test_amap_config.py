import os
import tempfile
import unittest
from pathlib import Path

import scripts.build_amap_school_map as amap


class AMapConfigTests(unittest.TestCase):
    def test_loads_amap_config_from_env_local_when_environment_is_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".env.local").write_text(
                'AMAP_KEY="local-key"\nAMAP_SECURITY_CODE=local-security\n',
                encoding="utf-8",
            )
            old_key = os.environ.pop("AMAP_KEY", None)
            old_security = os.environ.pop("AMAP_SECURITY_CODE", None)
            try:
                self.assertEqual(amap.load_amap_config(root), ("local-key", "local-security"))
            finally:
                if old_key is not None:
                    os.environ["AMAP_KEY"] = old_key
                if old_security is not None:
                    os.environ["AMAP_SECURITY_CODE"] = old_security


if __name__ == "__main__":
    unittest.main()
