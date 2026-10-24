(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const method = '/api/method/saeenaria_portal.purchase_reports.service.';
  const labels = {StockTitle:'انبار',Category:'دسته‌بندی',ExpertGroup:'کارشناس',CustomerTemperature:'وضعیت مشتری',MismatchSide:'نوع مغایرت',WeekStart:'ابتدای هفته'};
  const formatter = new Intl.NumberFormat('fa-IR', {maximumFractionDigits:2});
  let active = location.hash.slice(1) || 'orders', filters = {}, page = 1, sort = '', descending = false, total = 0, request = 0, polling;
  if(active==='reconcile'){location.replace('/portal-products?status=issues');return;}
  let statusData, lastReport, searchTimer, suggestionRequest=0;
  const node = (tag, value, cls) => { const n = document.createElement(tag); if (value != null) n.textContent = value; if (cls) n.className=cls; return n; };
  const numeric = value => value !== null && value !== '' && value !== undefined && Number.isFinite(Number(value));
  function format(value, field='') {
    if (value == null || value === '') return 'ناموجود';
    if (field.endsWith('Code') || ['ItemTitle','ReferenceTitle'].includes(field)) return String(value);
    if (field === 'LastPurchaseDate' || field === 'WeekStart') return date(value, false);
    return numeric(value) ? formatter.format(Number(value)) : String(value);
  }
  function date(value, time=true) {
    if (!value) return 'ثبت نشده';
    const d = new Date(value);
    if (!Number.isFinite(d.getTime())) return String(value);
    return new Intl.DateTimeFormat('fa-IR-u-ca-persian', {dateStyle:'short', ...(time?{timeStyle:'short'}:{}), timeZone:'Asia/Tehran'}).format(d);
  }
  async function api(name, params={}, post=false) {
    const options = {credentials:'same-origin', headers:{}};
    let url = method + name;
    if (post) { options.method='POST'; options.headers['Content-Type']='application/json'; options.headers['X-Frappe-CSRF-Token']=document.querySelector('meta[name=csrf-token]').content; options.body=JSON.stringify(params); }
    else url += '?' + new URLSearchParams(params);
    const response = await fetch(url, options);
    if (!response.ok) throw new Error(response.status===403?'دسترسی مجاز نیست یا نشست ورود پایان یافته است.': 'دریافت اطلاعات موفق نبود. دوباره تلاش کنید.');
    const body = await response.json(); return body.message;
  }
  function status(message, error=false) { $('purchase-status').textContent=message; $('purchase-status').classList.toggle('error',error); }
  function showSourceState() {
    const state = statusData?.state || {};
    if (!statusData?.configured) status('اتصال منابع هنوز تنظیم نشده است. پس از اتصال، گزارش‌ها با داده واقعی نمایش داده می‌شوند.');
    else if (state.running) status('دریافت داده از منابع در حال انجام است. آخرین داده موفق تا پایان دریافت حفظ می‌شود.');
    else if (Object.keys(state.errors || {}).length) status('آخرین دریافت از '+Object.keys(state.errors).map(()=> 'سپیدار / محاسبات پورتال').join(' و ')+' موفق نبود. گزارش موجود، آخرین دریافت موفق است؛ زمان آن را بررسی کنید.',true);
    else status('داده‌ها از منابع شرکت خوانده می‌شوند. برای بررسی تازگی، زمان دریافت و نسخه تنظیمات پورتال را ببینید.');
    $('refresh-source').disabled=!statusData?.configured || !!state.running;
  }
  async function overview() {
    statusData = await api('overview');
    if (!['settings','incoming'].includes(active)&&!statusData.reports.some(r=>r.name===active)) active='orders';
    $('report-tabs').replaceChildren(...[...statusData.reports,{name:'incoming',title:'سفارش‌های در راه'},{name:'settings',title:'تنظیمات خرید'}].map(report=>{
      const button=node('button',report.title);button.type='button';button.dataset.report=report.name;
      if (report.name===active) button.setAttribute('aria-current','page');
      button.addEventListener('click',()=>{location.hash=report.name;});return button;
    }));
    showSourceState();
  }
  function readFilters() {
    const values={};
    $('select-filters').querySelectorAll('select').forEach(s=>{if(s.value) values[s.name]=s.value;});
    if ($('report-search').value.trim()) values.search=$('report-search').value.trim();
    return values;
  }
  function drawFilters(options) {
    $('select-filters').replaceChildren();
    for (const [field,values] of Object.entries(options)) {
      const label=node('label',labels[field]||field), select=node('select');select.name=field;
      select.append(new Option(field==='StockTitle'&&active==='orders'?'همه انبارها (محاسبه تجمیعی)':'همه', ''));
      for(const v of values) { if(active==='orders'&&field==='StockTitle'&&v==='همه انبارها')continue;select.append(new Option(format(v,field),v)); }
      select.value=filters[field]||'';label.append(select);$('select-filters').append(label);
    }
    $('report-search').value=filters.search||'';
  }
  function drawMetrics(metrics) {
    $('report-metrics').replaceChildren(...metrics.map(m=>{const card=node('div',null,'purchase-metric'),value=format(m.value);if(value.length>16)card.classList.add('long-value');card.append(node('span',m.label),node('strong',value));return card;}));
  }
  function drawTable(columns, rows, sorting=false) {
    const table=node('table'), head=node('thead'), tr=node('tr');
    for (const column of columns) {
      const th=node('th');th.scope='col';
      if(sorting){const b=node('button',column.label+(sort===column.field?(descending?' ↓':' ↑'):''));b.type='button';b.addEventListener('click',()=>{descending=sort===column.field?!descending:false;sort=column.field;page=1;load();});th.append(b);}
      else th.textContent=column.label;tr.append(th);
    }
    head.append(tr);table.append(head);const body=node('tbody');
    for(const row of rows){const line=node('tr');for(const col of columns){const v=row[col.field];line.append(node('td',format(v,col.field),v==null?'missing':numeric(v)&&!col.field.endsWith('Code')?'numeric':''));}body.append(line);}table.append(body);return table;
  }
  async function load() {
    const id=++request;
    const settings=active==='settings',incoming=active==='incoming';document.body.classList.toggle('purchase-incoming-view',incoming);$('purchase-report-panel').hidden=settings||incoming;$('purchase-settings-panel').hidden=!settings;$('purchase-incoming-panel').hidden=!incoming;$('purchase-report-help').hidden=settings||incoming;$('refresh-source').hidden=settings||incoming;
    if(settings){await window.PurchaseSettings.load();return;}
    if(incoming){await window.PurchaseIncoming.load();return;}
    $('report-table').setAttribute('aria-busy','true');
    try {
      const data=await api('report',{name:active,filters:JSON.stringify(filters),page,page_size:50,sort_by:sort,descending:descending?'1':'0'});
      if(id!==request)return;lastReport=data;total=data.total;
      $('report-title').textContent=data.title;
      const hasCustomer=data.columns.some(c=>c.field==='CustomerName'),hasCode=data.columns.some(c=>['ItemCode','ReferenceCode'].includes(c.field));
      $('report-search').placeholder=hasCustomer?(hasCode?'کد یا نام کالا، نام مشتری…':'نام مشتری…'):'کد یا نام کالا…';
      $('report-search-help').textContent=(hasCustomer?'دو حرف از نام مشتری، نام کالا یا کد کالا':'دو حرف از نام کالا یا کد کالا')+' تایپ کنید؛ پیشنهاد را انتخاب و «اعمال فیلتر» را بزنید.';
      const sourceDate=data.settings_at?.[0]?.portal_catalog_sync;
      const sourceRun=data.source_run?.[0];
      const localPolicy=data.settings_at?.[0];
      $('source-time').textContent=data.updated_at?'دریافت: '+date(data.updated_at)+(localPolicy?.portal_settings_revision?' · نسخه تنظیمات پورتال: '+formatter.format(localPolicy.portal_settings_revision):'')+(sourceDate?' · همگام‌سازی کالاها: '+date(sourceDate):''): 'هنوز دریافت نشده';
      if(sourceRun&&sourceRun.run_status!=='succeeded') status('آخرین پردازش منبع '+(sourceRun.run_status==='running'?'هنوز در حال اجراست.':'موفق نبوده است.')+' داده نمایش‌داده‌شده مربوط به آخرین خروجی موفق است.',true);
      drawFilters(data.options);drawMetrics(data.metrics);
      $('report-empty').hidden=data.available&&data.total>0;
      $('report-empty').textContent=data.available?'برای فیلترهای انتخاب‌شده ردیفی وجود ندارد.':'هنوز داده‌ای برای این گزارش دریافت نشده است. پس از تکمیل اتصال منابع، «به‌روزرسانی از منابع» را انتخاب کنید.';
      if(!data.total&&data.catalog_matches?.length){
        $('report-empty').replaceChildren(node('span','کالای مطابق جست‌وجو در کاتالوگ موجود است؛ در نتیجه این گزارش با فیلترهای فعلی نمایش داده نمی‌شود.'));
        for(const item of data.catalog_matches){
          const link=node('a',item.code+' — '+item.title+' · مشاهده مشخصات کالا');link.href=item.url;
          $('report-empty').append(document.createElement('br'),link,document.createElement('br'),node('span',item.reason));
        }
      }
      $('report-table').replaceChildren(...(data.rows.length?[drawTable(data.columns,data.rows,true)]:[]));
      $('report-table').hidden=!data.rows.length;
      $('report-groups').hidden=!data.groups.length;
      const groupMetrics=data.groups[0]?.metrics||[];
      const groupRows=data.groups.map(g=>Object.fromEntries([['group',g.label],...g.metrics.map(m=>[m.name,m.value])]));
      $('groups-table').replaceChildren(...(groupRows.length?[drawTable([{field:'group',label:active==='weekly'?'کارشناس':'گروه'},...groupMetrics.map(m=>({field:m.name,label:m.label}))],groupRows)]:[]));
      $('row-count').textContent=data.available?formatter.format(data.total)+' ردیف · خلاصه‌ها برای تمام نتایج فیلترشده محاسبه شده‌اند.':'';
      $('page-number').textContent=formatter.format(page)+' / '+formatter.format(Math.max(1,Math.ceil(total/50)));
      $('previous-page').disabled=page<=1;$('next-page').disabled=page*50>=total;
      $('export-csv').hidden=!data.available;
      $('export-csv').href=method+'export_csv?'+new URLSearchParams({name:active,filters:JSON.stringify(filters)});
    } catch(e){if(id===request){status(e.message,true);$('report-table').replaceChildren();$('report-metrics').replaceChildren();$('export-csv').hidden=true;}}
    finally{if(id===request)$('report-table').setAttribute('aria-busy','false');}
  }
  function clearSuggestions(){++suggestionRequest;clearTimeout(searchTimer);$('report-search-suggestions').replaceChildren();}
  $('report-search').addEventListener('input',()=>{
    clearSuggestions();const query=$('report-search').value.trim(),id=suggestionRequest,report=active;
    if(query.length<2)return;
    searchTimer=setTimeout(async()=>{try{const data=await api('search_suggestions',{name:report,query,filters:JSON.stringify(readFilters())});if(id!==suggestionRequest||report!==active)return;$('report-search-suggestions').replaceChildren(...data.map(item=>{const option=new Option(item.label,item.value);option.label=item.label;return option;}));}catch{if(id===suggestionRequest)$('report-search-suggestions').replaceChildren();}},250);
  });
  $('select-filters').addEventListener('change',clearSuggestions);
  $('report-filters').addEventListener('submit',e=>{e.preventDefault();clearSuggestions();filters=readFilters();page=1;load();});
  $('clear-filters').addEventListener('click',()=>{clearSuggestions();filters={};page=1;load();});
  $('previous-page').addEventListener('click',()=>{if(page>1){page--;load();}});
  $('next-page').addEventListener('click',()=>{if(page*50<total){page++;load();}});
  window.addEventListener('hashchange',async()=>{clearSuggestions();active=location.hash.slice(1)||'orders';if(active==='reconcile'){location.replace('/portal-products?status=issues');return;}filters={};page=1;sort='';await overview();load();});
  async function monitor(previousStart) {
    let attempts=0;
    clearInterval(polling);
    polling=setInterval(async()=>{try{await overview();const state=statusData.state||{};if(!state.running&&state.started_at&&state.started_at!==previousStart){clearInterval(polling);if(!['settings','incoming'].includes(active))await load();}if(++attempts>=360){clearInterval(polling);status('دریافت هنوز نهایی نشده است. کمی بعد صفحه را تازه کنید.');}}catch(e){clearInterval(polling);status(e.message,true);}},5000);
  }
  $('refresh-source').addEventListener('click',async()=>{const old=statusData?.state?.started_at;$('refresh-source').disabled=true;try{await api('refresh',{},true);status('درخواست به‌روزرسانی ثبت شد؛ در انتظار دریافت داده از منابع…');monitor(old);}catch(e){status(e.message,true);$('refresh-source').disabled=false;}});
  (async()=>{try{await overview();await load();if(statusData.state?.running)monitor(null);}catch(e){status(e.message,true);}})();
})();
