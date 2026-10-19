frappe.ui.form.on('Portal Report', {
 async refresh(frm) {
  const wrapper=frm.fields_dict.snapshot_view?.$wrapper;if(!wrapper)return;
  wrapper.empty();
  const panel=$('<section dir="rtl" class="report-snapshot-panel"></section>').appendTo(wrapper);
  $('<h4 style="font-size:16px;margin-bottom:12px">ریز شاخص‌های گزارش</h4>').appendTo(panel);
  if(!frm.doc.snapshot){$('<p class="text-muted"></p>').text('پس از تغییر وضعیت به «ارسال‌شده» و ذخیره، مقادیر شاخص‌های این حوزه و دوره در این قسمت ثبت می‌شوند.').appendTo(panel);return;}
  let rows;try{rows=JSON.parse(frm.doc.snapshot);if(!Array.isArray(rows))throw Error();}catch(error){$('<p class="text-danger"></p>').text('اطلاعات ثبت‌شده قابل نمایش نیست؛ برای بررسی با مدیر سامانه تماس بگیرید.').appendTo(panel);return;}
  if(!window.PortalCalendar)await frappe.require('/assets/saeenaria_portal/js/calendar.js');
  const status={Draft:'پیش‌نویس',Submitted:'ارسال‌شده','Needs Revision':'نیازمند اصلاح',Approved:'تأییدشده'};
  const valid={Valid:'معتبر',Provisional:'موقت',Missing:'ناموجود'};
  const signals={'Green':'مطلوب','Red':'نامطلوب','Amber':'هشدار','Missing':'ناموجود','No Target':'هدف تعیین نشده','No Thresholds':'آستانه تعیین نشده','Provisional':'داده موقت'};
  const number=v=>v===null||v===undefined?'ناموجود':typeof v==='number'?new Intl.NumberFormat('fa-IR',{maximumFractionDigits:6}).format(v):String(v);
  const date=v=>v?PortalCalendar.format(String(v).slice(0,10)):'';
  const updated=v=>v?date(v)+(String(v).length>10?' — '+String(v).slice(11,19):''):'ثبت نشده';
  const info=$('<div style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:12px"></div>').appendTo(panel);
  for(const text of [status[frm.doc.status]||frm.doc.status,frm.doc.is_demo?'داده آزمایشی':'داده واقعی',date(frm.doc.period_start)+' تا '+date(frm.doc.period_end),new Intl.NumberFormat('fa-IR').format(rows.length)+' مقدار شاخص'])$('<span style="background:var(--subtle-fg,#edf4f5);padding:6px 10px;border-radius:6px"></span>').text(text).appendTo(info);
  $('<p class="text-muted" style="line-height:1.9"></p>').text('این جدول مقادیر ثبت‌شده هنگام ارسال گزارش را نشان می‌دهد. تغییر مقدار شاخص در آینده، این نسخه گزارش را تغییر نمی‌دهد. دستاوردها، موانع و برنامه بعد در فیلدهای بالای فرم نوشته شده‌اند.').appendTo(panel);
  if(!rows.length){$('<p></p>').text('در زمان ارسال، برای این حوزه، بازه و نوع داده، مقدار شاخصی ثبت نشده بود.').appendTo(panel);return;}
  const missing=rows.filter(r=>r.actual===null||r.actual===undefined||r.data_status==='Missing').length;
  const noTarget=rows.filter(r=>r.target===null||r.target===undefined).length;
  $('<p></p>').text(new Intl.NumberFormat('fa-IR').format(missing)+' مقدار ناموجود · '+new Intl.NumberFormat('fa-IR').format(noTarget)+' مقدار بدون هدف؛ بدون هدف درباره موفقیت شاخص قضاوت نمی‌شود.').appendTo(panel);
  const scroll=$('<div style="overflow:auto;border:1px solid var(--border-color,#dce6e9);border-radius:8px"></div>').appendTo(panel);
  const table=$('<table class="table table-bordered" style="margin:0;min-width:900px;font-size:13px"></table>').appendTo(scroll);
  const head=$('<tr></tr>').appendTo($('<thead style="background:var(--subtle-fg,#edf4f5)"></thead>').appendTo(table));
  ['نام شاخص','دوره','مقدار واقعی','واحد','وضعیت داده','هدف','تغییر نسبت به دوره قبل','ارزیابی','منبع','به‌روزرسانی منبع'].forEach(label=>$('<th style="white-space:nowrap"></th>').text(label).appendTo(head));
  const body=$('<tbody></tbody>').appendTo(table);
  for(const row of rows){
   const tr=$('<tr></tr>').appendTo(body),hasTarget=row.target!==null&&row.target!==undefined;
   const actual=row.data_status==='Missing'?null:row.actual;
   const cells=[row.title||'شاخص بدون عنوان',date(row.period_start)+' تا '+date(row.period_end),number(actual),row.unit||'—',valid[row.data_status]||row.data_status||'ثبت نشده',hasTarget?number(row.target):'تعیین نشده',row.change===null||row.change===undefined?'قابل محاسبه نیست':number(row.change),!hasTarget?'هدف تعیین نشده':signals[row.signal]||'ارزیابی نشده',row.source||'ثبت نشده',updated(row.updated_at)];
   cells.forEach(text=>$('<td style="vertical-align:middle;line-height:1.8"></td>').text(text).appendTo(tr));
  }
 }
});
