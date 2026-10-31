from pathlib import Path
import sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
import categories as c

class CategoriesTests(unittest.TestCase):
    def test_equipment_precedes_character(self):
        a=c.classify("cooked/characters/accessories/wieldable_items/weapons/a_n.dds",role="spec",role_present=True,scope="current_queue_snapshot")
        self.assertEqual(a["content_group"],"armor_weapons")
        self.assertEqual(a["map_types"],["specular"]) # Actual role beats misleading suffix.
        self.assertEqual(a["saved_classification"]["role"],"spec")
    def test_effects_precede_interface(self):
        a=c.classify("cooked/ui_fx/fx/fire/fire_c.dds")
        self.assertEqual(a["content_group"],"effects")
        self.assertEqual(c.classify("cooked/ui/icons/button.dds")["content_group"],"ui")
    def test_terrain_and_building_maps_stay_with_content(self):
        a=c.classify("_exp01/cooked/zones/sourceimages/masonry/wall_s.dds",role="bump",role_present=True,scope="current_queue_snapshot")
        self.assertEqual(a["content_group"],"buildings_props")
        self.assertEqual(a["map_types"],["bump"])
        self.assertEqual(c.classify("cooked/interiors/sourceimages/ground/sand.dds")["content_group"],"terrain")
    def test_null_unknown_and_signed_storage_not_invented(self):
        a=c.classify("unrecognized/blob.dds",role=None,role_present=True,scope="current_queue_snapshot",format_name="QWVU")
        self.assertEqual(a["map_types"],["unknown"]);self.assertEqual(a["content_group"],"unclassified")
        self.assertIsNone(a["saved_classification"]["role"]);self.assertTrue(a["saved_classification"]["role_present"])
        self.assertIn("no inferred vector",a["storage_qualification"]);self.assertTrue(a["review_required"])
        self.assertFalse(c.classify("blob.dds")["saved_classification"]["role_present"])
    def test_alpha_route_joins_semantic_role_without_opacity_claim(self):
        a=c.classify("cooked/characters/body_c.dds",role="color",role_present=True,scope="current_queue_snapshot",route={"kind":"QWEN_ALPHA_SELECTED_CHANNEL"})
        self.assertEqual(a["map_types"],["alpha","color"]);c.validate(a)
        self.assertIn("other than opacity",c.taxonomy()["qualification"])
    def test_bad_category_refused_and_counts_keep_unknowns(self):
        a=c.classify("mystery.dds");s=c.summary([{"category":a}])
        self.assertEqual(s["content_groups"]["unclassified"],1)
        a["content_group"]="made_up"
        with self.assertRaises(ValueError):c.validate(a)
    def test_soga_and_playerstudio_domains(self):
        self.assertEqual(c.classify("cooked/soga_art/soga_characters/soga_pc/body.dds")["content_group"],"characters_monsters")
        self.assertEqual(c.classify("cooked/playerstudio/environments/houseitems/table/table_s.dds")["content_group"],"buildings_props")
if __name__=="__main__":unittest.main(verbosity=2)
