from pathlib import Path
import copy,sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from project_inventory import project

class InventoryTests(unittest.TestCase):
    def test_projection_keeps_identity_without_mutating_controls_or_status(self):
        d={"current_worker":{"pid":123},"rows":[{"id":"catalog-7","owner":"MixedCase.vpk",
            "member":"cooked/characters/accessories/wieldable_items/shields/x.dds",
            "status":"running","role":"normal","material":"metal","processing_route":{"kind":"EXAMPLE"}}]}
        before=copy.deepcopy(d);out=project(d,"f"*64)
        self.assertEqual(d,before);r=out["rows"][0]
        self.assertEqual(r["id"],"catalog-7");self.assertEqual(r["owner"],"MixedCase.vpk")
        self.assertEqual(r["category"]["content_group"],"armor_weapons")
        self.assertEqual(r["category"]["map_types"],["normal"])
        self.assertNotIn("status",r);self.assertNotIn("current_worker",out)
    def test_alias_refusal(self):
        r={"owner":"A.vpk","member":"literal.dds"}
        with self.assertRaisesRegex(ValueError,"Duplicate"):
            project({"rows":[r,{**r,"owner":"a.vpk"}]},"0"*64)
if __name__=="__main__":unittest.main(verbosity=2)
