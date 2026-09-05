#!/usr/bin/env python3
import argparse, csv, datetime as dt, hashlib, json, os, re, sys, time
from pathlib import Path
from urllib.parse import urljoin, urlparse, urlunparse, parse_qsl, urlencode
import requests
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parent; DATA=ROOT/'data.json'; CSV=ROOT/'data.csv'
UA='CapitalHarvester/0.1 (+https://fujimototaku.github.io/)'
KW=re.compile(r'キャンペーン|特典|プレゼント|ポイント|還元|キャッシュバック|クーポン|無料|新規|初回|入会|登録|口座開設|乗り換え|MNP|招待|紹介|おかえり|カムバック|増量|山分け|抽選|もらえる|ギフト|cashback|campaign|offer|bonus|reward',re.I)
BAD=re.compile(r'privacy|利用規約|terms|company|採用|問い合わせ|faq|login|ログイン',re.I)
TAGS={
 'free_or_zero':r'無料|0円|ゼロ円|登録だけ|口座開設だけ|投資不要|購入不要',
 'new_only':r'新規|初めて|はじめて|初回|入会者対象',
 'reentry':r'再入会|再登録|再契約|おかえり|カムバック|復帰|再度対象',
 'targeted':r'対象者限定|限定オファー|あなたへの|個別にお知らせ|表示された方|メールが届いた方',
 'kyc':r'本人確認|KYC|マイナンバー|本人認証',
 'spend_required':r'購入|利用で|決済で|お買い物|合計.{0,12}円以上|チャージ.{0,12}円以上',
 'deposit_required':r'入金|預入|残高.{0,10}円以上|資金拘束',
 'investment_required':r'投資|取引|積立|株式|FX|暗号資産|クラウドファンディング|社債',
 'borrowing_risk':r'ローン|借入|リボ|キャッシング|あと払い|分割払い',
 'subscription':r'サブスク|月額|定額|無料体験|トライアル',
 'telecom':r'MNP|乗り換え|回線|SIM|eSIM|スマホ|携帯',
 'lottery':r'抽選|山分け|当選|くじ|ガチャ',
 'guaranteed':r'もれなく|全員|必ず|プレゼント|進呈'}
TAGS={k:re.compile(v,re.I) for k,v in TAGS.items()}
MONEY=re.compile(r'(?:最大|合計最大|もれなく|全員に|プレゼント|特典)?\s*([0-9][0-9,]{0,8})\s*(?:円|円相当|ポイント|pt|Pontaポイント|PayPayポイント|Vポイント)',re.I)
PCT=re.compile(r'([0-9]{1,3}(?:\.[0-9]+)?)\s*%\s*(?:還元|OFF|オフ|戻)',re.I)
DATE1=re.compile(r'(20\d{2})[年/.\-](\d{1,2})[月/.\-](\d{1,2})日?'); DATE2=re.compile(r'(\d{1,2})[月/.\-](\d{1,2})日?')

SOURCES=[
 ('PayPay','payments','https://paypay.ne.jp/event/'),('PayPayお知らせ','payments','https://paypay.ne.jp/notice/campaign/'),('PayPay地域還元','local-benefits','https://paypay.ne.jp/event/support-local/'),('PayPayカード','cards','https://www.paypay-card.co.jp/event/'),
 ('auじぶん銀行','banking','https://www.jibunbank.co.jp/campaign/'),('三井住友カード','cards','https://www.smbc-card.com/camp/'),('Vクーポン','cards','https://www.smbc-card.com/camp/vcoupon/index.jsp'),('SBI証券','brokerage','https://www.sbisec.co.jp/ETGate/WPLETmgR001Control?OutSide=on&getFlg=on&burl=search_campaign&cat1=campaign&dir=campaign&file=campaign.html'),('楽天証券','brokerage','https://www.rakuten-sec.co.jp/web/campaign/'),('マネックス証券','brokerage','https://info.monex.co.jp/news/campaign/'),('松井証券','brokerage','https://www.matsui.co.jp/campaign/'),('楽天銀行','banking','https://www.rakuten-bank.co.jp/campaign/'),('住信SBIネット銀行','banking','https://www.netbk.co.jp/contents/cmp/'),('ソニー銀行','banking','https://moneykit.net/visitor/campaign/'),
 ('楽天ポイント','points','https://point.rakuten.co.jp/campaign/'),('Ponta','points','https://www.ponta.jp/c/campaign/'),('Ponta PLAY','games-offerwall','https://play.ponta.jp/campaign/index.html'),('dポイント','points','https://dpoint.docomo.ne.jp/cp_2/index.html'),('au PAY','payments','https://aupay.wallet.auone.jp/campaign/'),
 ('povo','telecom','https://povo.jp/campaign'),('LINEMO','telecom','https://www.linemo.jp/campaign/index_a.html'),('Y!mobile','telecom','https://www.ymobile.jp/cp/'),('楽天モバイル','telecom','https://network.mobile.rakuten.co.jp/campaign/'),('SoftBank','telecom','https://www.softbank.jp/mobile/campaigns/'),('ドコモ','telecom','https://www.docomo.ne.jp/campaign_event/'),
 ('ファミリーマート','retail','https://www.family.co.jp/campaign.html'),('ローソンセール','retail','https://www.lawson.co.jp/recommend/sale/index.html'),('ローソンキャンペーン','retail','https://www.lawson.co.jp/lab/entertainment/campaign/index.html'),('セブン-イレブン','retail','https://www.sej.co.jp/cmp/'),('Amazon Pay','payments','https://pay.amazon.co.jp/shop/campaign'),('メルカリ','marketplace','https://jp-news.mercari.com/campaign/'),('Yahoo!ショッピング','marketplace','https://shopping.yahoo.co.jp/promotion/campaign/'),
 ('ハピタス','point-site','https://hapitas.jp/campaign/'),('モッピー','point-site','https://pc.moppy.jp/campaign/'),('ワラウ','point-site','https://www.warau.jp/service/campaign/list/'),('ECナビ','point-site','https://ecnavi.jp/campaign/'),('ちょびリッチ','point-site','https://www.chobirich.com/campaign/'),('ポイントタウン','point-site','https://www.pointtown.com/ptu/campaign/')]
QUERIES='''
2026 日本 キャンペーン 無料登録 もれなく ポイント プレゼント
2026 日本 おかえり 再入会 再登録 再契約 特典
2026 日本 対象者限定 キャンペーン ポイント メール アプリ限定
2026 日本 KYC 本人確認 だけ プレゼント ポイント 無料
2026 日本 新規口座開設 投資不要 現金 Amazonギフト ポイント
2026 日本 銀行 証券 カード 既存顧客 限定 キャンペーン
2026 日本 PayPay au PAY 楽天ペイ d払い ファミペイ キャンペーン
2026 日本 MNP SIM eSIM 回線 端末 キャンペーン
2026 日本 ゲーム ポイ活 Offerwall 無課金 新規
2026 日本 アプリ 初回起動 ログイン 登録 ポイント
2026 日本 無料体験 再入会 カムバック 特典
2026 日本 買取 増額 不用品 フリマ 出品 キャンペーン
2026 日本 自治体 キャッシュレス 還元 給付金 商品券 支援
2026 日本 コンビニ 無料 クーポン 1個もらえる
2026 日本 Ponta Vポイント dポイント 楽天ポイント 増量
2026 日本 レシート ログインだけ アプリダウンロード プレゼント
2026 日本 BaaS 地銀 アプリ 新規口座 キャンペーン
2026 日本 Apple Pay Google Pay 初回 キャンペーン
2026 日本 Web3 ウォレット カード 新規 無料 キャンペーン
2026 日本 100円 200円 500円 全員 キャンペーン
'''.strip().splitlines()

def now(): return dt.datetime.now(dt.timezone.utc).astimezone().isoformat(timespec='seconds')
def canon(u):
 try:
  p=urlparse(u.strip()); q=[(k,v) for k,v in parse_qsl(p.query,keep_blank_values=True) if not k.lower().startswith('utm_') and k.lower() not in {'fbclid','gclid','yclid','ref','referrer','scid'}]
  return urlunparse((p.scheme.lower(),p.netloc.lower(),p.path.rstrip('/'),'',urlencode(q),''))
 except: return u.strip()
def iid(t,u): return hashlib.sha1((re.sub(r'\s+',' ',t.lower()).strip()+'|'+canon(u)).encode()).hexdigest()[:16]
def fetch(u):
 try:
  r=requests.get(u,headers={'User-Agent':UA,'Accept-Language':'ja,en;q=0.7'},timeout=18); r.raise_for_status(); r.encoding=r.apparent_encoding or r.encoding; return r
 except: return None
def text_soup(r):
 s=BeautifulSoup(r.text,'html.parser'); [x.decompose() for x in s(['script','style','noscript','svg'])]; return s,re.sub(r'\s+',' ',' '.join(s.stripped_strings))[:50000]
def title(s,fb):
 h=s.find('h1'); x=' '.join(h.stripped_strings).strip() if h else ''; return (x or (s.title.string.strip() if s.title and s.title.string else fb))[:180]
def tags(txt): return [k for k,p in TAGS.items() if p.search(txt)]
def reward(txt):
 vals=[]
 for m in MONEY.finditer(txt[:18000]):
  try:
   v=int(m.group(1).replace(',',''))
   if 1<=v<=10000000: vals.append((v,m.group(0)[:80]))
  except: pass
 if vals:return max(vals,key=lambda x:x[0])
 m=PCT.search(txt[:18000]); return (None,m.group(0)[:80]) if m else (None,'')
def deadline(txt):
 today=dt.date.today(); ds=[]
 for p in (DATE1,DATE2):
  for m in p.finditer(txt[:12000]):
   try:
    if len(m.groups())==3:y,mo,d=map(int,m.groups())
    else:
     mo,d=map(int,m.groups()); y=today.year
     if dt.date(y,mo,d)<today-dt.timedelta(days=120):y+=1
    z=dt.date(y,mo,d)
    if today-dt.timedelta(days=60)<=z<=today+dt.timedelta(days=730):ds.append(z)
   except:pass
 f=[x for x in ds if x>=today]; return min(f).isoformat() if f else None
def parse(u,src,cat,fb='',evidence='direct'):
 r=fetch(u)
 if not r:return None
 s,txt=text_soup(r)
 if not KW.search(txt):return None
 t=title(s,fb or src); rv,rt=reward(txt); ts=now()
 return {'id':iid(t,u),'title':t,'url':canon(u),'source_name':src,'category':cat,'source_type':'official','excerpt':txt[:900],'reward_yen_est':rv,'reward_text':rt,'tags':tags(txt),'discovered_at':ts,'last_seen_at':ts,'deadline':deadline(txt),'status':'active','evidence_level':evidence}
def crawl(src,cat,u,maxlinks):
 r=fetch(u)
 if not r:return []
 s,_=text_soup(r); out=[]; idx=parse(u,src,cat,src)
 if idx: idx['title']=src+' — キャンペーン一覧'; idx['id']=iid(idx['title'],u); out.append(idx)
 seen=set()
 for a in s.find_all('a',href=True):
  label=' '.join(a.stripped_strings).strip(); v=canon(urljoin(u,a['href']))
  if not v.startswith('http') or v in seen or BAD.search(label+' '+v) or not KW.search(label+' '+v):continue
  if urlparse(v).netloc!=urlparse(u).netloc:continue
  seen.add(v); x=parse(v,src,cat,label)
  if x:out.append(x)
  if len(seen)>=maxlinks:break
  time.sleep(.08)
 return out
def existing():
 try:return {x['id']:x for x in json.loads(DATA.read_text())['items']}
 except:return {}
def ai_discover(known,nq):
 if not os.getenv('OPENAI_API_KEY'):return []
 try:from openai import OpenAI
 except:return []
 qs=QUERIES; start=(dt.date.today().toordinal()*nq)%len(qs); qs=(qs+qs)[start:start+nq]
 schema={'type':'object','properties':{'items':{'type':'array','items':{'type':'object','properties':{'title':{'type':'string'},'url':{'type':'string'},'source_name':{'type':'string'},'category':{'type':'string'},'summary':{'type':'string'},'reward_yen_est':{'type':['integer','null']},'reward_text':{'type':'string'},'deadline':{'type':['string','null']},'tags':{'type':'array','items':{'type':'string'}}},'required':['title','url','source_name','category','summary','reward_yen_est','reward_text','deadline','tags'],'additionalProperties':False}}},'required':['items'],'additionalProperties':False}
 try:
  r=OpenAI().responses.create(model=os.getenv('OPENAI_MODEL','gpt-5.6-luna'),reasoning={'effort':'low'},tools=[{'type':'web_search','search_context_size':'medium','user_location':{'type':'approximate','country':'JP'}}],input=[{'role':'system','content':'Search the current web for lawful capital giveaways usable by people in Japan. Collect first, filter later: tiny rewards too. Include free signup/KYC, new/re-entry/comeback, targeted-user public clues, points/payment/cards/banks/brokerage, MNP/telecom/devices, apps/games/offerwalls, retail coupons, public benefits, resale bonuses, and spend/investment-required promotions tagged as such. Prefer direct official URLs. Return current/upcoming items only.'},{'role':'user','content':'Search these query families now:\n'+'\n'.join('- '+q for q in qs)}],text={'format':{'type':'json_schema','name':'capital_giveaways','strict':True,'schema':schema}})
  d=json.loads(r.output_text)
 except Exception as e: print('AI discovery failed:',e,file=sys.stderr); return []
 ts=now(); out=[]
 for x in d.get('items',[]):
  u=canon(x['url'])
  if not u or u in known:continue
  tg=sorted(set(x['tags'])|set(tags(x['summary'])))
  out.append({'id':iid(x['title'],u),'title':x['title'][:180],'url':u,'source_name':x['source_name'][:80],'category':x['category'][:80],'source_type':'web-search','excerpt':x['summary'][:900],'reward_yen_est':x['reward_yen_est'],'reward_text':x['reward_text'][:120],'tags':tg,'discovered_at':ts,'last_seen_at':ts,'deadline':x['deadline'],'status':'active','evidence_level':'search-lead'})
 return out
def merge(new,old):
 seen=set(); m=dict(old)
 for x in new:
  seen.add(x['id'])
  if x['id'] in m:x['discovered_at']=m[x['id']].get('discovered_at',x['discovered_at'])
  m[x['id']]=x
 z=dt.datetime.now(dt.timezone.utc)
 for k,x in m.items():
  if k in seen:continue
  try:
   q=dt.datetime.fromisoformat(x['last_seen_at'].replace('Z','+00:00'))
   if q.tzinfo is None:q=q.replace(tzinfo=dt.timezone.utc)
   if (z-q.astimezone(dt.timezone.utc)).days>=14:x['status']='stale'
  except:pass
 def sc(x):
  t=x.get('tags',[]); bonus=(40000 if 'targeted'in t else 0)+(30000 if'reentry'in t else 0)+(20000 if'free_or_zero'in t else 0)+(10000 if'guaranteed'in t else 0)-(5000 if'lottery'in t else 0)-(50000 if'borrowing_risk'in t else 0)
  return (0 if x.get('status')=='active' else 1,-((x.get('reward_yen_est')or 0)+bonus),x.get('deadline')or'9999')
 return sorted(m.values(),key=sc)
def write(items,ok):
 meta={'generated_at':now(),'source_count':len(SOURCES),'source_success_count':ok,'active_count':sum(x['status']=='active' for x in items),'total_count':len(items),'note':'Collect first, filter later. Reward amounts are heuristic leads; confirm conditions before execution.'}
 DATA.write_text(json.dumps({'meta':meta,'items':items},ensure_ascii=False,indent=2))
 fs=['id','status','title','source_name','category','reward_yen_est','reward_text','deadline','tags','url','discovered_at','last_seen_at','excerpt','evidence_level']
 with CSV.open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fs);w.writeheader()
  for x in items:y={k:x.get(k) for k in fs};y['tags']=','.join(x.get('tags',[]));w.writerow(y)
 print(json.dumps(meta,ensure_ascii=False))
def main():
 a=argparse.ArgumentParser();a.add_argument('--max-links',type=int,default=12);a.add_argument('--ai',action='store_true');a.add_argument('--ai-query-count',type=int,default=12);o=a.parse_args();old=existing(); found=[];ok=0
 for i,(s,c,u) in enumerate(SOURCES,1):
  xs=crawl(s,c,u,o.max_links); found+=xs;ok+=bool(xs);print(f'[{i}/{len(SOURCES)}] {s}: {len(xs)}')
 if o.ai:
  xs=ai_discover({x['url'] for x in found},o.ai_query_count); found+=xs;print('AI web discovery:',len(xs))
 write(merge(found,old),ok)
if __name__=='__main__':main()
