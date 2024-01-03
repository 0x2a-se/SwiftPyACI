import unittest
import pathlib
import json

import swiftpyaci




def make_test_tenant():
    meta_data_folder = pathlib.Path(__file__).absolute().parent / ".meta_data"
    
    with open(meta_data_folder / "fvTenant.json") as tenant_file:
        tenant_meta = json.load(tenant_file)
    tenat_meta = swiftpyaci.class_meta(**list(tenant_meta.values())[0])
    tenant = swiftpyaci.mo("fvTenant",parent_dn = "uni", name = "Tenant", class_meta = tenat_meta, nameAlias = "Alias", descr = "Tenant descr")
    return tenant

class TestManagedObject(unittest.TestCase):

    def test_new_fv_tenant(self):
        tenant = make_test_tenant()
        result = {'fvTenant': {'attributes': {'dn': 'uni/tn-Tenant', 'name': 'Tenant', 'nameAlias': 'Alias', 'descr': 'Tenant descr'}}}
        self.assertEqual(tenant.serilize(), result)

    def test_new_fv_tenant_diff(self):
        tenant = make_test_tenant()
        result = {'attributes': {'name': {'previous': '', 'new': 'Tenant', 'action': 'new'}, 'nameAlias': {'previous': '', 'new': 'Alias', 'action': 'new'}, 'descr': {'previous': '', 'new': 'Tenant descr', 'action': 'new'}, 'dn': {'previous': '', 'new': 'uni/tn-Tenant', 'action': 'new'}}}
        self.assertEqual(tenant.diff(), result)

    def test_change_fv_tenant_diff(self):
        tenant = make_test_tenant()
        tenant.set_cache()
        tenant.nameAlias = "new-alias"
        result = {'attributes': {'nameAlias': {'previous': 'Alias', 'new': 'new-alias', 'action': 'changed'}}}
        self.assertEqual(tenant.diff(), result)
    
   

if __name__ == '__main__':
    unittest.main()
