(()=>{
'use strict';
const $=id=>document.getElementById(id),el=(tag,text)=>{const node=document.createElement(tag);if(text!=null)node.textContent=text;return node;};
const fmt=value=>value==null?'ناموجود':typeof value==='number'?new Intl.NumberFormat('fa-IR',{maximumFractionDigits:2}).format(value):value;
const jalaliDate=value=>{if(!value)return 'ناموجود';const date=new Date(String(value).slice(0,10)+'T12:00:00Z');return Number.isNaN(date.getTime())?'ناموجود':new Intl.DateTimeFormat('fa-IR-u-ca-persian',{year:'numeric',month:'2-digit',day:'2-digit',timeZone:'Asia/Tehran'}).format(date);};
const monthValue=value=>String(value||'').replace(/[۰-۹]/g,c=>'۰۱۲۳۴۵۶۷۸۹'.indexOf(c));
const columns=[['seller_name','کارشناس'],['channel_label','کانال'],['target','تارگت ماه (ریال)'],['actual','فروش واقعی (ریال)'],['facilitator_cost','پورسانت آسان ساز فروش (ریال)'],['after_facilitator','فروش پس از کسر پورسانت آسان‌ساز (ریال)'],['achievement','تحقق تارگت (%)'],['invoice_count','تعداد فاکتور'],['repair_invoice_count','تعداد فاکتور تعمیرات'],['average_invoice','میانگین فاکتور (ریال)'],['new_customers','مشتری جدید'],['conversion','نرخ تبدیل (%)'],['followup','نرخ پیگیری (%)'],['retention','نرخ حفظ مشتری (%)'],['discount','میانگین تخفیف (%)'],['discount_limit','حد مجاز تخفیف (%)'],['discount_deviation','انحراف تخفیف (واحد درصد)']];
let state,visible=[],pollTimer,elapsedTimer,startedAt=0,loading=false,serial=0,editingRuleId='';
const selection=new Set();
const pageTabs=[...document.querySelectorAll('[data-sales-page]')];
function showPageTab(key){
 for(const button of pageTabs){const selected=button.dataset.salesPage===key;button.setAttribute('aria-selected',String(selected));button.tabIndex=selected?0:-1;$(button.getAttribute('aria-controls')).hidden=!selected;}
}
for(const [index,button]of pageTabs.entries()){
 button.onclick=()=>showPageTab(button.dataset.salesPage);
 button.onkeydown=event=>{let next;if(event.key==='ArrowLeft')next=(index+1)%pageTabs.length;else if(event.key==='ArrowRight')next=(index-1+pageTabs.length)%pageTabs.length;else if(event.key==='Home')next=0;else if(event.key==='End')next=pageTabs.length-1;else return;event.preventDefault();showPageTab(pageTabs[next].dataset.salesPage);pageTabs[next].focus();};
}
function canonical(id){return state?.snapshot?.crm_metadata?.seller_aliases?.[id]||state?.directory?.seller_aliases?.[id]||id;}
function allNames(){return state?.snapshot?.sellers||state?.directory?.sellers||{};}
function activeNames(){return state?.snapshot?.crm_metadata?.seller_choices||state?.directory?.seller_choices||allNames();}
function historicalChoices(selected=$('rule-seller').value){const names={...activeNames()};if($('show-inactive').checked)for(const [id,name]of Object.entries(allNames()))names[canonical(id)]=name;if(selected&&!names[selected])names[selected]=allNames()[selected]||'کارشناس سابق';return names;}
function inactive(id){return (state?.snapshot?.crm_metadata?.inactive_sellers||[]).includes(id);}
function error(error,target='status'){$(target).textContent=error.message;}
async function api(method,args={},post=false){
 const response=await fetch('/api/method/saeenaria_portal.sales_reports.service.'+method+(post?'':'?'+new URLSearchParams(args)),post?{method:'POST',headers:{'Content-Type':'application/json','X-Frappe-CSRF-Token':document.querySelector('meta[name="csrf-token"]').content},body:JSON.stringify(args)}:{});
 const result=await response.json();if(!response.ok||result.exc)throw Error('عملیات انجام نشد؛ ورودی‌ها را بررسی و صفحه را دوباره دریافت کنید.');return result.message;
}
function options(select,values,current=select.value){
 select.replaceChildren();for(const [value,label]of Object.entries(values)){const option=el('option',label);option.value=value;select.append(option);}
 if(Object.hasOwn(values,current))select.value=current;
 select.syncSearch?.();
}
const cleanName=value=>String(value||'').replace(/[\u061c\u200e\u200f\u202a-\u202e\u2066-\u2069\ufeff]/g,'').trim();
const searchText=value=>monthValue(cleanName(value)).normalize('NFKC').replace(/ي/g,'ی').replace(/ك/g,'ک').replace(/\u200c/g,' ').replace(/\s+/g,' ').toLocaleLowerCase('fa');
function searchableSelect(id){
 const select=$(id),wrap=el('div'),input=el('input'),list=el('div');wrap.className='sales-combobox';input.id=id+'-search';input.setAttribute('aria-label',select.closest('label').firstChild.textContent.trim());input.setAttribute('role','combobox');input.setAttribute('aria-autocomplete','list');input.setAttribute('aria-controls',id+'-suggestions');input.setAttribute('aria-expanded','false');input.placeholder=id==='rule-customer'?'جستجو با نام یا کد مشتری…':'جستجو و انتخاب…';input.autocomplete='off';input.required=true;list.id=id+'-suggestions';list.className='sales-combobox-list';list.setAttribute('role','listbox');list.hidden=true;select.hidden=true;select.required=false;select.after(wrap);wrap.append(input,list);
 let choices=[],matches=[],active=-1;
 const close=()=>{list.hidden=true;input.setAttribute('aria-expanded','false');input.removeAttribute('aria-activedescendant');active=-1;};
 const choose=choice=>{select.value=choice.value;input.value=choice.label;input.setCustomValidity('');close();select.dispatchEvent(new Event('change',{bubbles:true}));};
 const highlight=()=>{[...list.querySelectorAll('[role=option]')].forEach((node,index)=>node.setAttribute('aria-selected',String(index===active)));if(active>=0){input.setAttribute('aria-activedescendant',id+'-choice-'+active);list.children[active]?.scrollIntoView({block:'nearest'});}};
 const show=()=>{const term=searchText(input.value);matches=choices.filter(o=>searchText(o.label+' '+o.value).includes(term)).slice(0,60);list.replaceChildren();active=-1;for(const [index,choice]of matches.entries()){const option=el('div',choice.label);option.id=id+'-choice-'+index;option.setAttribute('role','option');option.setAttribute('aria-selected','false');option.onmousedown=event=>event.preventDefault();option.onclick=()=>choose(choice);list.append(option);}if(!matches.length)list.append(el('p','موردی پیدا نشد؛ نام یا کد دیگری وارد کنید.'));list.hidden=false;input.setAttribute('aria-expanded','true');};
 select.syncSearch=()=>{choices=[...select.options].filter(o=>o.value).map(o=>({value:o.value,label:cleanName(o.text)+(id==='rule-customer'?' — کد '+o.value:'')})).sort((a,b)=>a.label.localeCompare(b.label,'fa'));if(document.activeElement===input&&!select.value){show();return;}input.value=choices.find(o=>o.value===select.value)?.label||'';input.setCustomValidity('');close();select.dispatchEvent(new Event('change',{bubbles:true}));};
 input.onfocus=()=>{input.select();show();};
 input.oninput=()=>{select.value='';input.setCustomValidity('یکی از نتایج جستجو را انتخاب کنید.');show();};
 input.onkeydown=event=>{if(event.key==='Escape'){close();return;}if(event.key==='ArrowDown'||event.key==='ArrowUp'){event.preventDefault();if(list.hidden)show();active=Math.max(0,Math.min(matches.length-1,active+(event.key==='ArrowDown'?1:-1)));highlight();}else if(event.key==='Enter'&&!list.hidden){event.preventDefault();if(active>=0&&matches[active])choose(matches[active]);else if(matches.length===1)choose(matches[0]);}};
 input.onblur=()=>close();
 select.syncSearch();
}

function monthInvoices(){return (state?.snapshot?.invoices||[]).filter(row=>row.date>=state.start&&row.date<=state.end);}
function monthSuggestions(){const suggestions=state?.snapshot?.suggestions||{};return Object.fromEntries(monthInvoices().filter(row=>!row.excluded&&!row.is_repair&&!row.mapped&&suggestions[row.key]).map(row=>[row.key,suggestions[row.key]]));}
function ruleMode(id=''){editingRuleId=id;$('save-customer-rule').textContent=id?'ذخیره اصلاحات':'ثبت تغییر مسئول مشتری';$('cancel-customer-rule').hidden=!id;}
function table(cols,rows){
 const result=el('table'),head=el('thead'),header=el('tr'),body=el('tbody');
 for(const [,label]of cols)header.append(el('th',label));head.append(header);
 for(const row of rows){const tr=el('tr');for(const [key]of cols)tr.append(el('td',fmt(row[key])));body.append(tr);}
 result.append(head,body);return result;
}
function reportColumns(){return [...columns,...Object.entries(state?.groups||{}).map(([key,label])=>['group_'+key,label+' (تعداد خالص)']),['unclassified_quantity','تعداد بدون گروه خرید'],['total_quantity','جمع کالای فروخته‌شده'],['coverage','پوشش مالی']];}
function busy(value,title='در حال دریافت گزارش…',detail=''){
 loading=value;$('loading-panel').hidden=!value;$('refresh').disabled=value;$('refresh').textContent=value?'در حال دریافت و محاسبه…':'دریافت و محاسبه مجدد';
 $('report-table').setAttribute('aria-busy',String(value));$('loading-title').textContent=title;$('loading-detail').textContent=detail;
 if(value&&!startedAt){startedAt=Date.now();elapsedTimer=setInterval(()=>{$('loading-elapsed').textContent='زمان سپری‌شده: '+fmt(Math.floor((Date.now()-startedAt)/1000))+' ثانیه؛ می‌توانید سایر بخش‌های صفحه را استفاده کنید.';},1000);}
 if(!value){clearInterval(elapsedTimer);startedAt=0;$('loading-elapsed').textContent='';}
}
function draw(){
 const snap=state.snapshot,names=allNames(),choices=activeNames(),showInactive=$('show-inactive').checked,filterNames={...choices};
 if(showInactive)for(const row of snap?.rows||[])filterNames[canonical(row.seller)]=row.seller_name||names[row.seller]||'کارشناس سابق';
 options($('seller-filter'),{'':'همه کارشناسان فعال',...filterNames});
 options($('target-seller'),{'':'انتخاب کارشناس فعال',...choices});
 const channel=$('channel').value,seller=$('seller-filter').value;
 visible=(snap?.rows||[]).filter(row=>(showInactive||!inactive(row.seller))&&(!channel||row.channel===channel)&&(!seller||canonical(row.seller)===seller)).map(row=>{
  const result={...row,channel_label:state.channels[row.channel],...Object.fromEntries(Object.entries(row.groups||{}).map(([key,value])=>['group_'+key,value])),coverage:row.financial_complete?'انتساب اسناد ماه کامل است':row.actual==null?'داده مالی برای این ردیف موجود نیست':'انتساب اسناد همین ماه ناقص است'};
  if(!row.financial_complete&&!row.invoice_count)for(const key of ['actual','invoice_count','new_customers','total_quantity','unclassified_quantity',...Object.keys(row.groups||{}).map(key=>'group_'+key)])result[key]=null;
  return result;
 });
 $('report-table').replaceChildren(table(reportColumns(),visible));if(!visible.length)$('report-table').append(el('p','برای این ماه و فیلتر داده‌ای ثبت نشده است. می‌توانید دریافت از منابع را شروع کنید یا تارگت این ماه را ثبت کنید.'));
 const repairTotals=new Map();for(const invoice of snap?.repair_rows||[]){if(invoice.excluded||!invoice.repair_seller||channel&&invoice.repair_channel!==channel||seller&&canonical(invoice.repair_seller)!==seller)continue;const key=invoice.repair_seller+'|'+invoice.repair_channel,row=repairTotals.get(key)||{repair_seller_name:invoice.repair_seller_name,channel_label:state.channels[invoice.repair_channel],repair_invoice_count:0,gross:0,discount:0,repair_sales:0,tax:0,total_amount:0,repair_facilitator_amount:0};row.repair_invoice_count++;for(const field of ['gross','discount','amount','tax','total_amount','repair_facilitator_amount'])row[field]+=Number(invoice[field]||0);row.repair_sales=row.amount;repairTotals.set(key,row);}const repairSummary=[...repairTotals.values()].map(row=>({...row,discount_percent:row.gross?100*row.discount/row.gross:null}));
 $('repair-performance-table').replaceChildren(repairSummary.length?table([['repair_seller_name','کارشناس'],['channel_label','کانال / نوع مشتری'],['repair_invoice_count','تعداد فاکتور تعمیرات'],['gross','مبلغ قبل از تخفیف (ریال)'],['discount','جمع تخفیف (ریال)'],['discount_percent','میانگین تخفیف (%)'],['repair_sales','فروش تعمیرات پس از تخفیف (ریال)'],['tax','مالیات (ریال)'],['total_amount','جمع نهایی (ریال)'],['repair_facilitator_amount','پورسانت آسان‌ساز (ریال)']],repairSummary):el('p','فاکتور تعمیراتیِ دارای کارشناس تأییدشده برای فیلترهای فعلی وجود ندارد.'));
 $('summary').replaceChildren(el('p','ردیف کارشناس / کانال: '+fmt(visible.length)),el('p','⚠ بدون پیش‌فاکتور یا ارتباط نامشخص: '+fmt(monthInvoices().filter(row=>['missing','unresolved'].includes(row.quotation_status)).length)),el('p','سند فروش/برگشت بدون انتساب این ماه: '+fmt(monthInvoices().filter(row=>!row.excluded&&!row.is_repair&&!row.mapped).length)),el('p','نوع کالای بدون گروه خرید: '+fmt(snap?.unclassified_products?.length)));
 $('freshness').textContent=snap?'گزارش ماه '+state.month+' · آخرین دریافت: '+snap.captured_at+' · مبالغ ریال است.':'ماه گزارش: '+state.month;
 $('status').textContent=state.busy?'دریافت اطلاعات در پس‌زمینه در حال اجراست.':state.error?'دریافت اخیر ناموفق بود؛ آخرین داده موفق حفظ شد.':!state.api_configured?'کلید API دیدار را در فرم اتصال ثبت کنید.':snap?'داده‌های گزارش آماده است. تارگت و سقف تخفیف از آخرین تنظیمات ثبت‌شده خوانده می‌شوند.':'برای این ماه هنوز داده‌ای دریافت نشده است.';
 $('api-panel').hidden=!state.can_configure_api;
 $('catalog-status').textContent='گروه‌های خرید: '+Object.values(state.groups||{}).join('، ');
 drawInvoices();
 drawCustomerRules();
 drawCustomerGroups();
 drawFacilitators();
 if(state.busy){busy(true,'در حال دریافت و محاسبه ماه '+state.month,state.job?.detail||'در انتظار پردازشگر گزارش');schedulePoll();}
}
async function load(showLoading=true){
 const requestId=++serial,month=monthValue($('month').value);
 if(showLoading)busy(true,'در حال بازکردن گزارش '+month,'آخرین گزارش ذخیره‌شده بررسی می‌شود.');
 try{
  const result=await api('report',month?{month}:{});
  if(requestId!==serial)return;
  if(state?.month!==result.month){selection.clear();$('select-suggestions').checked=false;}
  state=result;$('month').value=result.month;if(!$('target-month').value)$('target-month').value=result.month;
  for(const key of selection)if(!monthSuggestions()[key])selection.delete(key);
  draw();if(!result.busy)busy(false);
 }catch(e){if(requestId===serial){busy(false);error(e);}throw e;}
}
function schedulePoll(){
 clearTimeout(pollTimer);pollTimer=setTimeout(async()=>{try{await load(false);}catch(e){error(e);}},3000);
}
async function loadTargets(){
 if(!state)return;
 const result=await api('target_data',{month:monthValue($('target-month').value)});state.revision=result.revision;
 $('target-month').value=result.month;
 $('targets').replaceChildren(table([['seller_name','کارشناس'],['channel_label','کانال'],['target','تارگت (ریال)'],['discount_limit','سقف تخفیف (%)']],result.targets.map(row=>({...row,seller_name:allNames()[row.seller]||allNames()[canonical(row.seller)]||'کارشناس سابق',channel_label:state.channels[row.channel]}))));
}
const invoiceDialog=el('dialog'),invoiceDialogHeader=el('div'),invoiceDialogTitle=el('h2'),invoiceDialogClose=el('button','بستن'),invoiceDialogBody=el('div');
invoiceDialog.className='sales-invoice-dialog';invoiceDialogTitle.id='invoice-detail-title';invoiceDialog.setAttribute('aria-labelledby',invoiceDialogTitle.id);invoiceDialogHeader.className='sales-invoice-dialog-header';invoiceDialogClose.type='button';invoiceDialogClose.onclick=()=>invoiceDialog.close();invoiceDialogHeader.append(invoiceDialogTitle,invoiceDialogClose);invoiceDialog.append(invoiceDialogHeader,invoiceDialogBody);document.body.append(invoiceDialog);
let detailRequest=0;
invoiceDialog.addEventListener('close',()=>{detailRequest++;});
async function showInvoiceDetails(row,editCommission=false){
 const request=++detailRequest,month=state.month;invoiceDialogTitle.textContent='جزئیات فاکتور '+row.number;invoiceDialogBody.replaceChildren(el('p','در حال دریافت جزئیات…'));invoiceDialog.showModal();
 try{
  const data=await api('invoice_details',{month,key:row.key});if(request!==detailRequest||!invoiceDialog.open)return;
  invoiceDialogTitle.textContent=(data.document_type==='Return'?'جزئیات برگشت از فروش ':'جزئیات فاکتور ')+data.number;
  const info=el('p',data.customer+' · کد مشتری: '+data.customer_id+' · تاریخ: '+jalaliDate(data.date)+' · '+(data.quotation_number?'پیش‌فاکتور '+data.quotation_number:data.quotation_status==='missing'?'⚠ بدون پیش‌فاکتور سپیدار':'پیش‌فاکتور: نامشخص'));
  const scroll=el('div');scroll.className='sales-invoice-detail-scroll';scroll.tabIndex=0;scroll.setAttribute('aria-label','اقلام فاکتور؛ برای مشاهده ستون‌ها پیمایش کنید');
  scroll.append(table([['index','ردیف'],['code','کد کالا'],['title','نام کالا'],['quantity','تعداد'],['unit','واحد'],['fee','قیمت واحد'],['gross','مبلغ قبل از تخفیف'],['discount','تخفیف'],['amount','پس از تخفیف، قبل از مالیات'],['tax','مالیات و عوارض'],['addition','اضافات'],['total','مبلغ نهایی']],data.items));
  const totals=el('dl');totals.className='sales-invoice-detail-totals';for(const [key,label]of [['gross','جمع قبل از تخفیف'],['discount','جمع تخفیف'],['amount','جمع قبل از مالیات'],['tax','مالیات و عوارض'],['addition','اضافات'],['total','جمع نهایی']])totals.append(el('dt',label),el('dd',fmt(data.totals[key])+' ریال'));
  const creator=el('p','ثبت‌کنندهٔ '+(data.document_type==='Return'?'برگشت از فروش':'فاکتور')+' در سپیدار: '+(data.creator_name||data.creator_username||(data.creator_status==='unavailable'?'دریافت نام ثبت‌کننده ممکن نشد؛ دوباره تلاش کنید.':'نام ثبت‌کننده در دسترس نیست'))+(data.creator_name&&data.creator_username?' ('+data.creator_username+')':''));
  const quotationCreator=el('p','ثبت‌کنندهٔ پیش‌فاکتور در سپیدار: '+(data.quotation_creator_name||data.quotation_creator_username||(data.quotation_creator_status==='not_applicable'?'برای برگشت از فروش کاربرد ندارد':data.quotation_creator_status==='missing'?'پیش‌فاکتور مرتبط ندارد':data.quotation_creator_status==='unavailable'?'دریافت نام ثبت‌کننده ممکن نشد؛ دوباره تلاش کنید.':'نام ثبت‌کننده در دسترس نیست'))+(data.quotation_creator_name&&data.quotation_creator_username?' ('+data.quotation_creator_username+')':''));
  invoiceDialogBody.replaceChildren(info,creator,quotationCreator,el('p','همه مبالغ ریال هستند. تعداد و مبالغ برگشت از فروش با علامت منفی نمایش داده می‌شوند.'),scroll,totals,el('small','منبع: آخرین دریافت سپیدار در پورتال · '+(data.captured_at||'زمان نامشخص')));
  const commission=facilitatorInvoiceForm(data,month);
  if(editCommission){invoiceDialogBody.prepend(commission);commission.querySelector('input[type="number"]').focus();}else invoiceDialogBody.append(commission);
 }catch(e){if(request===detailRequest&&invoiceDialog.open)invoiceDialogBody.replaceChildren(el('p','جزئیات دریافت نشد. پنجره را ببندید و دوباره تلاش کنید؛ در صورت تکرار، داده‌های ماه را مجدداً دریافت کنید.'));}
}
function invoiceDetailButtons(container,rows){[...$(container).querySelectorAll('tbody tr')].forEach((tr,index)=>{const row=rows[index],button=el('button',row.number+' · جزئیات');button.type='button';button.className='sales-invoice-detail-button';button.setAttribute('aria-label','جزئیات فاکتور '+row.number+' '+row.customer);button.onclick=()=>showInvoiceDetails(row);tr.cells[0].replaceChildren(button);const saleType=el('small','نوع فاکتور: '+(row.sale_type_title||'دریافت مجدد لازم است'));saleType.className='sales-cell-note';tr.cells[0].append(saleType);if(row.facilitator?.name){const commission=el('button','ویرایش مبلغ پورسانت');commission.type='button';commission.className='sales-invoice-detail-button';commission.setAttribute('aria-label','ویرایش مبلغ پورسانت فاکتور '+row.number+' '+row.customer);commission.onclick=()=>showInvoiceDetails(row,true);const applied=el('small','پورسانت: '+fmt(row.facilitator.amount)+' ریال · '+(row.facilitator.manual?'مبلغ دستی':'درصد مشتری'));applied.className='sales-cell-note';tr.cells[0].append(applied,commission);}});} 
function facilitatorInvoiceForm(data,month){
 const box=el('section'),value=data.facilitator||{},form=el('form'),name=el('input'),amount=el('input'),note=el('input'),save=el('button','ذخیره مبلغ دستی همین فاکتور'),reset=el('button','بازگشت به درصد مشتری'),status=el('p');
 box.append(el('h3','پورسانت آسان ساز فروش'),el('p','آسان‌ساز: '+(value.name||'ثبت نشده')+' · درصد مشتری: '+fmt(value.rate||0)+'٪ · محاسبه درصدی: '+fmt(value.calculated||0)+' ریال · مبلغ اعمال‌شده: '+fmt(value.amount||0)+' ریال ('+(value.manual?'دستی':'درصدی')+')'));box.append(el('p','مبلغ دستی فقط برای همین فاکتور اعمال می‌شود؛ درصد مشتری و پورسانت سایر فاکتورها تغییر نمی‌کند. مبلغ را به ریال وارد کنید؛ صفر هم قابل ثبت است.'));form.className='sales-form';
 name.value=value.name||'';name.required=true;name.maxLength=140;amount.type='number';amount.step='1';amount.required=true;amount.value=value.amount||0;if(data.document_type==='Return')amount.max='0';else amount.min='0';note.value=value.note||'';note.maxLength=500;
 for(const [title,input]of [['نام آسان ساز فروش',name],['مبلغ دستی پورسانت همین فاکتور (ریال)',amount],['توضیح تغییر',note]]){const label=el('label',title);label.append(input);form.append(label);}reset.type='button';reset.disabled=!value.manual;form.append(save,reset);status.setAttribute('role','status');
 async function persist(remove){save.disabled=true;reset.disabled=true;status.textContent='در حال ذخیره…';try{await api('save',{kind:'facilitator_invoice',values:{month,key:data.key,name:name.value,amount:amount.value,note:note.value,remove},revision:data.revision},true);invoiceDialog.close();await load(false);$('assignment-status').textContent=remove?'مبلغ دستی حذف شد؛ درصد مشتری اعمال می‌شود.':'پورسانت آسان ساز فروش برای همین فاکتور ذخیره شد.';}catch(e){status.textContent='ذخیره نشد؛ ورودی‌ها را بررسی کنید و جزئیات فاکتور را دوباره باز کنید.';save.disabled=false;reset.disabled=!value.manual;}}
 form.onsubmit=event=>{event.preventDefault();persist(false);};reset.onclick=()=>persist(true);box.append(form,status);return box;
}
function drawFacilitators(){
 $('facilitator-totals').replaceChildren(table([['name','آسان ساز فروش'],['sales','پورسانت فروش منتسب (ریال)'],['repairs','پورسانت تعمیرات (ریال)'],['unassigned','پورسانت اسناد بدون انتساب (ریال)'],['amount','پورسانت آسان ساز فروش ـ جمع (ریال)'],['documents','تعداد اسناد']],state.snapshot?.facilitator_totals||[]));
 options($('facilitator-customer'),customerChoices());
 const records=Object.values(state.facilitator_customers||{}),result=table([['customer_name','مشتری'],['name','آسان ساز فروش'],['rate','درصد پورسانت']],records);result.querySelector('thead tr').append(el('th','عملیات'));
 [...result.querySelectorAll('tbody tr')].forEach((tr,index)=>{const cell=el('td'),button=el('button','ویرایش');button.type='button';button.onclick=()=>{options($('facilitator-customer'),customerChoices(),records[index].customer_id);fillFacilitator();$('facilitator-form').scrollIntoView({block:'center',behavior:'smooth'});};cell.append(button);tr.append(cell);});$('facilitator-customers').replaceChildren(result);
 $('facilitator-names').replaceChildren(...[...new Set(records.map(r=>r.name))].sort().map(name=>{const option=el('option');option.value=name;return option;}));
 options($('facilitator-dated-customer'),customerChoices());
 options($('facilitator-old-name'),Object.fromEntries([...new Set([...records.map(r=>r.name),...(state.snapshot?.facilitator_totals||[]).map(r=>r.name)])].sort().map(name=>[name,name])));
}
function fillFacilitator(){const record=state.facilitator_customers?.[$('facilitator-customer').value];$('facilitator-name').value=record?.name||'';$('facilitator-rate').value=record?.rate??'';}
$('facilitator-customer').onchange=fillFacilitator;
async function saveFacilitator(remove){const form=$('facilitator-form'),buttons=[...form.querySelectorAll('button')];if(!remove&&!form.reportValidity())return;const values=Object.fromEntries(new FormData(form));if(!values.customer_id){$('facilitator-status').textContent='ابتدا مشتری را انتخاب کنید.';return;}buttons.forEach(b=>b.disabled=true);$('facilitator-status').textContent='در حال ذخیره…';try{await api('save',{kind:'facilitator_customer',values:{...values,month:state.month,remove},revision:state.revision},true);await load(false);fillFacilitator();$('facilitator-status').textContent=remove?'تنظیم مشتری حذف شد؛ مبلغ‌های دستی فاکتورها همچنان برقرارند.':'آسان‌ساز و درصد مشتری ذخیره شد؛ روی همه ماه‌ها اعمال می‌شود.';}catch(e){error(e,'facilitator-status');}finally{buttons.forEach(b=>b.disabled=false);}}
$('facilitator-form').onsubmit=event=>{event.preventDefault();saveFacilitator(false);};$('facilitator-remove').onclick=()=>saveFacilitator(true);
 $('facilitator-dated-form').onsubmit=async event=>{event.preventDefault();const form=event.currentTarget;if(!form.reportValidity())return;const values=Object.fromEntries(new FormData(form));try{values.from_date=PortalCalendar.toISO(values.from_date.replace(/-/g,'/'));await api('save',{kind:'facilitator_customer_dated',values:{...values,month:state.month},revision:state.revision},true);await load(false);form.reset();$('facilitator-dated-status').textContent='تغییر از تاریخ انتخاب‌شده ثبت شد و سوابق قبلی حفظ شد.';}catch(e){error(e,'facilitator-dated-status');}};
 $('facilitator-transfer-form').onsubmit=async event=>{event.preventDefault();const form=event.currentTarget;if(!form.reportValidity())return;const values=Object.fromEntries(new FormData(form));values.old_name=$('facilitator-old-name').value;try{await api('save',{kind:values.kind,values:{old_name:values.old_name,new_name:values.new_name},revision:state.revision},true);await load(false);form.reset();$('facilitator-transfer-status').textContent='نام یا مالک سوابق آسان‌ساز به‌روزرسانی شد.';}catch(e){error(e,'facilitator-transfer-status');}};
searchableSelect('facilitator-customer');
const dealDialog=el('dialog');dealDialog.className='sales-invoice-dialog';dealDialog.setAttribute('aria-label','انتخاب معامله دیدار برای فاکتور');document.body.append(dealDialog);
let dealSession=0;
dealDialog.addEventListener('close',()=>{dealSession++;});
function itemMatchLabel(match){return !match?.available||!match.total?'اقلام دریافت نشده؛ بررسی جزئیات':fmt(match.matched)+' از '+fmt(match.total)+' کالای فاکتور · تعداد برابر: '+fmt(match.equal_quantity)+(match.extra?' · '+fmt(match.extra)+' کالای اضافه':'');}
function itemMatchDetails(match){const details=el('details'),summary=el('summary','کالاهای مشترک و اختلاف تعداد');details.append(summary,el('p','مقایسه بر اساس کد کالا؛ ردیف‌های تکراری یک کالا با جمع تعداد محاسبه می‌شوند. تطبیق کالا به معنی یکسان‌بودن مبلغ یا تأیید انتساب نیست.'));details.append(table([['code','کد کالا'],['title','کالای فاکتور'],['invoice_quantity','تعداد فاکتور'],['deal_quantity','تعداد معامله'],['status','تطبیق']],(match?.details||[]).map(item=>({...item,status:!match.available?'اطلاعات دریافت نشده':!item.present?'در معامله نیست':item.equal_quantity?'کالا و تعداد برابر':'کالا مشترک؛ تعداد متفاوت یا نامشخص'}))));return details;}
async function chooseInvoiceDeal(row){
 const session=++dealSession,month=state.month,header=el('div'),title=el('h2','اتصال معامله به فاکتور '+row.number),close=el('button','بستن'),toolbar=el('div'),rangeLabel=el('label','بازه نسبت به تاریخ فاکتور'),range=el('select'),search=el('input'),useInvoiceAmount=el('button','جستجوی مبلغ همین فاکتور'),list=el('div'),preview=el('div'),status=el('p');
 header.className='sales-invoice-dialog-header';close.type='button';close.onclick=()=>dealDialog.close();header.append(title,close);toolbar.className='sales-deal-toolbar';range.setAttribute('aria-label','بازه زمانی معاملات');options(range,{'7':'۷ روز قبل و بعد','15':'۱۵ روز قبل و بعد','30':'۳۰ روز قبل و بعد','60':'۶۰ روز قبل و بعد','90':'۹۰ روز قبل و بعد'},'7');rangeLabel.append(range);search.type='search';search.placeholder='جستجوی عنوان، کد معامله یا مشتری';search.setAttribute('aria-label','جستجوی معاملات دیدار');useInvoiceAmount.type='button';useInvoiceAmount.disabled=row.total_amount==null;useInvoiceAmount.setAttribute('aria-pressed','false');useInvoiceAmount.onclick=()=>{filterInvoiceAmount=!filterInvoiceAmount;useInvoiceAmount.setAttribute('aria-pressed',String(filterInvoiceAmount));useInvoiceAmount.textContent=filterInvoiceAmount?'نمایش همه مبالغ':'جستجوی مبلغ همین فاکتور';render();};toolbar.append(rangeLabel,search,useInvoiceAmount);list.className='sales-invoice-detail-scroll';status.setAttribute('role','status');dealDialog.replaceChildren(header,el('p',row.customer+' · '+jalaliDate(row.date)+' · مبلغ فاکتور: '+fmt(row.total_amount)+' ریال'),el('p','معاملات فروش موفق یا باز نزدیک به تاریخ ثبت یا موفق‌شدن، از آخرین دریافت دیدار. معاملات متصل به اسناد دیگر نمایش داده نمی‌شوند. این اتصال فقط برای همین فاکتور ذخیره می‌شود.'),toolbar,status,list,preview);dealDialog.showModal();
 let available=[],revision='',selectionRequest=0,filterInvoiceAmount=false;
 const alive=()=>session===dealSession&&dealDialog.open;
 function render(){const query=searchText(search.value),rows=available.filter(d=>searchText([d.title,d.code,d.customer,d.seller_name].join(' ')).includes(query)&&(!filterInvoiceAmount||(d.total!=null&&Number(d.total)===Number(row.total_amount))));const result=table([['title','عنوان / مشتری معامله'],['code','کد'],['customer','مشتری دیدار'],['date_label','تاریخ ثبت'],['won_label','تاریخ موفق‌شدن'],['seller_name','کارشناس'],['channel_name','کانال'],['state','وضعیت'],['total_label','جمع نهایی (ریال)'],['item_match_label','تطبیق کالاهای فاکتور']],rows.map(d=>({...d,item_match_label:itemMatchLabel(d.item_match),date_label:jalaliDate(d.date),won_label:d.state==='موفق'?jalaliDate(d.won_date):'—',total_label:d.total==null?'بررسی جزئیات':fmt(Number(d.total))})));result.querySelector('thead tr').append(el('th','بررسی'));[...result.querySelectorAll('tbody tr')].forEach((tr,i)=>{const cell=el('td'),button=el('button','مشاهده و انتخاب');button.type='button';button.onclick=()=>inspect(rows[i]);cell.append(button);tr.append(cell);if(rows[i].item_match?.available)tr.cells[9].append(itemMatchDetails(rows[i].item_match));});list.replaceChildren(rows.length?result:el('p','معامله‌ای در این بازه و جستجو پیدا نشد.'));}
 async function inspect(deal){const request=++selectionRequest;preview.replaceChildren(el('p','در حال دریافت اقلام معامله از دیدار…'));try{const [details,financial]=await Promise.all([api('candidate_detail',{month,key:row.key,deal_id:deal.id,days:range.value}),api('invoice_details',{month,key:row.key})]);if(!alive()||request!==selectionRequest)return;revision=details.revision;const selected=details.deal,panels=el('div');panels.className='sales-deal-comparison';for(const [label,cols,items]of [['اقلام فاکتور سپیدار',[['code','کد'],['title','کالا'],['quantity','تعداد'],['discount','تخفیف'],['tax','مالیات'],['total','نهایی']],financial.items],['اقلام معامله دیدار',[['ProductCode','کد'],['Quantity','تعداد'],['UnitPrice','قیمت واحد'],['Discount','تخفیف'],['TaxPrice','مالیات']],selected.items]]){const panel=el('section'),scroll=el('div');scroll.className='sales-invoice-detail-scroll';scroll.append(table(cols,items));panel.append(el('h3',label),scroll);panels.append(panel);}const reviewed=el('input'),label=el('label'),save=el('button','ثبت اتصال این معامله به فاکتور');reviewed.type='checkbox';label.append(reviewed,document.createTextNode(' مشتری، اقلام، اختلاف مبلغ و کارشناس/کانال را بررسی کردم و این معامله را تأیید می‌کنم.'));const quoteReview=el('input'),quoteLabel=el('label'),quoteWarning=['missing','unresolved'].includes(row.quotation_status);quoteReview.type='checkbox';quoteLabel.append(quoteReview,document.createTextNode(' نبود پیش‌فاکتور سپیدار را جداگانه بررسی و تأیید کردم.'));quoteLabel.hidden=!quoteWarning;save.type='button';save.disabled=true;reviewed.onchange=quoteReview.onchange=()=>{save.disabled=!reviewed.checked||(quoteWarning&&!quoteReview.checked);};save.onclick=async()=>{save.disabled=true;try{await api('save',{kind:'manual_deal',values:{month,key:row.key,deal_id:deal.id,days:range.value,reviewed:reviewed.checked,reviewed_no_quotation:quoteReview.checked},revision},true);if(alive())dealDialog.close();await load(false);$('assignment-status').textContent='معامله به همین فاکتور متصل شد؛ کارشناس و کانال ثبت شدند.';}catch(e){status.textContent='ثبت انجام نشد؛ ممکن است معامله یا تنظیمات تغییر کرده باشد. بازه را دوباره انتخاب و معامله را بررسی کنید.';}finally{save.disabled=false;}};preview.replaceChildren(el('h3',selected.title+' · کد '+(selected.code||'—')),el('p',selected.customer+' · '+selected.seller_name+' · '+selected.channel_name),el('p','مبلغ دیدار: '+(selected.total==null?'ناموجود':fmt(Number(selected.total)))+' ریال · اختلاف با سپیدار: '+(selected.total==null?'نامشخص':fmt(financial.totals.total-Number(selected.total)))+' ریال'),el('p',itemMatchLabel(selected.item_match)),itemMatchDetails(selected.item_match),panels,label,quoteLabel,save);preview.scrollIntoView({block:'nearest'});}catch(e){if(alive()&&request===selectionRequest)preview.replaceChildren(el('p','جزئیات معامله دریافت نشد؛ دوباره انتخاب کنید یا دریافت گزارش را به‌روز کنید.'));}}
 async function fetchCandidates(){const request=++selectionRequest;preview.replaceChildren();list.replaceChildren();status.textContent='در حال دریافت معاملات قابل انتخاب…';try{const data=await api('deal_candidates',{month,key:row.key,days:range.value});if(!alive()||request!==selectionRequest)return;available=data.deals;revision=data.revision;status.textContent=fmt(available.length)+' معامله قابل بررسی · آخرین دریافت: '+(data.captured_at||'—');render();}catch(e){if(alive())status.textContent='دریافت معاملات انجام نشد؛ دوباره بازه را انتخاب کنید.';}}
 search.oninput=render;range.onchange=fetchCandidates;await fetchCandidates();
}
function compactInvoiceTable(container,repair=false){
 const result=$(container).querySelector('table');if(!result)return;result.classList.add('sales-compact-invoices');
 const labels=repair?['فاکتور','مشتری','جمع نهایی (ریال)','کارشناس فروش مرتبط','مسئول خدمات / کانال','دلیل تعمیرات','عملیات']:['فاکتور','مشتری','جمع نهایی (ریال)','وضعیت / انتخاب','کارشناس / کانال','عملیات'];
 result.querySelector('thead tr').replaceChildren(...labels.map(label=>el('th',label)));
 for(const tr of result.querySelectorAll('tbody tr')){
  const c=[...tr.cells],line=(cell,label,text)=>{const node=el('small',label+text);node.className='sales-cell-note';cell.append(node);};
  line(c[0],'',c[1].textContent);line(c[0],'',c[2].textContent);
  if(repair){line(c[8],'',c[7].textContent);if(c[10].textContent!=='—')line(c[9],'انتساب قبلی: ',c[10].textContent);tr.replaceChildren(c[0],c[3],c[6],c[12],c[8],c[9],c[11]);result.classList.add('sales-repair-compact');}
  else{const original=c[3].textContent;c[3].replaceChildren(el('strong',original));line(c[3],'دیدار: ',c[4].textContent);line(c[9],'',c[8].textContent);const sellerLabel=el('label','کارشناس'),channelLabel=el('label','کانال');sellerLabel.append(...c[10].childNodes);channelLabel.append(...c[11].childNodes);c[10].replaceChildren(sellerLabel,channelLabel);tr.replaceChildren(c[0],c[3],c[7],c[9],c[10],c[12]);}
 }
}
function drawInvoices(){
 const query=$('invoice-search').value.trim(),names=activeNames(),suggestions=monthSuggestions();
 const all=monthInvoices().map(row=>({...row,date_label:jalaliDate(row.date),quotation_label:row.quotation_status==='present'?'پیش‌فاکتور '+(row.quotation_number||'ثبت‌شده'):row.quotation_status==='missing'?'⚠ بدون پیش‌فاکتور سپیدار':row.quotation_status==='unresolved'?'⚠ ارتباط پیش‌فاکتور نامشخص':row.quotation_status==='not_applicable'?'برگشت از فروش':'هنوز بررسی نشده؛ دریافت مجدد لازم است'})),records=all.filter(row=>!query||[row.number,row.customer,row.key].some(value=>value?.includes(query)));
 $('invoice-count').textContent='ماه '+state.month+' · '+fmt(records.length)+' از '+fmt(all.length)+' فاکتور · '+fmt(Object.keys(suggestions).length)+' پیشنهاد قابل تأیید · '+fmt(selection.size)+' انتخاب‌شده';
 for(const mapped of [false,true]){
 const rows=records.filter(row=>!row.excluded&&!row.is_repair&&Boolean(row.mapped)===mapped).map(row=>({...row,related_customer:row.didar_customer_name||suggestions[row.key]?.related_customer_name||row.related_customer_name||'شناسایی نشده',status_label:row.mapped?'انتساب ثبت‌شده':(suggestions[row.key]?.document_confidence||suggestions[row.key]?.confidence)==='document_minor_difference'?'اقلام منطبق، اختلاف جزئی مبلغ':suggestions[row.key]?.confidence==='document'?'تطبیق کامل سند':suggestions[row.key]?.confidence==='customer_relation'?'پیشنهاد از ارتباط شخص و شرکت':suggestions[row.key]?'پیشنهاد بر اساس مشتری':row.match_note?'نیازمند بررسی':'بدون انتساب'})),result=table([['number','شماره'],['date_label','تاریخ شمسی'],['quotation_label','وضعیت پیش‌فاکتور'],['customer','مشتری فاکتور سپیدار'],['related_customer','مشتری مرتبط در دیدار'],['amount','قبل از مالیات (ریال)'],['tax','مالیات و عوارض (ریال)'],['total_amount','جمع نهایی فاکتور (ریال)'],['status_label','وضعیت']],rows),header=result.querySelector('thead tr');
 for(const label of ['انتخاب پیشنهاد','کارشناس فعلی / اصلاح','کانال فعلی / اصلاح','عملیات'])header.append(el('th',label));
 [...result.querySelectorAll('tbody tr')].forEach((tr,index)=>{
  const row=rows[index],proposal=suggestions[row.key],seller=el('select'),channel=el('select'),check=el('input');check.type='checkbox';check.dataset.key=row.key;check.disabled=!proposal||row.mapped;check.checked=selection.has(row.key);check.setAttribute('aria-label','انتخاب پیشنهاد فاکتور '+row.number);check.onchange=()=>{if(check.checked)selection.add(row.key);else selection.delete(row.key);drawInvoices();};
  const id=canonical(row.seller||proposal?.seller),choices={...names};if(id&&!choices[id])choices[id]=allNames()[id]||'کارشناس سابق';
  options(seller,{'':'انتخاب کارشناس',...choices},id);seller.setAttribute('aria-label','کارشناس فاکتور '+row.number);
  options(channel,{'':'انتخاب کانال',...state.channels},row.channel||proposal?.channel);channel.setAttribute('aria-label','کانال فاکتور '+row.number);
  const actions=el('div'),button=el('button',row.mapped?'اصلاح این فاکتور':'ثبت این فاکتور');button.type='button';
  const quoteWarning=['missing','unresolved'].includes(row.quotation_status),reviewed=el('input');reviewed.type='checkbox';
  if(quoteWarning){tr.classList.add('sales-invoice-warning');const label=el('label');label.append(reviewed,document.createTextNode(' نبود پیش‌فاکتور را بررسی کردم؛ انتساب دستی تأیید است'));actions.append(label);button.disabled=true;reviewed.onchange=()=>{button.disabled=!reviewed.checked;};}
  async function saveAssignment(kind){
   button.disabled=true;
   try{await api('save',{kind,values:{month:state.month,key:row.key,customer_id:row.customer_id,seller:seller.value,channel:channel.value,reviewed_no_quotation:reviewed.checked},revision:state.revision},true);await load(false);$('assignment-status').textContent=quoteWarning?'انتساب پس از بررسی هشدار ثبت شد؛ مرجع خودکار مشتری از این فاکتور ساخته نشد.':proposal?.confidence==='customer_relation'||row.related_customer_name?'انتساب فقط برای این فاکتور ثبت شد؛ ارتباط شخص و شرکت برای فاکتورهای دیگر دوباره بررسی می‌شود.':'انتساب ثبت شد؛ کارشناس و کانال به‌عنوان مرجع فاکتورهای بدون انتساب این مشتری ذخیره شد.';}
   catch(e){error(e,'assignment-status');}finally{button.disabled=false;}
  }
  button.onclick=()=>saveAssignment('invoice');actions.append(button);
  if(row.key.startsWith('Sale:')){const choose=el('button',row.matched_deal_id?'تغییر معامله متصل':'انتخاب معامله دیدار');choose.type='button';choose.onclick=()=>chooseInvoiceDeal(row);actions.append(choose);}
  const more=el('details');more.className='sales-row-more';more.append(el('summary','سایر عملیات'));actions.append(more);
  const repair=el('button','ثبت به‌عنوان تعمیرات');repair.type='button';repair.onclick=()=>saveDocumentType(row,'repair','',repair);more.append(repair,exclusionButton(row));
  const rule=el('button','تغییر مسئول مشتری از تاریخ');rule.type='button';rule.onclick=()=>{ruleMode();options($('rule-customer'),customerChoices(),row.customer_id);$('rule-date').value=state.month+'-01';options($('rule-seller'),{'':'انتخاب کارشناس',...historicalChoices(id)},id);$('rule-channel').value=channel.value;$('rule-channel').syncSearch();ruleFormFocus();};more.append(rule);
  const explanations=[proposal?.reason||row.match_note,row.channel_reason].filter(Boolean);
  if(explanations.length){
   const details=el('details'),summary=el('summary','جزئیات تطبیق'),body=el('div');details.className='sales-match-details';
   for(const text of explanations)body.append(el('p',text));
   details.append(summary,body);actions.append(details);
  }
  for(const node of [check,seller,channel,actions]){const cell=el('td');cell.append(node);tr.append(cell);}
 });
 $(mapped?'assigned-invoices':'invoices').replaceChildren(rows.length?result:el('p','فاکتوری در این بخش برای ماه و جستجوی انتخاب‌شده وجود ندارد.'));
 invoiceDetailButtons(mapped?'assigned-invoices':'invoices',rows);
 compactInvoiceTable(mapped?'assigned-invoices':'invoices');
 $(mapped?'assigned-title':'unassigned-title').textContent=(mapped?'انتساب‌شده':'بدون انتساب')+' ('+fmt(rows.length)+')';
 }
 const repairRecords=records.filter(row=>!row.excluded&&row.is_repair),repairFilter=$('repair-assignment-filter').value;
 const confirmedRepairs=repairRecords.filter(row=>row.repair_sales_seller).length;
 $('repair-assignment-count').textContent='در نتیجه جستجوی این ماه: '+fmt(confirmedRepairs)+' تأییدشده · '+fmt(repairRecords.length-confirmedRepairs)+' در انتظار تأیید';
 const repairs=repairRecords.filter(row=>repairFilter==='all'||(repairFilter==='confirmed'?Boolean(row.repair_sales_seller):!row.repair_sales_seller)).map(row=>({...row,seller_name:row.seller?allNames()[canonical(row.seller)]||'کارشناس سابق':'در انتظار تعیین مسئول خدمات',previous_assignment:row.previous_sales_assignment?(allNames()[canonical(row.previous_sales_assignment.seller)]||'کارشناس سابق')+' / '+(state.channels[row.previous_sales_assignment.channel]||''):'—',channel_name:state.document_channels?.[row.channel]||'خدمات پس از فروش'}));
 $('repair-title').textContent='تعمیرات ('+fmt(repairRecords.length)+')';
 $('repair-invoices').replaceChildren(repairs.length?table([['number','شماره'],['date_label','تاریخ شمسی'],['quotation_label','وضعیت پیش‌فاکتور'],['customer','مشتری'],['amount','قبل از مالیات (ریال)'],['tax','مالیات و عوارض (ریال)'],['total_amount','جمع نهایی فاکتور (ریال)'],['channel_name','کانال فاکتور'],['seller_name','مسئول خدمات'],['repair_reason','دلیل جداسازی'],['previous_assignment','انتساب فروش قبلی (اعمال نمی‌شود)']],repairs):el('p','فاکتور تعمیراتی مطابق ماه، جستجو و وضعیت انتخاب‌شده وجود ندارد.'));
 const repairTable=$('repair-invoices').querySelector('table');
 invoiceDetailButtons('repair-invoices',repairs);
 if(repairTable){repairTable.querySelector('thead tr').append(el('th','نوع / شرح تعمیرات'));[...repairTable.querySelectorAll('tbody tr')].forEach((tr,index)=>{const row=repairs[index],cell=el('td'),description=el('input'),save=el('button','ذخیره شرح تعمیرات');if(['missing','unresolved'].includes(row.quotation_status))tr.classList.add('sales-invoice-warning');description.value=row.repair_description||'';description.maxLength=200;description.placeholder='مثلاً تعمیر موتور یا تعویض قطعه';description.setAttribute('aria-label','شرح تعمیرات فاکتور '+row.number);save.type='button';save.onclick=()=>saveDocumentType(row,'repair',description.value,save);cell.append(description,save,exclusionButton(row));if(row.manual_repair){const undo=el('button','لغو تعیین دستی تعمیرات');undo.type='button';undo.onclick=()=>saveDocumentType(row,'auto','',undo);cell.append(undo);}tr.append(cell);});}
 if(repairTable){[...repairTable.querySelectorAll('tbody tr')].forEach((tr,index)=>{
  const row=repairs[index],cell=el('td'),select=el('select'),button=el('button',row.repair_sales_seller?'اصلاح کارشناس فروش':'تأیید کارشناس فروش'),proposal=row.repair_sales_proposal,current=canonical(row.repair_sales_seller||proposal?.seller)||'',choices={...activeNames()};
  if(current&&!choices[current])choices[current]=(allNames()[current]||'کارشناس سابق')+' (غیرفعال)';
  options(select,{'':'بدون انتساب',...choices},current);select.setAttribute('aria-label','کارشناس فروش مرتبط با تعمیرات '+row.number);button.type='button';
  const note=el('small',row.repair_sales_seller?'ثبت‌شده · '+row.repair_sales_source:proposal?'پیشنهاد: '+proposal.source:'پیشنهاد معتبری موجود نیست؛ کارشناس را انتخاب کنید.');note.className='sales-cell-note';
  button.onclick=async()=>{button.disabled=true;try{await api('save',{kind:'repair_sales_seller',values:{month:state.month,key:row.key,seller:select.value},revision:state.revision},true);await load(false);$('repair-sales-status').textContent=select.value?'کارشناس فروش فقط برای همین فاکتور تعمیرات ثبت شد؛ مبلغ وارد آمار فروش نمی‌شود.':'انتساب کارشناس فروش این فاکتور حذف شد.';}catch(e){error(e,'repair-sales-status');}finally{button.disabled=false;}};
  const badge=el('span',row.repair_sales_seller?'✓ کارشناس فروش تأییدشده':'در انتظار تأیید کارشناس فروش');badge.className='sales-repair-badge '+(row.repair_sales_seller?'is-confirmed':'is-pending');
  tr.classList.add(row.repair_sales_seller?'sales-repair-confirmed':'sales-repair-pending');cell.append(badge,select,button,note);tr.append(cell);
 });}
 const repairProposals=monthInvoices().filter(r=>r.is_repair&&!r.excluded&&!r.repair_sales_seller&&r.repair_sales_proposal);
 $('confirm-repair-sales').disabled=!repairProposals.length;$('confirm-repair-sales').textContent='تأیید همه پیشنهادهای کارشناس فروش این ماه ('+fmt(repairProposals.length)+')';
 compactInvoiceTable('repair-invoices',true);
 const excluded=records.filter(row=>row.excluded);
 $('excluded-title').textContent='خارج از آمار ('+fmt(excluded.length)+')';
 $('excluded-invoices').replaceChildren(excluded.length?table([['number','شماره'],['date_label','تاریخ شمسی'],['customer','مشتری'],['total_amount','جمع نهایی (ریال)']],excluded):el('p','در این ماه فاکتوری خارج از آمار نیست.'));
 const excludedCustomers=Object.values(state.excluded_customers||{}),excludedTable=table([['customer_name','مشتری'],['customer_id','کد مشتری سپیدار']],excludedCustomers);
 invoiceDetailButtons('excluded-invoices',excluded);
 excludedTable.querySelector('thead tr').append(el('th','عملیات'));
 [...excludedTable.querySelectorAll('tbody tr')].forEach((tr,index)=>{const cell=el('td');cell.append(exclusionButton({...excludedCustomers[index],excluded:true}));tr.append(cell);});
 $('excluded-customers').replaceChildren(excludedTable);
 const eligible=Object.keys(suggestions);$('select-suggestions').checked=!!eligible.length&&eligible.every(key=>selection.has(key));$('select-suggestions').indeterminate=selection.size>0&&!$('select-suggestions').checked;
}
function exclusionButton(row){const button=el('button',row.excluded?'بازگرداندن مشتری به آمار':'خروج کل مشتری از آمار فروش');button.type='button';button.disabled=!row.customer_id;button.title='این تغییر برای تمام ماه‌ها و همه فاکتورهای مشتری است و قابل بازگرداندن است.';button.onclick=async()=>{button.disabled=true;try{await api('save',{kind:'customer_exclusion',values:{month:state.month,customer_id:row.customer_id,excluded:!row.excluded},revision:state.revision},true);await load(false);$('assignment-status').textContent=row.excluded?'مشتری به آمار فروش بازگشت.':'تمام گردش مشتری از آمار فروش خارج شد؛ در تب «خارج از آمار» قابل بازگرداندن است.';}catch(e){error(e,'assignment-status');}finally{button.disabled=false;}};return button;}
async function saveDocumentType(row,type,description,button){button.disabled=true;try{await api('save',{kind:'document_type',values:{month:state.month,key:row.key,type,description},revision:state.revision},true);await load(false);$('assignment-status').textContent=type==='repair'?'نوع فاکتور تعمیرات ثبت شد؛ در خدمات پس از فروش نمایش داده می‌شود.':'تعیین دستی تعمیرات لغو شد؛ تشخیص خودکار دوباره اعمال شد.';}catch(e){error(e,'assignment-status');}finally{button.disabled=false;}}
function customerChoices(){
 const choices={'':'انتخاب مشتری'};
 for(const rule of [...(state.customer_rules||[]),...Object.values(state.customer_references||{}),...Object.values(state.facilitator_customers||{})])if(rule.customer_id)choices[rule.customer_id]=cleanName(rule.customer_name)||rule.customer_id;
 for(const row of state.snapshot?.invoices||[])if(row.customer_id)choices[row.customer_id]=cleanName(row.customer)||choices[row.customer_id]||row.customer_id;
 return choices;
}

function ruleFormFocus(){showPageTab('customers');$('customer-rule-form').scrollIntoView({behavior:'smooth',block:'center'});}
function drawCustomerRules(){
 options($('rule-customer'),customerChoices());options($('rule-seller'),{'':'انتخاب کارشناس',...historicalChoices()});
 if(!$('rule-date').value)$('rule-date').value=state.month+'-01';
 const names=customerChoices(),query=searchText($('customer-rules-search').value),matchesCustomer=r=>searchText((names[r.customer_id]||r.customer_name||'')+' '+r.customer_id).includes(query);
 const rules=(state.customer_rules||[]).filter(matchesCustomer),rows=rules.map(rule=>({...rule,customer_name:names[rule.customer_id]||cleanName(rule.customer_name),seller_name:allNames()[rule.seller]||rule.seller,channel_name:state.channels[rule.channel]}));
 const result=table([['customer_name','مشتری'],['from_jalali','از تاریخ'],['seller_name','کارشناس'],['channel_name','کانال']],rows);
 result.querySelector('thead tr').append(el('th','عملیات'));
 [...result.querySelectorAll('tbody tr')].forEach((tr,index)=>{
  const rule=rules[index],cell=el('td'),edit=el('button','ویرایش'),remove=el('button','حذف');edit.type=remove.type='button';
  edit.onclick=()=>{ruleMode(rule.id||'');options($('rule-customer'),customerChoices(),rule.customer_id);$('rule-date').value=rule.from_jalali;options($('rule-seller'),{'':'انتخاب کارشناس',...historicalChoices(canonical(rule.seller))},canonical(rule.seller));$('rule-channel').value=rule.channel;$('rule-channel').syncSearch();$('rule-status').textContent='در حال ویرایش تغییر مسئول '+(rule.customer_name||'')+' از '+rule.from_jalali;ruleFormFocus();};
  remove.onclick=async()=>{remove.disabled=true;try{await api('save',{kind:'customer_rule_delete',values:{month:state.month,customer_id:rule.customer_id,from_date:rule.from_jalali,rule_id:rule.id},revision:state.revision},true);if(editingRuleId===rule.id)ruleMode();await load(false);$('rule-status').textContent='قاعده مشتری حذف شد و گزارش به‌روز شد.';}catch(e){error(e,'rule-status');}finally{remove.disabled=false;}};
  cell.append(edit,remove);tr.append(cell);
 });
 $('customer-rules').replaceChildren(rows.length?result:el('p',query?'مشتری مطابق جستجو پیدا نشد.':'هنوز تغییر مسئول تاریخ‌داری ثبت نشده است.'));
 $('customer-dated-tab').textContent='تغییر مسئول از تاریخ ('+fmt(rows.length)+')';
 const references=Object.values(state.customer_references||{}).filter(matchesCustomer).map(r=>({...r,customer_name:names[r.customer_id]||cleanName(r.customer_name),seller_name:allNames()[canonical(r.seller)]||'کارشناس سابق',channel_name:state.channels[r.channel]}));
 $('customer-references').replaceChildren(references.length?table([['customer_name','مشتری'],['seller_name','کارشناس'],['channel_name','کانال']],references):el('p',query?'مشتری مطابق جستجو پیدا نشد.':'هنوز انتساب خودکاری ذخیره نشده است.'));
 $('customer-default-tab').textContent='انتساب خودکار مشتریان ('+fmt(references.length)+')';
}
function drawCustomerGroups(){
 const saved=state.customer_group_sellers||{},groups={...Object.fromEntries(Object.entries(saved).map(([id,r])=>[id,r.group_title])),...state.customer_groups},query=searchText($('group-search').value);
 const rows=Object.entries(groups).filter(([id,title])=>searchText(title+' '+id).includes(query)).sort((a,b)=>String(a[1]).localeCompare(String(b[1]),'fa')).map(([id,title])=>({id,title}));
 const result=table([['id','کد گروه سپیدار'],['title','گروه مشتری']],rows);result.querySelector('thead tr').append(el('th','کارشناس فروش دیدار'),el('th','عملیات'));
 [...result.querySelectorAll('tbody tr')].forEach((tr,index)=>{
  const row=rows[index],cell=el('td'),select=el('select'),actions=el('td'),button=el('button','ذخیره تطبیق');button.type='button';select.setAttribute('aria-label','کارشناس گروه '+row.title);
  const current=canonical(saved[row.id]?.seller)||'',names={...activeNames()};if(current&&!names[current])names[current]=(allNames()[current]||'کارشناس سابق')+' (غیرفعال)';
  options(select,{'':'بدون تطبیق',...names},current);cell.append(select);actions.append(button);tr.append(cell,actions);
  button.onclick=async()=>{button.disabled=true;$('group-status').textContent='در حال ذخیره تطبیق گروه…';try{await api('save',{kind:'customer_group_seller',values:{month:state.month,group_id:row.id,seller:select.value},revision:state.revision},true);await load(false);$('group-status').textContent='تطبیق گروه ذخیره شد؛ پیشنهادهای موارد اختلاف به‌روز شدند.';}catch(e){error(e,'group-status');}finally{button.disabled=false;}};
 });
 $('customer-group-table').replaceChildren(rows.length?result:el('p','گروهی در داده‌های دریافت‌شده یا نتیجه جستجو یافت نشد.'));
}
$('group-search').oninput=drawCustomerGroups;
function showCustomerTab(name){for(const key of ['dated','default']){const selected=key===name;$( 'customer-'+key+'-tab').setAttribute('aria-selected',String(selected));$('customer-'+key+'-tab').tabIndex=selected?0:-1;$('customer-'+key+'-panel').hidden=!selected;}}
for(const name of ['dated','default']){const button=$('customer-'+name+'-tab');button.onclick=()=>showCustomerTab(name);button.onkeydown=event=>{if(['ArrowLeft','ArrowRight','Home','End'].includes(event.key)){event.preventDefault();const next=event.key==='Home'?'dated':event.key==='End'?'default':name==='dated'?'default':'dated';showCustomerTab(next);$('customer-'+next+'-tab').focus();}};}
$('customer-rules-search').oninput=drawCustomerRules;
$('filters').onsubmit=async event=>{event.preventDefault();clearTimeout(pollTimer);try{await load();await loadTargets();}catch(e){error(e);}};
$('month').onchange=async()=>{clearTimeout(pollTimer);try{await load();}catch(e){error(e);}};
$('refresh').onclick=async()=>{
 const month=monthValue($('month').value);clearTimeout(pollTimer);busy(true,'در حال درخواست گزارش '+month,'درخواست به سرور ارسال می‌شود…');
 try{await api('refresh',{month},true);await load(false);if(state.busy)schedulePoll();}catch(e){busy(false);error(e);}
};
$('channel').onchange=draw;$('seller-filter').onchange=draw;$('show-inactive').onchange=draw;
$('target-month').onchange=()=>loadTargets().catch(e=>error(e,'target-status'));
$('target-form').onsubmit=async event=>{
 event.preventDefault();const button=event.target.querySelector('button');button.disabled=true;$('target-status').textContent='در حال ثبت تارگت…';
 try{const values=Object.fromEntries(new FormData(event.target));values.month=monthValue(values.month);await api('save',{kind:'target',values,revision:state.revision},true);await load(false);await loadTargets();$('target-status').textContent='تارگت و سقف تخفیف ماه '+values.month+' ثبت شد؛ در گزارش همین ماه فوراً قابل مشاهده است.';}catch(e){error(e,'target-status');}finally{button.disabled=false;}
};
$('invoice-search').oninput=drawInvoices;
$('repair-assignment-filter').onchange=drawInvoices;
$('confirm-repair-sales').onclick=async()=>{const button=$('confirm-repair-sales'),keys=monthInvoices().filter(r=>r.is_repair&&!r.excluded&&!r.repair_sales_seller&&r.repair_sales_proposal).map(r=>r.key);if(!keys.length)return;button.disabled=true;try{await api('save',{kind:'repair_sales_suggestions',values:{month:state.month,keys},revision:state.revision},true);await load(false);$('repair-sales-status').textContent=fmt(keys.length)+' کارشناس فروش مرتبط با تعمیرات تأیید شد؛ مبالغ فروش تغییری نکرد.';}catch(e){error(e,'repair-sales-status');}finally{button.disabled=false;}};

async function exportInvoiceTabs(all){
 if(!state?.snapshot)return;
 const month=state.month,scope=all?'all':['unassigned','assigned','repair','excluded'].find(name=>$(name+'-title').getAttribute('aria-selected')==='true');
 const buttons=[$('export-invoices-all'),$('export-invoices-tab')];buttons.forEach(b=>{b.disabled=true;});$('invoice-export-status').textContent='در حال آماده‌سازی فایل اکسل ماه '+month+'…';
 try{const response=await fetch('/api/method/saeenaria_portal.sales_reports.service.export_invoices?'+new URLSearchParams({month,scope}));if(!response.ok||!(response.headers.get('content-type')||'').includes('application/'))throw Error('دریافت اکسل انجام نشد');const blob=await response.blob();if((response.headers.get('content-type')||'').includes('json'))throw Error('دریافت اکسل انجام نشد');const url=URL.createObjectURL(blob),link=el('a');link.href=url;link.download='sales-invoices-'+month+'-'+scope+'.xlsx';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);$('invoice-export-status').textContent='فایل اکسل ماه '+month+' آماده شد؛ شامل تمام اسناد '+(all?'چهار تب':'تب جاری')+'، بدون فیلتر جستجوی صفحه.';}catch(e){$('invoice-export-status').textContent='خروجی اکسل دریافت نشد؛ دوباره تلاش کنید.';}finally{buttons.forEach(b=>{b.disabled=false;});}
}
$('export-invoices-all').onclick=()=>exportInvoiceTabs(true);
$('export-invoices-tab').onclick=()=>exportInvoiceTabs(false);
function showInvoiceTab(selected){
 for(const name of ['unassigned','assigned','repair','excluded']){const active=name===selected;$(name+'-title').setAttribute('aria-selected',String(active));$(name+'-title').tabIndex=active?0:-1;$(name+'-panel').hidden=!active;}
}
for(const name of ['unassigned','assigned','repair','excluded']){
 $(name+'-title').onclick=()=>showInvoiceTab(name);
 $(name+'-title').onkeydown=event=>{if(!['ArrowLeft','ArrowRight','Home','End'].includes(event.key))return;event.preventDefault();const tabs=['unassigned','assigned','repair','excluded'],next=event.key==='Home'?tabs[0]:event.key==='End'?tabs[tabs.length-1]:tabs[(tabs.indexOf(name)+(event.key==='ArrowLeft'?1:tabs.length-1))%tabs.length];showInvoiceTab(next);$(next+'-title').focus();};
}
$('select-suggestions').onchange=event=>{selection.clear();if(event.target.checked)for(const key of Object.keys(monthSuggestions()))selection.add(key);drawInvoices();};
$('confirm-suggestions').onclick=async()=>{
 const button=$('confirm-suggestions');button.disabled=true;
 try{if(!selection.size)throw Error('ابتدا پیشنهادهای مورد تأیید خود را انتخاب کنید.');const saved=await api('save',{kind:'suggestions',values:{month:state.month,keys:[...selection]},revision:state.revision},true);const count=selection.size;selection.clear();$('select-suggestions').checked=false;await load(false);$('assignment-status').textContent=fmt(count)+' انتساب تأیید شد؛ موارد مبتنی بر ارتباط شخص و شرکت فقط برای همان فاکتور ذخیره شدند.'+(saved.reference_conflicts?.length?' برای '+fmt(saved.reference_conflicts.length)+' مشتری، انتخاب‌ها متفاوت بود؛ مرجع خودکار تغییر نکرد.':'');}catch(e){error(e,'assignment-status');}finally{button.disabled=false;}
};
$('customer-rule-form').onsubmit=async event=>{
 event.preventDefault();const button=event.target.querySelector('button');button.disabled=true;$('rule-status').textContent='در حال ثبت قاعده…';
 try{const values=Object.fromEntries(new FormData(event.target));values.month=state.month;values.rule_id=editingRuleId;await api('save',{kind:'customer_rule',values,revision:state.revision},true);ruleMode();await load(false);$('rule-status').textContent='تغییر مسئول مشتری ثبت شد و گزارش به‌روز شد.';}catch(e){error(e,'rule-status');}finally{button.disabled=false;}
};
for(const id of ['rule-customer','rule-seller','rule-channel'])searchableSelect(id);
$('cancel-customer-rule').onclick=()=>{ruleMode();$('customer-rule-form').reset();for(const id of ['rule-customer','rule-seller','rule-channel'])$(id).syncSearch();$('rule-date').value=state.month+'-01';$('rule-status').textContent='ویرایش لغو شد؛ می‌توانید تغییر مسئول دیگری ثبت کنید.';};
$('api-form').onsubmit=async event=>{event.preventDefault();const input=$('api-key'),button=event.target.querySelector('button');button.disabled=true;try{await api('configure_api',{api_key:input.value},true);input.value='';await load(false);$('status').textContent='کلید رمزگذاری‌شده ثبت شد؛ دریافت و محاسبه مجدد را بزنید.';}catch(e){input.value='';error(e);}finally{button.disabled=false;}};
$('print').onclick=()=>window.print();
$('csv').onclick=()=>{
 const cols=reportColumns(),cell=value=>{let text=String(value??'ناموجود');if(typeof value==='string'&&(/^\s*[=+@-]/.test(text)||/^[\t\r\n]/.test(text)))text="'"+text;return '"'+text.replaceAll('"','""')+'"';};
 const content=[cols.map(([,label])=>cell(label)).join(','),...visible.map(row=>cols.map(([key])=>cell(row[key])).join(','))].join('\r\n');
 const url=URL.createObjectURL(new Blob(['\ufeff'+content],{type:'text/csv;charset=utf-8;'})),link=el('a');link.href=url;link.download='sales-'+state.month+'.csv';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
};
$('excel-performance').onclick=async()=>{const button=$('excel-performance');button.disabled=true;try{const response=await fetch('/api/method/saeenaria_portal.sales_reports.service.export_performance?'+new URLSearchParams({month:state.month}));if(!response.ok)throw Error();const blob=await response.blob(),url=URL.createObjectURL(blob),link=el('a');link.href=url;link.download='sales-performance-'+state.month+'.xlsx';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);$('performance-export-status').textContent='فایل اکسل عملکرد و تعمیرات آماده شد.';}catch{$('performance-export-status').textContent='دریافت اکسل انجام نشد؛ دوباره تلاش کنید.';}finally{button.disabled=false;}};
load().then(loadTargets).catch(e=>error(e));
})();
