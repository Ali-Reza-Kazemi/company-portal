/* Flat navigation: ordinary links, native keyboard behavior, server-authorized extras. */
(()=>{
 'use strict';
 const header=document.querySelector('body > header'),main=document.querySelector('body > main');
 if(!header||!main)return;
 document.body.classList.add('portal-ui');
 main.id=main.id||'portal-main';
 const skip=document.createElement('a');skip.href='#'+main.id;skip.className='ui-skip';skip.textContent='رفتن به محتوای اصلی';
 main.tabIndex=-1;document.body.prepend(skip);
 const nav=document.createElement('nav');nav.className='ui-navigation';nav.setAttribute('aria-label','بخش‌های اصلی پورتال');
 const links=new Map();
 function add(url,label){
  if(links.has(url))return;
  const link=document.createElement('a');link.href=url;link.textContent=label;
  if(location.pathname.replace(/\/$/,'')===url)link.setAttribute('aria-current','page');
  nav.append(link);links.set(url,link);
 }
 add('/portal','کارها و عملکرد');add('/portal-staff','مرخصی و مأموریت');add('/portal-reviews','بررسی و تأیید');
 // Capture links already rendered for this user's permissions before hiding duplicate navigation.
 for(const link of header.querySelectorAll('a[href]')){
  const url=link.getAttribute('href');
  if(['/portal-purchase','/portal-inventory','/portal-products','/portal-admin'].includes(url))add(url,link.textContent.trim());
 }
 add('/portal-training','آموزش');add('/portal-account','حساب من');
 header.append(nav);
 const context=document.createElement('div');context.className='ui-page-context';
 const brand=document.createElement('span');brand.textContent='صائین آریا';
 const separator=document.createElement('span');separator.textContent='/';separator.setAttribute('aria-hidden','true');
 const title=document.createElement('span');title.textContent=document.querySelector('h1')?.textContent||document.title;
 context.append(brand,separator,title);main.prepend(context);
 fetch('/api/method/saeenaria_portal.api.environment_navigation')
  .then(response=>response.ok?response.json():Promise.reject())
  .then(payload=>{
   for(const link of payload.message?.links||[]){
    if(['/portal-purchase','/portal-inventory','/portal-products','/portal-admin'].includes(link.url))add(link.url,link.label);
    if(link.kind==='records'){
     add(link.url,'تنظیمات و فرم‌ها');
    }
    if(link.kind==='build')add(link.url,link.label);
   }
   const order=['/portal','/portal-staff','/portal-reviews','/portal-purchase','/portal-inventory','/portal-products','/portal-admin','/desk/saeenaria-portal/portal-domain','/desk/build','/portal-training','/portal-account'];
   for(const url of order)if(links.has(url))nav.append(links.get(url));
  })
  .catch(()=>{});
 for(const region of main.querySelectorAll('.scroll,.table-wrap,.purchase-scroll')){
  region.tabIndex=0;region.setAttribute('role','region');region.setAttribute('aria-label','جدول؛ برای مشاهده ستون‌های بیشتر پیمایش کنید');
 }
})();
