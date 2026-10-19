frappe.ui.form.on('Portal Template', {
 setup(frm){frm.set_query("responsible",()=>({query:"saeenaria_portal.api.template_responsibles",filters:{domain:frm.doc.domain,all_users:frm.doc.allow_external_responsible||0}}));},
 refresh(frm){renderWeekday(frm);renderResponsibleScope(frm);},
 async domain(frm){await frm.set_value({responsible:"",allow_external_responsible:0});renderResponsibleScope(frm);},
 frequency: renderWeekday,
 weekday(frm) { const select=frm.fields_dict.weekday_selector?.$wrapper.find('select');if(select?.length)select.val(String(frm.doc.weekday??5)); }
});
function renderWeekday(frm) {
 const field=frm.fields_dict.weekday_selector;if(!field)return;
 const wrapper=field.$wrapper;wrapper.empty();
 const standard=frm.fields_dict.frequency.$wrapper;
 function alignWidth(){const width=standard.find('select').outerWidth();if(width)wrapper.css({width:width+'px',maxWidth:'100%',marginInlineStart:'0',marginInlineEnd:'auto'});}
 alignWidth();if(field._weekdayResize)field._weekdayResize.disconnect();field._weekdayResize=new ResizeObserver(alignWidth);field._weekdayResize.observe(standard[0]);
 const id='weekday-choice-'+frm.doc.name.replace(/[^a-zA-Z0-9_-]/g,'');
 $('<label class="control-label"></label>').attr('for',id).text('روز هفته').appendTo(wrapper);
 const select=$('<select class="form-control" aria-label="روز هفته"></select>').attr('id',id).appendTo(wrapper);
 for(const [value,label] of [[5,'شنبه'],[6,'یکشنبه'],[0,'دوشنبه'],[1,'سه‌شنبه'],[2,'چهارشنبه'],[3,'پنجشنبه'],[4,'جمعه']])$('<option></option>').val(value).text(label).appendTo(select);
 const reference=standard.find('select')[0];if(reference){const style=getComputedStyle(reference);select.css({height:style.height,minHeight:style.minHeight,padding:style.padding,border:style.border,borderRadius:style.borderRadius,backgroundColor:style.backgroundColor,fontSize:style.fontSize,boxShadow:style.boxShadow});}
 select.val(String(frm.doc.weekday??5));select.prop('disabled',!(frm.perm||[]).some(p=>p.write || (frm.is_new() && p.create)));
 select.on('change',()=>frm.set_value('weekday',Number(select.val())));
 $('<div class="help-box small text-muted"></div>').text('روز اجرای برنامه هفتگی را انتخاب کنید. اگر تعطیل باشد، موعد به روز کاری بعد منتقل می‌شود.').appendTo(wrapper);
}

async function renderResponsibleScope(frm){
 renderResponsibleDropdown(frm);
 const field=frm.fields_dict.responsible_scope;if(!field)return;field.$wrapper.empty();
 frm.set_df_property('responsible','read_only',!frm.doc.domain);
 const hint=$('<div class="help-box small text-muted"></div>').text(frm.doc.domain?(frm.doc.allow_external_responsible?'همه کاربران فعال سامانه قابل انتخاب‌اند؛ این انتخاب به فرد دسترسی عمومی به حوزه نمی‌دهد.':'فقط کارکنان فعال همین حوزه قابل انتخاب‌اند.'):'ابتدا حوزه را انتخاب کنید.').appendTo(field.$wrapper);
 if(!frm.doc.domain||!(frm.perm||[]).some(p=>p.write || (frm.is_new() && p.create)))return;
 const domain=frm.doc.domain;
 const response=await frappe.call({method:'saeenaria_portal.api.template_assignment_access',args:{domain}});
 if(frm.doc.domain!==domain||!response.message)return;
 const label=$('<label style="display:flex;align-items:center;gap:8px;margin-top:10px;cursor:pointer;font-weight:normal;font-size:13px"></label>').appendTo(field.$wrapper);
 const checkbox=$('<input type="checkbox" aria-label="نمایش همه کاربران فعال" style="margin:0;accent-color:#01148b;width:16px;height:16px">').prop('checked',!!frm.doc.allow_external_responsible).appendTo(label);
 $('<span></span>').text('نمایش همه کاربران فعال (از جمله مدیران و افراد بدون حوزه)').appendTo(label);
 checkbox.on('change',async()=>{await frm.set_value({allow_external_responsible:checkbox.prop('checked')?1:0,responsible:''});renderResponsibleScope(frm);});
}

async function renderResponsibleDropdown(frm){
 const field=frm.fields_dict.responsible_selector;if(!field)return;
 const ticket=(frm._responsibleRequest||0)+1;frm._responsibleRequest=ticket;
 const wrapper=field.$wrapper;wrapper.empty();
 const reference=frm.fields_dict.frequency.$wrapper.find('select');
 const align=()=>{const width=reference.outerWidth();if(width)wrapper.css({width:width+'px',maxWidth:'100%',marginInlineStart:0,marginInlineEnd:'auto'});};
 align();if(field._resize)field._resize.disconnect();field._resize=new ResizeObserver(align);if(reference[0])field._resize.observe(reference[0]);
 const id='responsible-select-'+frm.doc.name.replace(/[^a-zA-Z0-9_-]/g,'');
 $('<label class="control-label"></label>').attr('for',id).text('مسئول').appendTo(wrapper);
 const select=$('<select class="form-control" aria-label="مسئول"></select>').attr('id',id).appendTo(wrapper);
 if(reference[0]){const style=getComputedStyle(reference[0]);select.css({height:style.height,padding:style.padding,border:style.border,borderRadius:style.borderRadius,backgroundColor:style.backgroundColor,boxShadow:style.boxShadow});}
 select.prop('disabled',true).append(new Option(frm.doc.domain?'در حال دریافت کاربران…':'ابتدا حوزه را انتخاب کنید',''));
 if(!frm.doc.domain)return;
 try{
  const response=await frappe.call({method:'saeenaria_portal.api.template_responsible_options',args:{domain:frm.doc.domain,all_users:frm.doc.allow_external_responsible||0,template:frm.is_new()?null:frm.doc.name}});
  if(frm._responsibleRequest!==ticket)return;
  const {users,current}=response.message;select.empty().append(new Option('انتخاب مسئول…',''));
  for(const user of users)select.append(new Option(user.full_name||'کاربر بدون نام',user.name));
  if(current&&current.name===frm.doc.responsible&&!users.some(u=>u.name===current.name)){
   const option=new Option((current.full_name||'مسئول فعلی')+' (مسئول فعلی؛ خارج از فهرست)',current.name);option.disabled=true;select.append(option);
  }
  select.val(frm.doc.responsible||'');select.prop('disabled',!(frm.perm||[]).some(p=>p.write||(frm.is_new()&&p.create)));
  select.on('change',()=>frm.set_value('responsible',select.val()));
 }catch(error){if(frm._responsibleRequest!==ticket)return;select.empty().append(new Option('دریافت نام کاربران ناموفق بود',''));}
}
