"""Selenium acceptance for requested equipment and compound accessory search."""
import json
import unittest
from urllib.parse import urlencode
from urllib.request import urlopen
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import test_product_experience_ui as experiences

class CricketEquipmentUiTest(unittest.TestCase):
    def setUp(self):
        options=webdriver.ChromeOptions();options.add_argument('--headless=new');options.add_argument('--window-size=1440,1000')
        self.driver=webdriver.Chrome(options=options);self.addCleanup(self.driver.quit);self.wait=WebDriverWait(self.driver,30)
    def test_compound_accessories_search_open_details_and_stay_out_of_bat_results(self):
        for query,kind in (('bat grip','bat-grip'),('bat oil','bat-oil'),('batting tee','batting-tee'),('toe guard','toe-guard'),('bat care kit','bat-care-kit'),('bat','bat')):
            with self.subTest(query=query):
                with urlopen('http://localhost:3000/api/catalog/public/products?'+urlencode({'q':query}),timeout=15) as r:expected=json.load(r)['items']
                self.assertTrue(expected)
                self.assertTrue(all(p['details']['equipmentType']==kind for p in expected))
                self.driver.get('http://localhost:3000/')
                search=self.wait.until(EC.element_to_be_clickable((By.ID,'store-search')));search.send_keys(query)
                self.driver.find_element(By.CSS_SELECTOR,'.shop-search button').click()
                self.wait.until(lambda d:d.execute_script("return [...document.querySelectorAll('.store-card')].map(c=>c.dataset.productId)")==[p['id'] for p in expected])
                self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR,'.store-card-image'))).click()
                detail=self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR,'.detail-layout')))
                self.assertEqual(expected[0]['id'],detail.get_attribute('data-product-id'))
                self.wait.until(lambda d:d.execute_script("return document.querySelector('.detail-image img')?.naturalWidth > 0"))
    def test_new_single_configuration_equipment_can_be_added_to_cart_and_restored(self):
        token=experiences.ProductExperienceUiTests.customer_login(self)
        with urlopen('http://localhost:3000/api/catalog/public/products?q=roller',timeout=15) as r:product=json.load(r)['items'][0]
        sku=product['skus'][0];url='http://localhost:8085/api/v1/customer/cart'
        status,original=experiences.manage.request_json(url,token=token);self.assertEqual(200,status)
        quantity=next((row['quantity'] for row in original if row['skuId']==sku['id']),0)
        self.assertLess(quantity,99)
        try:
            experiences.ProductExperienceUiTests.open_product(self,product)
            self.wait.until(EC.element_to_be_clickable((By.XPATH,"//button[normalize-space()='Add to cart']"))).click()
            self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR,'.store-alert.success')))
            self.driver.get('http://localhost:3000/cart')
            self.wait.until(lambda d:sku['code'] in d.find_element(By.CSS_SELECTOR,'.customer-page').text)
            status,current=experiences.manage.request_json(url,token=token);self.assertEqual(200,status)
            self.assertEqual(quantity+1,next(row['quantity'] for row in current if row['skuId']==sku['id']))
        finally:
            status,_=experiences.manage.request_json(url+'/items/'+sku['id'],token=token,method='PUT' if quantity else 'DELETE',data=json.dumps({'quantity':quantity}).encode() if quantity else None)
            self.assertIn(status,(200,204))

    def test_ground_equipment_and_protection_have_usable_detail_layout_and_realistic_options(self):
        for query in ('roller','sightscreen','padded shorts','light meter','shin guard'):
            with self.subTest(query=query):
                with urlopen('http://localhost:3000/api/catalog/public/products?'+urlencode({'q':query}),timeout=15) as r:products=json.load(r)['items']
                self.assertGreaterEqual(len(products),2)
                self.driver.get('http://localhost:3000/products/'+products[0]['slug'])
                self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR,'.detail-layout')))
                self.wait.until(lambda d:d.execute_script("return document.querySelector('.detail-image img')?.naturalWidth > 0"))
                text=self.driver.find_element(By.TAG_NAME,'body').text
                self.assertNotIn('That product is not available.',text)
                if query=='roller':self.assertNotIn('XS',text)
                self.driver.execute_cdp_cmd('Emulation.setDeviceMetricsOverride',{'width':390,'height':844,'deviceScaleFactor':1,'mobile':True})
                bounds=self.driver.execute_script("const i=document.querySelector('.detail-image img').getBoundingClientRect(),f=document.querySelector('.detail-image').getBoundingClientRect();return {i:{l:i.left,r:i.right,t:i.top,b:i.bottom},f:{l:f.left,r:f.right,t:f.top,b:f.bottom}}")
                self.assertGreaterEqual(bounds['i']['t'],bounds['f']['t']-1);self.assertLessEqual(bounds['i']['b'],bounds['f']['b']+1)
                self.assertGreaterEqual(bounds['i']['l'],bounds['f']['l']-1);self.assertLessEqual(bounds['i']['r'],bounds['f']['r']+1)
                self.driver.execute_cdp_cmd('Emulation.clearDeviceMetricsOverride',{})
