(() => {
 if(window.SaeenariaDeskCalendar)return;
 const C=window.PortalCalendar,months=['فروردین','اردیبهشت','خرداد','تیر','مرداد','شهریور','مهر','آبان','آذر','دی','بهمن','اسفند'];
 const en=v=>String(v).replace(/[۰-۹]/g,c=>String('۰۱۲۳۴۵۶۷۸۹'.indexOf(c))).replace(/[٠-٩]/g,c=>String('٠١٢٣٤٥٦٧٨٩'.indexOf(c)));
 const fa=v=>String(v).replace(/\d/g,c=>'۰۱۲۳۴۵۶۷۸۹'[c]);
 function iso(v){v=en(v).trim();if(/^\d{4}-\d{2}-\d{2}$/.test(v)){const date=new Date(v+'T12:00:00Z');if(Number.isNaN(date.getTime())||date.toISOString().slice(0,10)!==v)throw Error('تاریخ نامعتبر است');return v;}return C.toISO(v);}
 function dateText(value){return value?C.format(String(value).slice(0,10)):'';}
 function format(value,timed){if(!value)return '';const local=timed?frappe.datetime.convert_to_user_tz(value):value;const text=String(local);return dateText(text)+(timed?' '+text.slice(11,19):'');}
 function parse(value,timed){if(!value)return '';const text=en(value).trim();if(text==='Today'||text==='Now')return timed?frappe.datetime.now_datetime():frappe.datetime.get_today();let parts=text.split(/\s+/);let date;if(/^\d{1,2}[-/]\d{1,2}[-/]\d{4}$/.test(parts[0])){parts=frappe.datetime.user_to_str(text).split(/\s+/);date=parts[0];}else{date=iso(parts[0]);}if(!timed)return date;const time=parts[1]||'00:00:00';if(!/^([01]\d|2[0-3]):[0-5]\d(:[0-5]\d)?$/.test(time))frappe.throw('ساعت باید به صورت ۱۴:۳۰ یا ۱۴:۳۰:۰۰ باشد');let result=date+' '+(time.length===5?time+':00':time);if(!frappe.datetime.is_system_time_zone())result=frappe.datetime.convert_to_system_tz(result,true);return result;}
 async function picker(control){
  const timed=control.df.fieldtype==='Datetime',range=control.df.fieldtype==='DateRange';
  let selected=range?(Array.isArray(control.value)?control.value:[]):[];
  let current=(range?selected[0]:control.value)||frappe.datetime.get_today();let [year,month]=en(dateText(current)).split('/').map(Number);
  const dialog=new frappe.ui.Dialog({title:range?'انتخاب بازه شمسی':(control.df.label||'انتخاب تاریخ')+' — شمسی',fields:[{fieldname:'calendar',fieldtype:'HTML'}]});
  dialog.$wrapper.addClass('saeenaria-calendar-dialog');const wrapper=dialog.fields_dict.calendar.$wrapper;
  let time=timed?String(frappe.datetime.convert_to_user_tz(current)).slice(11,19)||frappe.datetime.now_time():null;
  let holidayMap={},drawId=0;
  async function choose(date){
   if(range){if(selected.length!==1){selected=[date];draw();return;}selected=[selected[0],date].sort();await control.set_value(selected);dialog.hide();return;}
   if(timed){const value=parse(C.format(date)+' '+time,true);await control.set_value(value);}else await control.set_value(date);
   dialog.hide();
  }
  function draw(){
   const ticket=++drawId;wrapper.empty();
   if(range)$('<div class="saeenaria-cal-range"></div>').text(selected.length===1?'تاریخ شروع: '+dateText(selected[0])+'؛ اکنون پایان را انتخاب کنید.':'ابتدا روز شروع، سپس روز پایان را انتخاب کنید.').appendTo(wrapper);
   const nav=$('<div class="saeenaria-cal-nav"></div>').appendTo(wrapper);
   const prev=$('<button type="button" aria-label="ماه قبل"><svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M9 6l6 6-6 6"/></svg></button>').appendTo(nav);
   const m=$('<select aria-label="ماه شمسی"></select>').appendTo(nav);months.forEach((v,i)=>$('<option></option>').val(i+1).text(v).appendTo(m));m.val(month);
   const y=$('<select aria-label="سال شمسی"></select>').appendTo(nav);for(let n=1500;n>=1300;n--)$('<option></option>').val(n).text(fa(n)).appendTo(y);y.val(year);
   const next=$('<button type="button" aria-label="ماه بعد"><svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M15 6l-6 6 6 6"/></svg></button>').appendTo(nav);
   prev.on('click',()=>{if(month===1){month=12;year--;}else month--;year=Math.max(1300,year);draw();});next.on('click',()=>{if(month===12){month=1;year++;}else month++;year=Math.min(1500,year);draw();});m.on('change',()=>{month=Number(m.val());draw();});y.on('change',()=>{year=Number(y.val());draw();});
   const grid=$('<div class="saeenaria-cal-grid" role="group" aria-label="روزهای ماه شمسی"></div>').appendTo(wrapper);
   ['شنبه','یکشنبه','دوشنبه','سه‌شنبه','چهارشنبه','پنجشنبه','جمعه'].forEach((day,index)=>$('<div class="saeenaria-cal-weekday"></div>').toggleClass('is-off',index>=5).text(['ش','ی','د','س','چ','پ','ج'][index]).attr('title',day).appendTo(grid));
   const first=C.toISO(`${year}/${month}/1`),offset=(new Date(first+'T12:00:00Z').getUTCDay()+1)%7;
   for(let i=0;i<offset;i++)$('<span></span>').appendTo(grid);
   const info=$('<div class="saeenaria-cal-info" aria-live="polite"></div>');let last=first;
   for(let day=1;day<=31;day++){let date;try{date=C.toISO(`${year}/${month}/${day}`);}catch(e){break;}last=date;
    const dow=new Date(date+'T12:00:00Z').getUTCDay(),weekend=dow===4||dow===5;
    const reason=holidayMap[date]||(weekend?'تعطیل کاری: '+(dow===4?'پنجشنبه':'جمعه'):'روز کاری');
    const button=$('<button type="button" class="saeenaria-cal-day"></button>').text(fa(day)).toggleClass('is-off',weekend||!!holidayMap[date]).toggleClass('is-today',date===frappe.datetime.get_today()).toggleClass('is-selected',range?selected.includes(date):String(control.value||'').startsWith(date)).attr('aria-label',`${fa(day)} ${months[month-1]} ${fa(year)} — ${reason}`).attr('title',reason).appendTo(grid);
    const min=String(control.df.min_date||'').slice(0,10),max=String(control.df.max_date||'').slice(0,10);button.prop('disabled',!!((min&&date<min)||(max&&date>max)));
    button.on('mouseenter focus',()=>info.text(reason)).on('click',()=>choose(date));
   }
   info.appendTo(wrapper);
   if(timed){const area=$('<div class="saeenaria-cal-time"></div>').appendTo(wrapper);$('<label>ساعت محلی (تهران)</label>').appendTo(area);$('<input type="time" step="1" class="form-control" aria-label="ساعت انتخاب تاریخ" dir="ltr">').val(time).appendTo(area).on('change',function(){time=this.value;});}
   const footer=$('<div class="saeenaria-cal-footer"></div>').appendTo(wrapper);$('<span class="saeenaria-cal-legend">● تعطیل کاری یا تعطیلات ثبت‌شده</span>').appendTo(footer);$('<button type="button" class="btn btn-default btn-sm">امروز</button>').appendTo(footer).on('click',()=>choose(frappe.datetime.get_today()));
   frappe.call({method:'saeenaria_portal.api.calendar_holidays',args:{start:first,end:last},quiet:true}).then(response=>{if(ticket!==drawId||!dialog.$wrapper.is(':visible'))return;const nextMap={};for(const h of response.message||[])nextMap[String(h.date).slice(0,10)]=h.title;if(JSON.stringify(nextMap)!==JSON.stringify(holidayMap)){holidayMap=nextMap;draw();}}).catch(()=>info.text('تعطیلات ثبت‌شده دریافت نشد؛ پنجشنبه و جمعه مشخص‌اند.'));
  }
  dialog.show();draw();
 }
 function makePicker(){
  this.$input.addClass('saeenaria-date-input').attr('placeholder',this.df.fieldtype==='DateRange'?'۱۴۰۵/۰۷/۰۱ تا ۱۴۰۵/۰۷/۳۰':this.df.fieldtype==='Datetime'?'۱۴۰۵/۰۷/۰۱ ۱۴:۳۰':'۱۴۰۵/۰۷/۰۱');
  const parent=this.$input.parent();parent.css('position','relative');
  this._jalaliButton=$('<button type="button" class="saeenaria-date-button" aria-label="باز کردن تقویم شمسی" title="تقویم شمسی"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true"><rect x="3" y="5" width="18" height="16" rx="3"/><path d="M7 3v4M17 3v4M3 10h18M7 14h3M14 14h3M7 17h3"/></svg></button>').appendTo(parent).on('click',()=>picker(this));
 }
 let attempts=0;
 function install(){
  const form=frappe.ui?.form;if(!form?.ControlDate||!form?.ControlDatetime||!form?.ControlDateRange){if(attempts++<100)setTimeout(install,100);return;}
  for(const [Class,timed] of [[form.ControlDate,false],[form.ControlDatetime,true]]){
   Class.prototype.make_picker=makePicker;
   Class.prototype.set_formatted_input=function(value){this.$input?.val(this.format_for_input(value));};
   Class.prototype.format_for_input=function(value){return format(value,timed);};
   Class.prototype.parse=function(value){try{return parse(value,timed);}catch(error){frappe.throw(error.message);}};
  }
  form.ControlDateRange.prototype.make_picker=makePicker;
  form.ControlDateRange.prototype.parse=function(value){if(Array.isArray(value)||value==null)return value;if(!value)return [];const parts=en(value).split(/\s+تا\s+|\s+to\s+|,/);if(parts.length!==2)frappe.throw('شروع و پایان را با «تا» جدا کنید');const dates=parts.map(v=>iso(v));if(dates[0]>dates[1])frappe.throw('پایان بازه پیش از شروع است');return dates;};
  form.ControlDateRange.prototype.format_for_input=function(a,b){return a&&b?dateText(a)+' تا '+dateText(b):'';};
  const fm=frappe.form?.formatters;if(fm){fm.Date=value=>dateText(value);fm.Datetime=value=>format(value,true);fm.DateRange=value=>Array.isArray(value)?value.map(dateText).join(' تا '):'';}
  window.SaeenariaDeskCalendar={parse,format,picker};
 }
 install();
})();
