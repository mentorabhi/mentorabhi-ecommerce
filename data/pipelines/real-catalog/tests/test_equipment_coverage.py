import copy
import json
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from equipment_coverage import audit


class EquipmentCoverageTest(unittest.TestCase):
    def setUp(self):
        self.registry=json.loads((Path(__file__).resolve().parents[1]/'cricket-equipment-coverage.json').read_text())
        for row in self.registry['requirements']:
            row['models']=[]
        self.product={'sourceKey':'a','sport':'cricket','source':{'url':'https://supplier.example/products/bat'},'image':{'kind':'photograph'}}
        self.manifest={'products':[self.product]}
        self.match={'sourceKey':'a','sourceUrl':self.product['source']['url'],'evidence':'Supplier identifies a willow cricket bat in its sourced product facts.'}
    def test_empty_registry_reports_gaps_without_claiming_completion(self):
        report=audit(self.manifest,self.registry)
        self.assertEqual((False,0,54,108),(report['complete'],report['coveredFamilies'],report['totalFamilies'],report['missingModels']))
        with self.assertRaisesRegex(ValueError,'incomplete'):
            audit(self.manifest,self.registry,require_complete=True)
    def test_duplicate_model_cannot_count_sku_options_twice(self):
        self.registry['requirements'][0]['models']=[self.match,self.match]
        with self.assertRaisesRegex(ValueError,'repeated models'):
            audit(self.manifest,self.registry)
    def test_football_unknown_source_wrong_evidence_and_fake_images_are_rejected(self):
        for mutation in ('football','unknown','wrong-url','no-evidence','art'):
            with self.subTest(mutation=mutation):
                registry=copy.deepcopy(self.registry);manifest=copy.deepcopy(self.manifest)
                registry['requirements'][0]['models']=[copy.deepcopy(self.match)]
                if mutation=='football':manifest['products'][0]['sport']='football'
                if mutation=='unknown':registry['requirements'][0]['models'][0]['sourceKey']='missing'
                if mutation=='wrong-url':registry['requirements'][0]['models'][0]['sourceUrl']='https://wrong.example'
                if mutation=='no-evidence':registry['requirements'][0]['models'][0]['evidence']='Bat'
                if mutation=='art':manifest['products'][0]['image']['kind']='illustration'
                with self.assertRaises(ValueError):audit(manifest,registry)
    def test_two_distinct_sourced_models_complete_one_family_only(self):
        second=copy.deepcopy(self.product);second['sourceKey']='b';second['source']['url']+='-second';self.manifest['products'].append(second)
        match=copy.deepcopy(self.match);match['sourceKey']='b';match['sourceUrl']=second['source']['url']
        self.registry['requirements'][0]['models']=[self.match,match]
        report=audit(self.manifest,self.registry)
        self.assertEqual(1,report['coveredFamilies']);self.assertEqual(106,report['missingModels'])
    def test_missing_or_renumbered_requirement_cannot_silently_disappear(self):
        self.registry['requirements'].pop()
        with self.assertRaisesRegex(ValueError,'54'):audit(self.manifest,self.registry)
