(() => {
 if(window.SaeenariaJalaliFormsLoaded)return;
 window.SaeenariaJalaliFormsLoaded=true;
 const months=['فروردین','اردیبهشت','خرداد','تیر','مرداد','شهریور','مهر','آبان','آذر','دی','بهمن','اسفند'];
 const fa=value=>String(value).replace(/\d/g,c=>'۰۱۲۳۴۵۶۷۸۹'[c]);
 const en=value=>value.replace(/[۰-۹]/g,c=>String('۰۱۲۳۴۵۶۷۸۹'.indexOf(c)));
 const ready=()=>window.PortalCalendar?Promise.resolve():frappe.require('/assets/saeenaria_portal/js/calendar.js');
 const parts=iso=>en(PortalCalendar.format(iso)).split('/').map(Number);
 const fields=frm=>frm.meta.fields.filter(f=>['Date','Datetime'].includes(f.fieldtype));
 function modelValue(frm,field,iso){
  if(!iso)return null;
  if(frm.fields_dict[field].df.fieldtype!=='Datetime')return iso;
  const time=frm._jalali_times[field].val();
  if(!/^\d{2}:\d{2}(:\d{2})?$/.test(time))throw Error('ساعت معتبر وارد کنید');
  return iso+' '+(time.length===5?time+':00':time);
 }
 function sync(frm,field){
  if(!window.PortalCalendar)return;
  const value=frm.doc[field]||'';
  frm._jalali_inputs?.[field]?.val(PortalCalendar.format(value.slice(0,10)));
  if(frm._jalali_times?.[field]&&value)frm._jalali_times[field].val(value.slice(11,19));
 }
 function control(frm,field){
  const df=frm.fields_dict[field].df,html=frm.fields_dict[field+'_jalali'];if(!html)return;
  const canEdit=!df.read_only&&!frm.read_only&&frappe.perm.has_perm(frm.doctype,df.permlevel||0,frm.is_new()?'create':'write',frm.doc);
  const label=df.label+' (شمسی)';const wrapper=html.$wrapper;wrapper.empty();
  const box=$('<div class="form-group"></div>').appendTo(wrapper);
  $('<label class="control-label"></label>').text(label+(df.reqd?' *':'')).appendTo(box);
  const line=$('<div style="display:flex;gap:8px;flex-wrap:wrap"></div>').appendTo(box);
  const input=$('<input type="text" class="form-control" autocomplete="off" inputmode="numeric" placeholder="۱۴۰۵/۰۷/۰۱" dir="ltr" style="flex:1;min-width:150px">').attr('aria-label',label).prop('disabled',!canEdit).appendTo(line);
  const button=$('<button type="button" class="btn btn-default">تقویم شمسی</button>').attr('aria-label','باز کردن تقویم '+label).prop('disabled',!canEdit).appendTo(line);
  frm._jalali_inputs=frm._jalali_inputs||{};frm._jalali_times=frm._jalali_times||{};frm._jalali_inputs[field]=input;
  let time=null;
  if(df.fieldtype==='Datetime'){
   time=$('<input type="time" step="1" class="form-control" dir="ltr" style="margin-top:8px">').attr('aria-label','ساعت '+df.label+' (تهران)').prop('disabled',!canEdit).val(frm.doc[field]?.slice(11,19)||frappe.datetime.now_time()).appendTo(box);
   frm._jalali_times[field]=time;
  }
  if(canEdit)$('<small class="text-muted"></small>').text(df.fieldtype==='Datetime'?'تاریخ شمسی و ساعت تهران':'سال/ماه/روز شمسی؛ مانند ۱۴۰۵/۰۷/۰۱').appendTo(box);
  async function update(){try{const iso=PortalCalendar.toISO(input.val());const value=modelValue(frm,field,iso);input.removeClass('is-invalid');await frm.set_value(field,value);}catch(error){input.addClass('is-invalid');frappe.msgprint({title:'تاریخ یا ساعت نامعتبر',message:error.message,indicator:'red'});}}
  input.on('change',update);if(time)time.on('change',update);
  button.on('click',()=>picker(frm,field,input));sync(frm,field);
 } function picker(frm,field,input) {
  let current=frm.doc[field]?.slice(0,10)||frappe.datetime.get_today();
  let [year,month]=parts(current);
  const dialog=new frappe.ui.Dialog({title:frm.fields_dict[field].df.label+' — تقویم شمسی',fields:[{fieldname:'calendar',fieldtype:'HTML'}]});
  const wrapper=dialog.fields_dict.calendar.$wrapper;
  function draw(){
   wrapper.empty();
   const navigation=$('<div style="display:flex;gap:8px;align-items:center;margin-bottom:16px"></div>').appendTo(wrapper);
   const prev=$('<button type="button" class="btn btn-default" aria-label="ماه قبل">قبلی</button>').appendTo(navigation);
   const select=$('<select class="form-control" aria-label="ماه شمسی"></select>').appendTo(navigation);
   months.forEach((name,index)=>$('<option></option>').val(index+1).text(name).appendTo(select));select.val(month);
   const yearInput=$('<input type="number" class="form-control" min="1300" max="1500" aria-label="سال شمسی" dir="ltr">').val(year).appendTo(navigation);
   const next=$('<button type="button" class="btn btn-default" aria-label="ماه بعد">بعدی</button>').appendTo(navigation);
   prev.on('click',()=>{if(month===1){year--;month=12;}else month--;if(year<1300){year=1300;month=1;}draw();});
   next.on('click',()=>{if(month===12){year++;month=1;}else month++;if(year>1500){year=1500;month=12;}draw();});
   select.on('change',()=>{month=Number(select.val());draw();});
   yearInput.on('change',()=>{const value=Number(yearInput.val());if(Number.isInteger(value)&&value>=1300&&value<=1500)year=value;draw();});
   const grid=$('<div style="display:grid;grid-template-columns:repeat(7,1fr);gap:6px;direction:rtl" role="group" aria-label="روزهای ماه شمسی"></div>').appendTo(wrapper);
   ['شنبه','یکشنبه','دوشنبه','سه‌شنبه','چهارشنبه','پنجشنبه','جمعه'].forEach(day=>$('<span style="text-align:center;font-size:11px"></span>').text(day).appendTo(grid));
   const firstISO=PortalCalendar.toISO(`${year}/${month}/1`);const offset=(new Date(firstISO+'T12:00:00Z').getUTCDay()+1)%7;
   for(let i=0;i<offset;i++)$('<span></span>').appendTo(grid);
   for(let day=1;day<=31;day++){
    let iso;try{iso=PortalCalendar.toISO(`${year}/${month}/${day}`);}catch(error){break;}
    const b=$('<button type="button" class="btn"></button>').addClass(iso===frm.doc[field]?.slice(0,10)?'btn-primary':'btn-default').text(fa(day)).attr('aria-label',`${fa(day)} ${months[month-1]} ${fa(year)}`).appendTo(grid);
    b.on('click',async()=>{await frm.set_value(field,modelValue(frm,field,iso));input.val(PortalCalendar.format(iso)).removeClass('is-invalid');dialog.hide();});
   }
   $('<button type="button" class="btn btn-default" style="margin-top:16px">امروز</button>').appendTo(wrapper).on('click',async()=>{const iso=frappe.datetime.get_today();await frm.set_value(field,modelValue(frm,field,iso));input.val(PortalCalendar.format(iso)).removeClass('is-invalid');dialog.hide();});
  }
  draw();dialog.show();
 }
 const doctypes=['Portal Action','Portal Metric Value','Portal Report','Portal Decision','Portal Template','Portal Holiday','Portal Record','Portal Metric','Portal Domain','Portal Assignment','Portal Policy'];
 for(const doctype of doctypes){
  const handlers={
   async refresh(frm){await ready();for(const df of fields(frm))control(frm,df.fieldname);},
   async validate(frm){await ready();for(const df of fields(frm)){const input=frm._jalali_inputs?.[df.fieldname];if(!input||input.prop('disabled'))continue;let value;try{value=modelValue(frm,df.fieldname,PortalCalendar.toISO(input.val()));}catch(error){frappe.throw(error.message);}if(df.reqd&&!value)frappe.throw('تاریخ '+df.label+' را وارد کنید');await frm.set_value(df.fieldname,value);}}
  };
  for(const field of ['start_date','due_date','completed_at','completion_due_date','period_start','period_end','source_updated_at','responded_at','date','record_date','planned_at','ordered_at','promised_at','actual_at'])handlers[field]=frm=>sync(frm,field);
  frappe.ui.form.on(doctype,handlers);
 }
})();