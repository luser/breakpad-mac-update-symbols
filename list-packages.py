#!/usr/bin/env python
import reposadolib.reposadocommon as reposadocommon
reposadocommon.get_main_dir = lambda: '/usr/local/bin/'

products = reposadocommon.getProductInfo()
args = []
for product_id, p in products.iteritems():
  t = p['title']
  if t.startswith('OS X') or t.startswith('Mac OS X'):
    args.append('--product-id=' + product_id)
print ' '.join(args)
