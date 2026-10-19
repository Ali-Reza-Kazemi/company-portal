const assert=require('node:assert/strict');
const fs=require('node:fs');
require('/workspace/apps/saeenaria_portal/saeenaria_portal/public/js/calendar.js');
global.window=globalThis;
class Control{}
global.frappe={ui:{form:{ControlDate:class extends Control{},ControlDatetime:class extends Control{},ControlDateRange:class extends Control{}}},form:{formatters:{}},datetime:{user_to_str:v=>{const parts=v.split(' ');const [d,m,y]=parts[0].split('-');return [y,m,d].join('-')+(parts[1]?' '+parts[1]:'');},convert_to_user_tz:v=>v,is_system_time_zone:()=>true,get_today:()=> '2026-10-14',now_datetime:()=> '2026-10-14 14:30:00'},throw:message=>{throw Error(message);}};
require('/workspace/apps/saeenaria_portal/saeenaria_portal/public/js/desk-calendar.js');
const d=new frappe.ui.form.ControlDate(),dt=new frappe.ui.form.ControlDatetime(),range=new frappe.ui.form.ControlDateRange();
assert.equal(d.parse('۱۴۰۵/۰۷/۲۲'),'2026-10-14');
assert.equal(d.parse('2026-10-14'),'2026-10-14');
assert.equal(d.format_for_input('2026-10-14'),'۱۴۰۵/۰۷/۲۲');
assert.equal(dt.parse('۱۴۰۵/۰۷/۲۲ ۱۴:۳۰'),'2026-10-14 14:30:00');
assert.equal(dt.format_for_input('2026-10-14 14:30:00'),'۱۴۰۵/۰۷/۲۲ 14:30:00');
assert.deepEqual(range.parse('۱۴۰۵/۰۷/۲۵ تا ۱۴۰۵/۰۷/۲۹'),['2026-10-17','2026-10-21']);
assert.equal(range.format_for_input('2026-10-17','2026-10-21'),'۱۴۰۵/۰۷/۲۵ تا ۱۴۰۵/۰۷/۲۹');
assert.throws(()=>range.parse('۱۴۰۵/۰۷/۲۹ تا ۱۴۰۵/۰۷/۲۵'));
assert.throws(()=>dt.parse('۱۴۰۵/۰۷/۲۲ 25:00'));
assert.throws(()=>d.parse('۱۴۰۴/۱۲/۳۰'));
assert.equal(d.parse('۱۴۰۳/۱۲/۳۰'),'2025-03-20');
console.log('Passed: Date, Datetime, DateRange, ISO preservation, Persian numerals, reversed range, invalid time and leap dates.');

assert.equal(d.parse('14-10-2026'),'2026-10-14');
assert.equal(dt.parse('14-10-2026 14:30:00'),'2026-10-14 14:30:00');
