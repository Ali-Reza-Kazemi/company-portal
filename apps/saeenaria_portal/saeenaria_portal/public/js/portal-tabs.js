(()=>{
 const sections=[['tasks-card','کارها و پیشرفت'],['form-card','ثبت و واگذاری کار'],['metrics-card','شاخص‌ها'],['management-card','گزارش‌ها و تصمیم‌ها'],['people-card','اعضا و نقش‌ها']].map(([id,label])=>({panel:document.getElementById(id),id,label})).filter(x=>x.panel);
 if(!sections.length)return;
 const main=document.querySelector('main'),nav=document.createElement('div');nav.className='portal-tabs';nav.setAttribute('role','tablist');nav.setAttribute('aria-label','بخش‌های پورتال');
 const oldNav=document.querySelector('.portal-quick-links');
 if(!oldNav)return;
 const directLinks=[...oldNav.querySelectorAll('a[href]')].filter(a=>!a.getAttribute('href').startsWith('#'));
 for(const link of directLinks.filter(a=>a.getAttribute('href').startsWith('/portal-')))link.classList.add('portal-module-link');
 oldNav.replaceChildren(...directLinks);oldNav.hidden=true;main.prepend(nav);
 const toolbar=document.querySelector('#tasks-card .toolbar'),filters=document.createElement('section');filters.className='card portal-shared-filters';
 const summary=document.createElement('h2');summary.textContent='محدوده نمایش اطلاعات';filters.append(summary,toolbar);nav.after(filters);
 const actions=document.createElement('div');actions.className='portal-task-tools';for(const b of [document.getElementById('csv'),toolbar.querySelector('button[onclick]')])if(b)actions.append(b);document.querySelector('#tasks-card h2').after(actions);
 const scope=document.getElementById('filter-scope').parentElement;
 const destinations={'metrics-card':['/app/portal-metric-value'],'management-card':['/app/portal-report','/app/portal-decision']};
 for(const [id,urls] of Object.entries(destinations)){const panel=document.getElementById(id);if(!panel)continue;const tools=document.createElement('div');tools.className='portal-task-tools';for(const link of directLinks.filter(a=>urls.includes(a.getAttribute('href'))))tools.append(link);panel.querySelector('h2').after(tools);}

 function activate(id,focus=false){const active=sections.find(x=>x.id===id)||sections[0];for(const s of sections){const yes=s===active;s.panel.hidden=!yes;s.button.setAttribute('aria-selected',String(yes));s.button.tabIndex=yes?0:-1;}filters.hidden=!['tasks-card','metrics-card','management-card'].includes(active.id);scope.hidden=active.id!=='tasks-card';if(focus)active.button.focus();return active.id;}
 for(const s of sections){const button=document.createElement('button');button.type='button';button.id='tab-'+s.id;button.textContent=s.label;button.setAttribute('role','tab');button.setAttribute('aria-controls',s.id);s.panel.setAttribute('role','tabpanel');s.panel.setAttribute('aria-labelledby',button.id);s.panel.tabIndex=0;s.button=button;nav.append(button);button.onclick=()=>{const id=activate(s.id);if(location.hash!=='#'+id)history.pushState(null,'','#'+id);};button.onkeydown=e=>{let index=sections.indexOf(s);if(e.key==='ArrowLeft')index=(index+1)%sections.length;else if(e.key==='ArrowRight')index=(index+sections.length-1)%sections.length;else if(e.key==='Home')index=0;else if(e.key==='End')index=sections.length-1;else return;e.preventDefault();sections[index].button.click();sections[index].button.focus();};}
 window.addEventListener('hashchange',()=>activate(location.hash.slice(1)));window.addEventListener('popstate',()=>activate(location.hash.slice(1)));
 activate(location.hash.slice(1));
})();
