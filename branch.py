#!/usr/bin/env python
import reposadolib.reposadocommon as reposadocommon
reposadocommon.get_main_dir = lambda: '/usr/local/bin/'

catalog_branches = reposadocommon.getCatalogBranches()
branch_name = 'osx-updates'
if branch_name not in catalog_branches:
  catalog_branches[branch_name] = []

products = reposadocommon.getProductInfo()
for product_id, p in products.iteritems():
  t = p['title']
  if t.startswith('OS X') or t.startswith('Mac OS X'):
    catalog_branches[branch_name].append(product_id)
reposadocommon.writeCatalogBranches(catalog_branches)
reposadocommon.writeAllBranchCatalogs()
