(()=>{
 'use strict';
 const $=id=>document.getElementById(id),base='/api/method/saeenaria_portal.purchase_reports.incoming_orders.';
 const node=(tag,value)=>{const element=document.createElement(tag);if(value!=null)element.textContent=value;return element;};
 const labels={Active:'در راه',Received:'دریافت‌شده',Cancelled:'لغوشده'};
 let page=1,serial=0,editing=null,referenceTimer,referenceSerial=0,visible=[],canEdit=false,importToken=null,importSerial=0;
 const selected=new Map(),excelBase='/api/method/saeenaria_portal.purchase_reports.incoming_excel.';
 const fa=value=>new Intl.NumberFormat('fa-IR').format(value);
 function selection(){ $('incoming-bulk').hidden=!canEdit||selected.size===0; $('incoming-selected').textContent=fa(selected.size)+' ردیف انتخاب شده';$('incoming-bulk-apply').disabled=!selected.size;const all=$('incoming-select-all'),count=visible.filter(item=>selected.has(item.name)).length;all.disabled=!canEdit||!visible.length;all.checked=Boolean(visible.length)&&count===visible.length;all.indeterminate=count>0&&count<visible.length; }
 function clearSelected(){selected.clear();selection();document.querySelectorAll('#incoming-rows input[type=checkbox]').forEach(input=>input.checked=false);}
 async function api(method,args={},post=false,endpoint=base){
  let url=endpoint+method;const options={headers:{}};
  if(post){options.method='POST';options.headers={'Content-Type':'application/json','X-Frappe-CSRF-Token':document.querySelector('meta[name=csrf-token]').content};options.body=JSON.stringify(args);}else url+='?'+new URLSearchParams(args);
  const response=await fetch(url,options),body=await response.json();
  if(!response.ok){let message='عملیات سفارش انجام نشد؛ مقادیر و دسترسی را بررسی کنید.';try{message=JSON.parse(JSON.parse(body._server_messages)[0]).message.replace(/<[^>]*>/g,'');}catch{}throw Error(message);}
  return body.message;
 }
 async function load(){
  const request=++serial;$('incoming-message').textContent='در حال دریافت سفارش‌ها…';
  try{
   const data=await api('overview',{page,search:$('incoming-search').value,status:$('incoming-filter').value});if(request!==serial)return;
   page=data.page;visible=data.rows;canEdit=data.can_edit;$('incoming-import').hidden=!canEdit;$('incoming-open-import').hidden=!canEdit;$('incoming-new').hidden=!data.can_edit;$('incoming-rows').replaceChildren();
   for(const item of data.rows){
    const row=node('tr'),checkCell=node('td'),check=node('input');check.type='checkbox';check.disabled=!canEdit;check.checked=selected.has(item.name);check.setAttribute('aria-label','انتخاب سفارش '+item.order_number+'، کالا '+item.reference_code);check.onchange=()=>{if(check.checked)selected.set(item.name,{name:item.name,modified:item.modified});else selected.delete(item.name);selection();};checkCell.append(check);row.append(checkCell);for(const value of [item.order_number,item.reference_code,new Intl.NumberFormat('fa-IR').format(item.quantity),labels[item.status],item.expected_date?PortalCalendar.format(item.expected_date):'ثبت نشده',item.supplier||'ثبت نشده'])row.append(node('td',value));
    const cell=node('td');if(data.can_edit){const button=node('button','ویرایش');button.type='button';button.onclick=()=>open(item);cell.append(button);}else cell.textContent='فقط مشاهده';row.append(cell);$('incoming-rows').append(row);
   }
   selection();$('incoming-message').textContent=data.total?'فقط سفارش‌های با وضعیت «در راه» در محاسبات لحاظ می‌شوند.':'سفارشی با این شرایط ثبت نشده است.';
   $('incoming-page').textContent='صفحه '+fa(page)+' از '+fa(data.pages)+' · '+fa(data.total)+' ردیف';$('incoming-prev').disabled=page<=1;$('incoming-next').disabled=page>=data.pages;
  }catch(error){if(request===serial)$('incoming-message').textContent=error.message;}
 }
 function open(item){
  editing=item;++referenceSerial;clearTimeout(referenceTimer);$('incoming-references').replaceChildren();
  $('incoming-form').reset();for(const field of ['order_number','reference_code','quantity','status','expected_date','supplier','notes'])$('incoming-'+field).value=item?.[field]??(field==='status'?'Active':'');
  $('incoming-expected_date').value=item?.expected_date?PortalCalendar.format(item.expected_date):'';$('incoming-expected_date').setCustomValidity('');
  $('incoming-error').textContent='';$('incoming-editor').showModal();
 }
 $('incoming-reference_code').oninput=()=>{
  clearTimeout(referenceTimer);const query=$('incoming-reference_code').value,request=++referenceSerial;if(query.trim().length<2){$('incoming-references').replaceChildren();return;}
  referenceTimer=setTimeout(async()=>{try{const response=await fetch('/api/method/saeenaria_portal.purchase_reports.product_catalog.references?'+new URLSearchParams({search:query}));if(!response.ok)return;const data=await response.json();if(request!==referenceSerial)return;$('incoming-references').replaceChildren(...data.message.filter(item=>item.item_code===item.reference_code).map(item=>new Option(item.item_title||item.item_code,item.item_code)));}catch{}},250);
 };
 $('incoming-form').onsubmit=async event=>{
  event.preventDefault();const button=$('incoming-save');button.disabled=true;
  try{
   const data=Object.fromEntries(new FormData(event.currentTarget));if(editing)data.name=editing.name;data.expected_date_jalali=data.expected_date;delete data.expected_date;
   await api('save',{data,expected_modified:editing?.modified},true);$('incoming-editor').close();clearSelected();await load();$('incoming-message').textContent='سفارش ذخیره شد؛ محاسبه مجدد گزارش‌ها در صف قرار گرفت.';
  }catch(error){$('incoming-error').textContent=error.message;}finally{button.disabled=false;}
 };
 $('incoming-open-import').onclick=()=>$('incoming-import').showModal();
 $('incoming-close-import').onclick=()=>$('incoming-import').close();
 $('incoming-import').addEventListener('cancel',event=>{if($('incoming-file').disabled)event.preventDefault();});
 $('incoming-cancel').onclick=()=>$('incoming-editor').close();$('incoming-new').onclick=()=>open(null);
 $('incoming-filters').onsubmit=event=>{event.preventDefault();page=1;clearSelected();load();};$('incoming-filter').onchange=()=>{page=1;clearSelected();load();};
 $('incoming-prev').onclick=()=>{if(page>1){page--;load();}};$('incoming-next').onclick=()=>{page++;load();};
 $('incoming-select-all').onchange=event=>{for(const item of visible){if(event.target.checked)selected.set(item.name,{name:item.name,modified:item.modified});else selected.delete(item.name);}for(const [index,input] of [...document.querySelectorAll('#incoming-rows input[type=checkbox]')].entries())input.checked=selected.has(visible[index].name);selection();};
 $('incoming-clear-selected').onclick=clearSelected;
 $('incoming-bulk-apply').onclick=async()=>{const button=$('incoming-bulk-apply');button.disabled=true;try{const result=await api('bulk_status',{selections:[...selected.values()],status:$('incoming-bulk-status').value},true);clearSelected();await load();$('incoming-message').textContent=fa(result.updated)+' سفارش به‌روز شد؛ محاسبه مجدد در صف قرار گرفت.';}catch(error){$('incoming-message').textContent=error.message;}finally{selection();}};
 function resetImport(){++importSerial;importToken=null;$('incoming-import-preview').replaceChildren();$('incoming-import-preview').hidden=true;$('incoming-import-commit').hidden=true;$('incoming-import-cancel').hidden=true;$('incoming-import-message').textContent='';}
 $('incoming-file').onchange=resetImport;$('incoming-import-cancel').onclick=resetImport;
 $('incoming-preview-file').onclick=async()=>{
  resetImport();const ticket=importSerial,button=$('incoming-preview-file'),file=$('incoming-file').files[0];button.disabled=true;
  try{if(!file||!file.name.toLowerCase().endsWith('.xlsx')||file.size>5000000)throw Error('یک فایل XLSX با حداکثر اندازه پنج مگابایت انتخاب کنید.');
   const content=await new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(String(reader.result).split(',')[1]);reader.onerror=()=>reject(Error('خواندن فایل ممکن نشد'));reader.readAsDataURL(file);});
   const result=await api('preview',{content},true,excelBase);if(ticket!==importSerial)return;importToken=result.token;
   const table=node('table'),head=node('thead'),heading=node('tr'),body=node('tbody');
   for(const label of result.errors.length?['ردیف اکسل','خطا']:['ردیف اکسل','عملیات','کد سفارش','کد مرجع','مانده تعداد','وضعیت','تاریخ شمسی'])heading.append(node('th',label));head.append(heading);table.append(head,body);
   for(const item of result.errors.length?result.errors:result.rows){const line=node('tr'),v=item.values;for(const value of result.errors.length?[item.row,item.message]:[item.row,item.action,v.order_number,v.reference_code,v.quantity,labels[v.status],v.expected_date?PortalCalendar.format(v.expected_date):''])line.append(node('td',value));body.append(line);}
   $('incoming-import-preview').replaceChildren(table);$('incoming-import-preview').hidden=false;$('incoming-import-cancel').hidden=false;$('incoming-import-commit').hidden=!importToken;
   $('incoming-import-message').textContent=result.errors.length?fa(result.errors.length)+' خطا؛ هیچ ردیفی ذخیره نشده است. فایل را اصلاح و دوباره بررسی کنید.':fa(result.rows.length)+' ردیف معتبر است. با تأیید شما ردیف‌های موجود ویرایش و ردیف‌های جدید ثبت می‌شوند.';
  }catch(error){if(ticket===importSerial)$('incoming-import-message').textContent=error.message;}finally{button.disabled=false;}
 };
 $('incoming-import-commit').onclick=async()=>{const button=$('incoming-import-commit');button.disabled=true;$('incoming-close-import').disabled=true;$('incoming-file').disabled=true;$('incoming-preview-file').disabled=true;$('incoming-import-cancel').disabled=true;try{const result=await api('commit',{token:importToken},true,excelBase);resetImport();clearSelected();page=1;await load();$('incoming-import-message').textContent=fa(result.created)+' ردیف جدید و '+fa(result.updated)+' ردیف ویرایش شد؛ محاسبه مجدد در صف قرار گرفت.';}catch(error){$('incoming-import-message').textContent=error.message;}finally{button.disabled=false;$('incoming-close-import').disabled=false;$('incoming-file').disabled=false;$('incoming-preview-file').disabled=false;$('incoming-import-cancel').disabled=false;}};
 window.PurchaseIncoming={load};
})();
