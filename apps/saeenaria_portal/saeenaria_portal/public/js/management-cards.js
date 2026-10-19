(function(){
 const reportStatuses={Draft:'پیش‌نویس',Submitted:'ارسال‌شده','Needs Revision':'نیازمند اصلاح',Approved:'تأییدشده'};
 const decisionStatuses={Open:'در انتظار پاسخ',Answered:'پاسخ داده شده'};
 function el(tag,cls,text){const node=document.createElement(tag);if(cls)node.className=cls;if(text!==undefined)node.textContent=text;return node;}
 function date(value){return value?PortalCalendar.format(String(value).slice(0,10)):'';}
 function section(title,count){const container=el('section','management-column');const header=el('div','management-column-heading');header.append(el('h3','',title),el('span','management-count',new Intl.NumberFormat('fa-IR').format(count)));container.append(header);return container;}
 function block(card,label,value,response=false){const group=el('div',response?'management-detail management-response':'management-detail');group.append(el('h5','management-label',label),el('p','management-text',value||'ثبت نشده'));card.append(group);}
 function cardBase(item,status,domainNames){const card=el('article','management-item');const heading=el('div','management-item-heading');heading.append(el('h4','',item.title||'بدون عنوان'));const badge=el('span','management-status',status);badge.dataset.status=item.status;heading.append(badge);card.append(heading);const meta=el('div','management-meta');meta.append(el('span','',domainNames[item.domain]||item.domain));if(item.is_demo)meta.append(el('span','management-demo','آزمایشی'));card.append(meta);return card;}
 function link(card,type,name,label){const anchor=el('a','management-open',label+' ←');anchor.href='/app/'+type+'/'+encodeURIComponent(name);card.append(anchor);}
 window.renderManagement=function(container,data,domainNames){
  container.replaceChildren();const reports=section('گزارش‌های حوزه',data.reports.length),decisions=section('درخواست‌ها و پاسخ مدیریت',data.decisions.length);
  if(!data.reports.length)reports.append(el('p','management-empty','برای حوزه و نوع داده انتخاب‌شده گزارشی ثبت نشده است.'));
  for(const report of data.reports){const card=cardBase(report,reportStatuses[report.status]||report.status,domainNames);if(report.period_start&&report.period_end)card.append(el('p','management-period','دوره: '+date(report.period_start)+' تا '+date(report.period_end)));block(card,'دستاوردها',report.achievements);block(card,'موانع',report.obstacles);block(card,'برنامه بعد',report.next_plan);block(card,'نظر مدیریت',report.management_comment||'هنوز نظری ثبت نشده است.',true);link(card,'portal-report',report.name,'مشاهده جزئیات و شاخص‌های گزارش');reports.append(card);}
  if(!data.decisions.length)decisions.append(el('p','management-empty','برای حوزه و نوع داده انتخاب‌شده درخواست تصمیمی ثبت نشده است.'));
  for(const decision of data.decisions){const card=cardBase(decision,decisionStatuses[decision.status]||decision.status,domainNames);if(decision.due_date)card.append(el('p','management-period','موعد تصمیم: '+date(decision.due_date)));block(card,'شرح درخواست',decision.request);block(card,'پاسخ مدیریت',decision.response||'هنوز پاسخی ثبت نشده است.',true);if(decision.responded_by_name)card.append(el('p','management-period','پاسخ‌دهنده: '+decision.responded_by_name));if(decision.responded_at)card.append(el('p','management-period','زمان پاسخ: '+date(decision.responded_at)+' — '+String(decision.responded_at).slice(11,16)));link(card,'portal-decision',decision.name,'مشاهده جزئیات درخواست');decisions.append(card);}
  container.append(reports,decisions);
 };
})();
