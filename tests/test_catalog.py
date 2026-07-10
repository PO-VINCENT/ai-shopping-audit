from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from catalogready.catalog.scoring import audit_catalog


class CatalogAuditTests(unittest.TestCase):
    def test_detects_duplicate_ids_and_ambiguous_variants(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "variants.csv"
            path.write_text(
                "id,item_group_id,title,description,link,image_link,price,availability,brand,product_type,color,size,gender,age_group,material\n"
                "1,G1,City Shoe,Blue,https://e/1,https://e/1.jpg,10 AUD,in_stock,Brand,shoes,Blue,M,unisex,adult,Mesh\n"
                "1,G1,City Shoe,Black,https://e/2,https://e/2.jpg,10 AUD,in_stock,Other,shoes,Black,M,unisex,adult,Mesh\n",
                encoding="utf-8",
            )
            result = audit_catalog(str(path))
        rule_ids = {finding["rule_id"] for finding in result["findings"]}
        self.assertIn("CAT-IDENTITY-001", rule_ids)
        self.assertIn("CAT-VARIANT-003", rule_ids)
        self.assertIn("CAT-VARIANT-004", rule_ids)

    def test_structural_defects_cap_the_score(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "duplicates.csv"
            path.write_text(
                "id,item_group_id,title,description,link,image_link,price,availability,brand,product_type,color\n"
                "1,G1,City Shoe Blue,Blue mesh shoe,https://e/1,https://e/1.jpg,10 AUD,in_stock,Brand,shoes,Blue\n"
                "1,G1,City Shoe Black,Black mesh shoe,https://e/2,https://e/2.jpg,10 AUD,in_stock,Brand,shoes,Black\n",
                encoding="utf-8",
            )
            result = audit_catalog(str(path))
        breakdown = result["summary"]["score_breakdown"]
        self.assertEqual(breakdown["base_completeness"], 100)
        self.assertLessEqual(result["scores"]["catalog_readiness"]["score"], 69)
        self.assertTrue(breakdown["cap_reasons"])

