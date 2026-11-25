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
{"code":"991002","address":"Ставрополь, ул. Доваторцев, д. 64","city":"Ставрополь"},
{"code":"991003","address":"Ставрополь, ул. Лермонтова, д. 259","city":"Ставрополь"},
{"code":"991004","address":"Ставрополь, ул. Краснофлотская, д. 91","city":"Ставрополь"},
{"code":"991102","address":"Ставрополь, ул. Тухачевского, д. 22/1","city":"Ставрополь"},
{"code":"991201","address":"Ставрополь, ул. Ленина, д. 440","city":"Ставрополь"},
{"code":"991301","address":"Ставрополь, пр-кт К.Маркса, д. 47/30","city":"Ставрополь"},
{"code":"991303","address":"Ставрополь, ул. Пирогова, д. 8","city":"Ставрополь"},
{"code":"991501","address":"Ставрополь, ул. Трунова, д. 134В","city":"Ставрополь"},
{"code":"992326","address":"Ставрополь, ул. Чапаева, д. 25","city":"Ставрополь"},
{"code":"992330","address":"Ставрополь, ул. Рогожникова, д. 90","city":"Ставрополь"},
{"code":"992334","address":"Ставрополь, пр-кт Кулакова, д. 29Д","city":"Ставрополь"},
{"code":"997101","address":"Ставрополь, ул. 50 лет ВЛКСМ, д. 28-а","city":"Ставрополь"},
{"code":"997201","address":"Ставрополь, Фестивальный проезд, д. 7","city":"Ставрополь"},
{"code":"991602","address":"Ставропольский край","city":"Ставрополь"},
{"code":"991603","address":"Ставропольский край","city":"Ставрополь"},
{"code":"991604","address":"Ставропольский край","city":"Ставрополь"},
{"code":"991606","address":"Ставропольский край","city":"Ставрополь"},
{"code":"991607","address":"Ставропольский край","city":"Ставрополь"},
{"code":"991608","address":"Ставропольский край","city":"Ставрополь"},
{"code":"991609","address":"Ставропольский край","city":"Ставрополь"},
{"code":"991612","address":"Ставропольский край","city":"Ставрополь"},
{"code":"991801","address":"Ставропольский край","city":"Ставрополь"},
{"code":"991802","address":"Ставропольский край","city":"Ставрополь"},
{"code":"stav_01","address":"Ставрополь, К.Маркса пр-кт, д. 47/30","city":"Ставрополь"},
{"code":"stav_02","address":"Ставрополь, Кулакова пр-кт, д. 69","city":"Ставрополь"},
{"code":"stav_03","address":"Ставрополь, СНТ Оптимист, д. 12","city":"Ставрополь"},
{"code":"stav_04","address":"Ставрополь, Фестивальный проезд, д. 7","city":"Ставрополь"},
{"code":"stav_05","address":"Ставрополь, б-р Зеленая Роща, д. 14","city":"Ставрополь"},
{"code":"stav_06","address":"Ставрополь, ул. Ленина, д. 127 стр 1","city":"Ставрополь"},
{"code":"stav_07","address":"Ставрополь, ул. Западный обход, д. 68а","city":"Ставрополь"},
{"code":"stav_08","address":"Ставрополь, пер. Макарова, д. 22","city":"Ставрополь"},
{"code":"stav_09","address":"Ставрополь, пер. Рубежный, д. 1","city":"Ставрополь"},
{"code":"stav_10","address":"Ставрополь, пер. Шеболдаева, д. 11","city":"Ставрополь"},
{"code":"stav_11","address":"Ставрополь, пр-кт Российский, д. 19","city":"Ставрополь"},
{"code":"stav_12","address":"Ставрополь, ул. 2 Промышленная, д. 1","city":"Ставрополь"},
{"code":"stav_13","address":"Ставрополь, ул. 50 лет ВЛКСМ, д. 28-а","city":"Ставрополь"},
{"code":"stav_14","address":"Ставрополь, ул. 50 лет ВЛКСМ, д. 54/1","city":"Ставрополь"},
{"code":"stav_15","address":"Ставрополь, ул. 50 лет ВЛКСМ, д. 63","city":"Ставрополь"},
{"code":"stav_16","address":"Ставрополь, ул. Апанасенковская, д. 12/1","city":"Ставрополь"},
{"code":"stav_17","address":"Ставрополь, ул. Дзержинского, д. 134","city":"Ставрополь"},
{"code":"stav_18","address":"Ставрополь, ул. Добролюбова / Мира, д. 49/152","city":"Ставрополь"},
{"code":"stav_19","address":"Ставрополь, ул. Доваторцев, д. 181г","city":"Ставрополь"},
{"code":"stav_20","address":"Ставрополь, ул. Доваторцев, д. 32а","city":"Ставрополь"},
{"code":"stav_21","address":"Ставрополь, ул. Доваторцев, д. 64","city":"Ставрополь"},
{"code":"stav_22","address":"Ставрополь, ул. Достоевского, д. 52а","city":"Ставрополь"},
{"code":"stav_23","address":"Ставрополь, ул. Космонавтов, д. 2","city":"Ставрополь"},
{"code":"stav_24","address":"Ставрополь, ул. Краснофлотская, д. 91","city":"Ставрополь"},
{"code":"stav_25","address":"Ставрополь, ул. Л.Толстого, д. 114","city":"Ставрополь"},
{"code":"stav_26","address":"Ставрополь, ул. Ленина, д. 472","city":"Ставрополь"},
{"code":"stav_27","address":"Ставрополь, ул. Лермонтова, д. 259","city":"Ставрополь"},
{"code":"stav_28","address":"Ставрополь, ул. Магистральная","city":"Ставрополь"},
{"code":"stav_29","address":"Ставрополь, ул. Матросова, д. 12","city":"Ставрополь"},
{"code":"stav_30","address":"Ставрополь, ул. Мира, д. 429","city":"Ставрополь"},
{"code":"stav_31","address":"Ставрополь, ул. Пирогова, д. 54в","city":"Ставрополь"},
{"code":"stav_32","address":"Ставрополь, ул. Пирогова, д. 8","city":"Ставрополь"},
{"code":"stav_33","address":"Ставрополь, ул. Рассветная, д. 4","city":"Ставрополь"},
{"code":"stav_34","address":"Ставрополь, ул. Рогожникова, д. 90","city":"Ставрополь"},
{"code":"stav_35","address":"Ставрополь, ул. Салова, д. 70","city":"Ставрополь"},
{"code":"stav_36","address":"Ставрополь, ул. Серова, д. 201","city":"Ставрополь"},
{"code":"stav_37","address":"Ставрополь, ул. Социалистическая, д. 17","city":"Ставрополь"},
{"code":"stav_38","address":"Ставрополь, ул. Трунова, д. 134В","city":"Ставрополь"},
{"code":"stav_39","address":"Ставрополь, ул. Тухачевского, д. 12а","city":"Ставрополь"},
{"code":"stav_40","address":"Ставрополь, ул. Тухачевского, д. 13","city":"Ставрополь"},
{"code":"stav_41","address":"Ставрополь, ул. Тухачевского, д. 22/1","city":"Ставрополь"},
{"code":"stav_42","address":"Ставрополь, ул. Чапаева, д. 25","city":"Ставрополь"},
{"code":"stav_43","address":"Ставрополь, ул. Чапаева, д. 4/1д","city":"Ставрополь"},
{"code":"stav_44","address":"Ставрополь, ул. Южный обход, д. 1а","city":"Ставрополь"},
{"code":"nev_01","address":"Невинномысск, ул Менделеева, д 1","city":"Невинномысск"},
{"code":"nev_02","address":"Невинномысск, ул Баумана, стр 11","city":"Невинномысск"},
{"code":"nev_03","address":"Невинномысск, ул Гагарина, д 21А","city":"Невинномысск"},
{"code":"nev_04","address":"Невинномысск, ул Гагарина, д 56","city":"Невинномысск"},
{"code":"nev_05","address":"Невинномысск, ул Апанасенко, д 82Б","city":"Невинномысск"},
{"code":"nev_06","address":"Невинномысск, Луначарского ул, стр 145","city":"Невинномысск"},
{"code":"262964","address":"Ставрополь (уточните адрес)","city":"Ставрополь"},
{"code":"262969","address":"Ставрополь (уточните адрес)","city":"Ставрополь"},
{"code":"262971","address":"Ставрополь, Назара Енина ул, 1","city":"Ставрополь"},
{"code":"262973","address":"Ставрополь (уточните адрес)","city":"Ставрополь"},
{"code":"262977","address":"Ставрополь (уточните адрес)","city":"Ставрополь"},
{"code":"262982","address":"Ставрополь (уточните адрес)","city":"Ставрополь"},
{"code":"262984","address":"Ставрополь (уточните адрес)","city":"Ставрополь"},
{"code":"262986","address":"Ставрополь (уточните адрес)","city":"Ставрополь"},
{"code":"262988","address":"Ставрополь (уточните адрес)","city":"Ставрополь"},
{"code":"262991","address":"Ставрополь (уточните адрес)","city":"Ставрополь"},
{"code":"262993","address":"Ставрополь (уточните адрес)","city":"Ставрополь"},
{"code":"262997","address":"Ставрополь (уточните адрес)","city":"Ставрополь"},
{"code":"262999","address":"Ставрополь (уточните адрес)","city":"Ставрополь"},
{"code":"263001","address":"Ставрополь (уточните адрес)","city":"Ставрополь"},
{"code":"263010","address":"Ставрополь (уточните адрес)","city":"Ставрополь"},
{"code":"260001","address":"Ставропольский край","city":"Ставрополь"},
{"code":"stav_new_01","address":"Ставрополь, Октябрьская ул, 233и","city":"Ставрополь"},
{"code":"stav_new_02","address":"Ставрополь, ул Пирогова, д 15А","city":"Ставрополь"},
{"code":"stav_new_03","address":"Ставрополь, ул Тельмана, д 234/1","city":"Ставрополь"},
{"code":"stav_new_04","address":"Ставрополь, ул 45 Параллель, д 22Б","city":"Ставрополь"},
{"code":"stav_new_05","address":"Ставрополь, ул Тухачевского, д 26","city":"Ставрополь"},
{"code":"992323","address":"Армавир","city":"Армавир"},
{"code":"995101","address":"Невинномысск","city":"Невинномысск"},
{"code":"992336","address":"Курганинск, ул Партизанская, д 215","city":"Курганинск"},
{"code":"992338","address":"Курганинск, ул Р.Люксембург, д 263","city":"Будённовск"},
{"code":"992338","address":"Курганинск, ул Р.Люксембург, д 263","city":"Курганинск"},
{"code":"992341","address":"Курганинск, ул Энгельса, д 314","city":"Курганинск"},
{"code":"992349","address":"Курганинск, ул Р.Люксембург, д 423","city":"Курганинск"},
{"code":"992358","address":"Курганинск, ул Матросова, д 186","city":"Курганинск"},
{"code":"992359","address":"Курганинск, ул Кочергина, д 158","city":"Курганинск"},
{"code":"992364","address":"Курганинск, ул Ленина, д 100","city":"Курганинск"},
{"code":"992365","address":"Курганинск, ул Красная, д 50","city":"Курганинск"},
{"code":"992340","address":"Краснодарский край (зона 12.99)","city":"Краснодарский край"},
{"code":"992342","address":"Краснодарский край (зона 9.99)","city":"Краснодарский край"},
{"code":"992343","address":"Краснодарский край (зона 9.99)","city":"Краснодарский край"},
{"code":"992344","address":"Краснодарский край (зона 9.99)","city":"Краснодарский край"},
{"code":"992347","address":"Краснодарский край (зона 10.29)","city":"Краснодарский край"},
{"code":"992351","address":"Краснодарский край (зона 9.99)","city":"Краснодарский край"},
{"code":"992352","address":"Краснодарский край (зона 12.29)","city":"Краснодарский край"},
{"code":"992354","address":"Краснодарский край (зона 10.29)","city":"Краснодарский край"},
{"code":"992356","address":"Краснодарский край (зона 10.29)","city":"Краснодарский край"},
{"code":"992357","address":"Краснодарский край (зона 10.29)","city":"Краснодарский край"},
{"code":"992360","address":"Краснодарский край (зона 10.29)","city":"Краснодарский край"},
{"code":"992362","address":"Краснодарский край (зона 10.29)","city":"Краснодарский край"},
{"code":"992367","address":"Краснодарский край (зона 10.29)","city":"Краснодарский край"},
{"code":"992368","address":"Краснодарский край (зона 10.29)","city":"Краснодарский край"},
{"code":"992369","address":"Краснодарский край (зона 10.29)","city":"Краснодарский край"},
{"code":"992371","address":"Краснодарский край (зона 10.99)","city":"Краснодарский край"},
{"code":"992373","address":"Краснодарский край (зона 10.29)","city":"Краснодарский край"},
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
    with ThreadPoolExecutor(max_workers=2) as ex:
        futs={ex.submit(parse_one,ca):ca for ca in codes_addr};done=0
        for f in as_completed(futs):
            code,addr,prods=f.result();done+=1
            if progress_callback:progress_callback(done,len(codes_addr),len(all_products))
            for p in prods:
                pid=p["id"]
                if pid not in all_products:all_products[pid]={**p,"stores":[]}
                all_products[pid]["stores"].append({"code":code,"address":addr,"stock":p["stock"],"price":p["price"],"discount_percent":p["discount_percent"]})
                if p["price"]<all_products[pid]["price"]:
                    all_products[pid]["price"]=p["price"];all_products[pid]["savings"]=p["savings"]
                if p["discount_percent"]>all_products[pid]["discount_percent"]:
                    all_products[pid]["discount_percent"]=p["discount_percent"]
                    all_products[pid]["old_price"]=p["old_price"]
                all_products[pid]["stock"]+=p["stock"]
    result=list(all_products.values())
    for p in result:p["stores"].sort(key=lambda x:x["price"])
    return result
