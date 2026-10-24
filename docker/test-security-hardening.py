"""Run with bench's Python; no permanent data or external source connections."""
import csv
import io
import os
from unittest.mock import patch

import frappe
from test_support import init_site
init_site()
from saeenaria_portal.csv_safety import safe_csv_cell
from saeenaria_portal.imports import import_csv
from saeenaria_portal.api import dashboard

try:
    frappe.set_user('Administrator')
    for value in ['=1+1', '  =1+1', '@SUM(1)', '＝1+1', '＋1', '－1', '＠SUM(1)', '\ttext', '\rtext', '\ntext', '+NaN', '-Infinity']:
        assert safe_csv_cell(value).startswith("'"), repr(value)
        stream = io.StringIO()
        csv.writer(stream).writerow([safe_csv_cell(value), 'normal'])
        assert next(csv.reader(io.StringIO(stream.getvalue())))[0] == "'" + value
    for value in [None, 0, -4, '-42.50', '1e3', 'کالا']:
        assert safe_csv_cell(value) == ('' if value is None else value)
    for content in ['title,title\na,b\n', 'title\n' + 'a\n' * 201, None]:
        with patch('frappe.get_doc') as create_doc:
            try:
                import_csv('Portal Action', content)
            except frappe.ValidationError:
                pass
            else:
                raise AssertionError('Invalid CSV accepted')
            create_doc.assert_not_called()
    with patch('frappe.get_doc', wraps=frappe.get_doc) as load_doc:
        result = dashboard()
        action_reads = [c for c in load_doc.call_args_list if c.args and c.args[0] == 'Portal Action']
        names = [c.args[1] for c in action_reads]
        assert len(names) == len(set(names)), 'Dashboard loaded an action twice'
        assert all(not row.is_demo for row in result['actions'])
    print('PASS CSV dangerous prefixes and round trips; numeric preservation; duplicate headers; row limit; invalid types; dashboard document reuse and demo scope')
finally:
    frappe.db.rollback()
    frappe.destroy()
