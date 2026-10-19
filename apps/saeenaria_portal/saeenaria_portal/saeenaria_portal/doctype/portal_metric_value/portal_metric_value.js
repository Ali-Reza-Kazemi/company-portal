frappe.ui.form.on('Portal Metric Value', {
 setup(frm){frm.set_query('metric',()=>({filters:frm.doc.domain?{domain:frm.doc.domain}:{}}));},
 domain(frm){if(frm.doc.metric)frm.set_value('metric',null);}
});
