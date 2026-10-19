(function(root){
 const formatter=new Intl.DateTimeFormat('en-US-u-ca-persian',{year:'numeric',month:'2-digit',day:'2-digit',timeZone:'UTC'});
 function parts(date){const values={};formatter.formatToParts(date).forEach(p=>values[p.type]=p.value);return [Number(values.year),Number(values.month),Number(values.day)];}
 function digits(value){return value.replace(/[۰-۹]/g,c=>String('۰۱۲۳۴۵۶۷۸۹'.indexOf(c))).replace(/[٠-٩]/g,c=>String('٠١٢٣٤٥٦٧٨٩'.indexOf(c)));}
 function toISO(value){if(!value.trim())return '';const match=digits(value.trim()).match(/^(\d{4})\/(\d{1,2})\/(\d{1,2})$/);if(!match)throw Error('تاریخ شمسی باید به صورت سال/ماه/روز باشد');const [y,m,d]=match.slice(1).map(Number);if(y<1300||y>1500||m<1||m>12||d<1||d>31)throw Error('تاریخ شمسی نامعتبر است');const begin=Date.UTC(y+621,2,18);for(let i=0;i<370;i++){const date=new Date(begin+i*86400000);const p=parts(date);if(p[0]===y&&p[1]===m&&p[2]===d)return date.toISOString().slice(0,10);}throw Error('روز در تقویم شمسی وجود ندارد');}
 function format(iso){if(!iso)return '';const p=parts(new Date(iso+'T12:00:00Z'));return [p[0],String(p[1]).padStart(2,'0'),String(p[2]).padStart(2,'0')].join('/').replace(/\d/g,c=>'۰۱۲۳۴۵۶۷۸۹'[c]);}
 root.PortalCalendar={toISO,format};
})(typeof window==='undefined'?globalThis:window);
