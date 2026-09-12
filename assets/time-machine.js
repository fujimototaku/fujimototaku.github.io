const machine=document.querySelector("[data-time-machine]");
if(machine){
  const parse=id=>{try{const n=document.getElementById(id);const v=JSON.parse(n?.textContent||"[]");return Array.isArray(v)?v:[]}catch{return[]}};
  const normalize=e=>{
    const date=String(e.date||"").slice(0,10);
    if(!/^\d{4}-\d{2}-\d{2}$/.test(date)||!e.title)return null;
    return{date,type:e.type||"other",source:e.source||"",title:String(e.title),text:String(e.text||""),url:String(e.url||""),image:String(e.image||"")};
  };
  const typeLabel={diary:"DIARY",announcement:"SITE",photo:"PHOTO",movie:"MOVIE",note:"NOTE",x:"X",activity:"ACTIVITY",book:"BOOK",place:"PLACE",other:"MEMORY"};
  const raw=[...parse("tm-manual-data"),...parse("tm-announcement-data"),...parse("tm-post-data")].map(normalize).filter(Boolean);
  const seen=new Set();
  const entries=raw.filter(e=>{const k=`${e.date}|${e.title}|${e.url}`;if(seen.has(k))return false;seen.add(k);return true})
    .sort((a,b)=>a.date.localeCompare(b.date)||a.title.localeCompare(b.title,"ja"));
  const byDate=[...new Set(entries.map(e=>e.date))];
  const groups=new Map(byDate.map(d=>[d,entries.filter(e=>e.date===d)]));
  const $=s=>machine.querySelector(s);
  const dateLabel=$("#tm-date-label"),dateInput=$("#tm-date"),relative=$("#tm-relative"),source=$("#tm-source"),title=$("#tm-title"),text=$("#tm-text"),image=$("#tm-image"),more=$("#tm-more"),rail=$("#tm-range"),start=$("#tm-start"),end=$("#tm-end"),pos=$("#tm-position"),nowBtn=$("#tm-now"),stage=$("#tm-stage");
  let i=Math.max(0,byDate.length-1),touchX=null,used=false;
  const safeUrl=v=>{if(!v)return"";if(v.startsWith("/"))return v;try{const u=new URL(v,location.origin);return["http:","https:"].includes(u.protocol)?u.href:""}catch{return""}};
  const pretty=d=>{const[y,m,day]=d.split("-").map(Number);return`${y}.${String(m).padStart(2,"0")}.${String(day).padStart(2,"0")}`};
  const daysBetween=(a,b)=>Math.round((Date.parse(`${b}T00:00:00Z`)-Date.parse(`${a}T00:00:00Z`))/86400000);
  const relativeText=d=>{
    const latest=byDate.at(-1);if(d===latest)return"最新の記録";
    const n=daysBetween(d,latest);
    if(n<31)return`${n}日前`;
    if(n<365)return`約${Math.round(n/30)}か月前`;
    return`約${(n/365).toFixed(n<730?1:0)}年前`;
  };
  const markUsed=()=>{if(!used){used=true;machine.classList.add("is-used")}};
  const escapeHtml=s=>String(s).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  const render=(animate=true)=>{
    if(!byDate.length){stage.innerHTML='<div class="tm-empty">まだ時間軸に記録がありません。</div>';return}
    const d=byDate[i],items=groups.get(d),hero=items[0];
    dateLabel.textContent=pretty(d);dateInput.value=d;relative.textContent=relativeText(d);
    source.textContent=typeLabel[hero.type]||hero.source||"MEMORY";
    title.textContent=hero.title;text.textContent=hero.text||"";
    const img=safeUrl(hero.image);image.hidden=!img;if(img)image.src=img;
    more.innerHTML=items.slice(1).map(e=>{const u=safeUrl(e.url),label=typeLabel[e.type]||"MEMORY";return u?`<a class="tm-chip" href="${u}">${label} · ${escapeHtml(e.title)}</a>`:`<span class="tm-chip">${label} · ${escapeHtml(e.title)}</span>`}).join("");
    rail.max=Math.max(0,byDate.length-1);rail.value=i;
    start.textContent=byDate[0].slice(0,4);end.textContent=byDate.at(-1).slice(0,4);pos.textContent=`${i+1} / ${byDate.length}`;
    nowBtn.hidden=i===byDate.length-1;
    if(animate&&!matchMedia("(prefers-reduced-motion: reduce)").matches){stage.classList.remove("tm-shift");void stage.offsetWidth;stage.classList.add("tm-shift")}
  };
  const move=n=>{const next=Math.max(0,Math.min(byDate.length-1,i+n));if(next===i)return;i=next;markUsed();render()};
  rail.addEventListener("input",()=>{i=Number(rail.value);markUsed();render(false)});
  rail.addEventListener("change",()=>render(true));
  dateInput.addEventListener("change",()=>{
    const target=dateInput.value;if(!target)return;
    let best=0,bestDist=Infinity;
    byDate.forEach((d,idx)=>{const dist=Math.abs(daysBetween(target,d));if(dist<bestDist){best=idx;bestDist=dist}});
    i=best;markUsed();render();
  });
  nowBtn.addEventListener("click",()=>{i=byDate.length-1;markUsed();render()});
  stage.addEventListener("touchstart",e=>{touchX=e.touches[0].clientX},{passive:true});
  stage.addEventListener("touchend",e=>{if(touchX===null)return;const dx=e.changedTouches[0].clientX-touchX;if(Math.abs(dx)>45)move(dx<0?-1:1);touchX=null},{passive:true});
  document.addEventListener("keydown",e=>{if(e.key==="ArrowLeft")move(-1);if(e.key==="ArrowRight")move(1)});
  render(false);
}
