(function(){
 const C=PortalCalendar,fa=v=>String(v).replace(/\d/g,c=>'۰۱۲۳۴۵۶۷۸۹'[c]),months=['فروردین','اردیبهشت','خرداد','تیر','مرداد','شهریور','مهر','آبان','آذر','دی','بهمن','اسفند'];
 const today=()=>new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Tehran',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());
 const dialog=document.createElement('dialog');dialog.className='portal-date-dialog';document.body.append(dialog);
 function el(tag,text,parent,cls){const e=document.createElement(tag);if(text)e.textContent=text;if(cls)e.className=cls;if(tag==='button')e.type='button';parent.append(e);return e;}
 function open(input){
  let current;try{current=C.toISO(input.value)||today();}catch{current=today();}
  let [year,month]=C.format(current).replace(/[۰-۹]/g,c=>'۰۱۲۳۴۵۶۷۸۹'.indexOf(c)).split('/').map(Number),ticket=0;
  const choose=date=>{input.value=date?C.format(date):'';input.setCustomValidity('');input.dispatchEvent(new Event('change',{bubbles:true}));dialog.close();input.focus();};
  function draw(){
   const version=++ticket;dialog.replaceChildren();const heading=el('div','',dialog,'portal-date-heading');el('strong',document.querySelector('label[for="'+input.id+'"]')?.textContent||'انتخاب تاریخ شمسی',heading);el('button','×',heading).onclick=()=>dialog.close();
   const nav=el('div','',dialog,'saeenaria-cal-nav');el('button','‹',nav).onclick=()=>{if(year===1300&&month===1)return;if(--month===0){month=12;year--;}draw();};
   const m=el('select','',nav);m.setAttribute('aria-label','ماه شمسی');months.forEach((name,i)=>m.add(new Option(name,i+1)));m.value=month;m.onchange=()=>{month=+m.value;draw();};
   const y=el('select','',nav);y.setAttribute('aria-label','سال شمسی');for(let n=1500;n>=1300;n--)y.add(new Option(fa(n),n));y.value=year;y.onchange=()=>{year=+y.value;draw();};
   el('button','›',nav).onclick=()=>{if(year===1500&&month===12)return;if(++month===13){month=1;year++;}draw();};
   nav.firstElementChild.innerHTML='<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M9 6l6 6-6 6"/></svg>';nav.firstElementChild.setAttribute('aria-label','ماه قبل');nav.lastElementChild.innerHTML='<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M15 6l-6 6 6 6"/></svg>';nav.lastElementChild.setAttribute('aria-label','ماه بعد');
   const grid=el('div','',dialog,'saeenaria-cal-grid');['ش','ی','د','س','چ','پ','ج'].forEach((d,i)=>el('div',d,grid,'saeenaria-cal-weekday'+(i>4?' is-off':'')));
   const first=C.toISO(`${year}/${month}/1`);for(let i=0;i<(new Date(first+'T12:00:00Z').getUTCDay()+1)%7;i++)el('span','',grid);
   let last=first;const days=[];
   for(let day=1;day<=31;day++){let date;try{date=C.toISO(`${year}/${month}/${day}`);}catch{break;}last=date;const dow=new Date(date+'T12:00:00Z').getUTCDay();const b=el('button',fa(day),grid,'saeenaria-cal-day'+([4,5].includes(dow)?' is-off':'')+(date===today()?' is-today':'')+(date===current?' is-selected':''));b.title=[4,5].includes(dow)?'تعطیل کاری':'روز کاری';b.setAttribute('aria-label',C.format(date)+' — '+b.title);b.onclick=()=>choose(date);days.push([date,b]);}
   const info=el('div','پنجشنبه و جمعه و تعطیلات ثبت‌شده با رنگ صورتی مشخص‌اند.',dialog,'saeenaria-cal-info');
   const footer=el('div','',dialog,'saeenaria-cal-footer');el('button','امروز',footer).onclick=()=>choose(today());el('button','پاک کردن',footer).onclick=()=>choose('');
   fetch('/api/method/saeenaria_portal.api.calendar_holidays?'+new URLSearchParams({start:first,end:last})).then(r=>{if(!r.ok)throw Error();return r.json();}).then(data=>{if(version!==ticket||!dialog.open)return;for(const h of data.message||[]){const pair=days.find(([date])=>date===h.date);if(pair){pair[1].classList.add('is-off');pair[1].title=h.title;pair[1].setAttribute('aria-label',C.format(h.date)+' — '+h.title);}}}).catch(()=>{if(version===ticket)info.textContent='تعطیلات ثبت‌شده دریافت نشد؛ پنجشنبه و جمعه مشخص‌اند.';});
  }
  dialog.showModal();draw();
 }
 for(const input of document.querySelectorAll('#from,#to,#start,#due,[data-jalali-date]')){const id=input.id;const wrap=document.createElement('div');wrap.className='portal-date-field';input.before(wrap);wrap.append(input);input.classList.add('saeenaria-date-input');input.inputMode='numeric';input.autocomplete='off';const b=el('button','▦',wrap,'saeenaria-date-button');b.setAttribute('aria-label','باز کردن تقویم شمسی '+(document.querySelector('label[for="'+id+'"]')?.textContent||''));b.title='تقویم شمسی';b.onclick=()=>open(input);if(document.getElementById('staff-request-form'))input.addEventListener('click',()=>{if(!dialog.open)open(input);});input.addEventListener('input',()=>input.setCustomValidity(''));input.addEventListener('change',()=>{try{const iso=C.toISO(input.value);input.value=iso?C.format(iso):'';input.setCustomValidity('');}catch(e){input.setCustomValidity(e.message);}});}
})();
