import requests,re,logging,urllib3,time
from concurrent.futures import ThreadPoolExecutor,as_completed
urllib3.disable_warnings()
logging.basicConfig(level=logging.INFO)
API_BASE="https://middle-api.magnit.ru"
HEADERS={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36","Accept":"application/json","Origin":"https://magnit.ru","Referer":"https://magnit.ru/"}
DEFAULT_STORES=[
{"code":"992301","address":"Краснодар, ул. Дзержинского, 42","city":"Краснодар"},
{"code":"990101","address":"Краснодарский край","city":"Краснодар"},
{"code":"990102","address":"Краснодарский край","city":"Краснодар"},
{"code":"991002","address":"Ставрополь, ул. Доваторцев, 64","city":"Ставрополь"},
{"code":"991003","address":"Ставрополь, ул. Лермонтова, 259","city":"Ставрополь"},
{"code":"991004","address":"Ставрополь, ул. Краснофлотская, 91","city":"Ставрополь"},
{"code":"991102","address":"Ставрополь, ул. Тухачевского, 22/1","city":"Ставрополь"},
{"code":"991201","address":"Ставрополь, ул. Ленина, 440","city":"Ставрополь"},
{"code":"991301","address":"Ставрополь, пр-кт К.Маркса, 47/30","city":"Ставрополь"},
{"code":"991303","address":"Ставрополь, ул. Пирогова, 8","city":"Ставрополь"},
{"code":"991501","address":"Ставрополь, ул. Трунова, 134В","city":"Ставрополь"},
{"code":"992326","address":"Ставрополь, ул. Чапаева, 25","city":"Ставрополь"},
{"code":"992330","address":"Ставрополь, ул. Рогожникова, 90","city":"Ставрополь"},
{"code":"992334","address":"Ставрополь, пр-кт Кулакова, 29Д","city":"Ставрополь"},
{"code":"997101","address":"Ставрополь, ул. 50 лет ВЛКСМ, 28а","city":"Ставрополь"},
{"code":"997201","address":"Ставрополь, Фестивальный проезд, 7","city":"Ставрополь"},
{"code":"992323","address":"Армавир","city":"Армавир"},
{"code":"995101","address":"Невинномысск","city":"Невинномысск"},
{"code":"992336","address":"Курганинск","city":"Курганинск"},
{"code":"992338","address":"Будённовск","city":"Будённовск"},
{"code":"777885","address":"Москва","city":"Москва"},
{"code":"699422","address":"Санкт-Петербург","city":"Санкт-Петербург"},
]
def extract_volume(name):
    m=re.search(r'(\d+(?:[.,]\d+)?)\s*(мл|л|г|кг|шт)',name,re.IGNORECASE)
    return (float(m.group(1).replace(',','.')),m.group(2).lower()) if m else (None,None)
def calc_price_per_liter(price,name):
    v,u=extract_volume(name)
    if not v:return 0
    if u=='мл':return round(price/(v/1000),2)
    if u=='л':return round(price/v,2)
    return 0
def search_cities(query):
    try:
        r=requests.get(f"{API_BASE}/v1/cities",headers=HEADERS,params={"query":query,"limit":20},timeout=15,verify=False)
        return r.json().get("data",[])
    except:return []
def check_store_code(code):
    try:
        r=requests.post(f"{API_BASE}/v2/goods/search",headers=HEADERS,json={"storeCode":str(code),"storeType":"1","cityId":"1","catalogType":"1","includeAdultGoods":True,"pagination":{"offset":0,"limit":1},"sort":{"order":"desc","type":"discount"}},timeout=4,verify=False)
        return r.json().get("pagination",{}).get("totalCount",0)
    except:return 0
def scan_range(start,end):
    found=[]
    for code in range(start,end):
        t=check_store_code(code)
        if t>0:found.append({"code":str(code),"total":t})
    return found
def fetch_products_page(store_code,offset=0,limit=50,term=None):
    payload={"storeCode":str(store_code),"storeType":"1","cityId":"1","catalogType":"1","includeAdultGoods":True,"pagination":{"offset":offset,"limit":limit},"sort":{"order":"desc","type":"discount"}}
    if term:payload["term"]=term
    try:
        r=requests.post(f"{API_BASE}/v2/goods/search",headers=HEADERS,json=payload,timeout=15,verify=False)
        r.raise_for_status();data=r.json()
    except Exception as e:
        logging.error(f"fetch {store_code} off={offset}: {e}");return [],False,0
    items=data.get("items",[]);pag=data.get("pagination",{});products=[]
    for item in items:
        promo=item.get("promotion") or {}
        if not promo.get("isPromotion"):continue
        price=item.get("price",0)/100;old_price=(promo.get("oldPrice") or 0)/100
        discount=promo.get("discountPercent") or 0
        if discount==0 and old_price>price and old_price>0:discount=round((1-price/old_price)*100)
        stock=item.get("quantity") or 0;name=item.get("name","")
        gallery=item.get("gallery") or [];image=gallery[0].get("url","") if gallery else ""
        v,u=extract_volume(name);vol=f"{v:g} {u}" if v else ""
        products.append({"id":str(item.get("id","")),"name":name,"price":price,"old_price":old_price,"discount_percent":discount,"savings":round(old_price-price,2) if old_price>price else 0,"image":image,"stock":stock,"is_adult":1 if item.get("isForAdults") else 0,"volume":vol,"price_per_liter":calc_price_per_liter(price,name),"store_code":str(store_code)})
    return products,pag.get("hasMore",False),pag.get("totalCount",0)
def parse_store_progressive(store_code,max_items=2000,term=None):
    all_p=[];offset=0;seen=set()
    while len(all_p)<max_items:
        prods,more,total=fetch_products_page(store_code,offset=offset,term=term)
        for p in prods:
            if p["id"] not in seen:seen.add(p["id"]);all_p.append(p)
        if not more or not prods or offset>=10000:break
        offset+=50
    return all_p
def parse_stores_parallel(codes_addr,max_items=1000,term=None,progress_callback=None):
    all_products={}
    def parse_one(ca):
        code,addr=ca;prods=parse_store_progressive(code,max_items=max_items,term=term);return code,addr,prods
    with ThreadPoolExecutor(max_workers=4) as ex:
        futs={ex.submit(parse_one,ca):ca for ca in codes_addr};done=0
        for f in as_completed(futs):
            code,addr,prods=f.result();done+=1
            if progress_callback:progress_callback(done,len(codes_addr),len(all_products))
            for p in prods:
                pid=p["id"]
                if pid not in all_products:all_products[pid]={**p,"stores":[]}
                all_products[pid]["stores"].append({"code":code,"address":addr,"stock":p["stock"],"price":p["price"],"discount_percent":p["discount_percent"]})
                if p["price"]<all_products[pid]["price"]:
                    all_products[pid]["price"]=p["price"];all_products[pid]["discount_percent"]=p["discount_percent"];all_products[pid]["savings"]=p["savings"]
                all_products[pid]["stock"]+=p["stock"]
    result=list(all_products.values())
    for p in result:p["stores"].sort(key=lambda x:x["price"])
    return result
