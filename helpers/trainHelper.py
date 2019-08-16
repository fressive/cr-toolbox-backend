import datetime
import data.trains as train_names
import json
import re
import requests
from diskcache import Cache

STATION_TRAIN_CODE_RE = re.compile(r"(.+)\((.+)-(.+)\)")

stations = Cache("cache/station") # 存储站点信息
trains = Cache("cache/train") # 存储列车信息
schedulers = Cache("cache/sche") # 存储时刻表

TRAIN_LIST_API = "https://kyfw.12306.cn/otn/resources/js/query/train_list.js?scriptVersion=1.0"
STATION_NAMES_API = "https://kyfw.12306.cn/otn/resources/js/framework/station_name.js"
GET_SCHEDULER_API = "https://kyfw.12306.cn/otn/czxx/queryByTrainNo"

req = requests.Session()
req.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US) AppleWebKit/534.16 (KHTML, like Gecko) Chrome/10.0.648.133 Safari/534.16",
})


def parseStations(s):
    data = s.split("|")
    for i in range(0, int((len(data) - 1) / 5)):

        name = data[i * 5 + 1]
        short_name = data[i * 5 + 2]
        pinyin = data[i * 5 + 3]
        pinyin_short = data[i * 5 + 4]

        stations.set(name, {
            "id": data[i * 5], 
            "name": name, 
            "tel": short_name,
            "full": pinyin,
            "short": pinyin_short
        }, 8035200)
        # 车站信息基本不会过期，设置一个季度更新一次

def getStations():
    print("Getting stations")
    s = req.get(STATION_NAMES_API).text[20:-2]
    parseStations(s)
    print("Finish getting stations")

def getTrainList():
    '''
        获取车次列表

        Warning: 耗时较长
    '''
    print("Getting train list")
    data = json.loads(req.get(TRAIN_LIST_API).text[16:])
    ks = list(data.keys())
    ks.sort(reverse=True)
    # 获取最后一天日期

    for i in data[ks[0]]:
        for j in data[ks[0]][i]:
            ma = STATION_TRAIN_CODE_RE.match(j["station_train_code"])
            res = ma.groups()
            trains.set(res[0], {
                "train": res[0],
                "from": res[1],
                "to": res[2],
                "train_no": j["train_no"]
            }, 604800) # 设置七天后过期
    print("Finish getting train list")
            

def getTrain(train):
    '''
        获取车次
    '''

    if not train in train_names.trains:
        return None

    t = trains.get(train)
    if not t:
        getTrainList()

    t = trains.get(train)
    return t

def getScheduler(train, date = None, froms = None , tos = None):
    '''
        获取列车时刻表

        Returns: (code, data)
        code:  0 -> Success
              -1 -> 未获取到数据
              -2 -> 未获取到车次编号
              -3 -> 站点不存在

    '''
    tn = getTrain(train)

    # 如果有缓存直接返回
    cached = schedulers.get(tn)
    if cached:
        return cached

    if not tn:
        # 未获取到车次编号
        return -2, None
    
    if not date:
        date = datetime.datetime.now().strftime("%Y-%m-%d")

    if not froms:
        froms = tn["from"]
    
    if not tos:
        tos = tn["to"]

    f = stations.get(froms)
    if not f:
        # 未获取到车站信息，重新获取
        getStations()
        f = stations.get(froms)
        if not f:
            # 还是没有则返回
            return -3, None

    froms = f["tel"]

    tos = stations.get(tos)

    if not tos:
        # 如果没有到达车站信息，返回
        return -3, None

    tos = tos["tel"]
    try:
        rep = req.get(GET_SCHEDULER_API, params = {
            "train_no": tn["train_no"],
            "from_station_telecode": froms,
            "to_station_telecode": tos,
            "depart_date": date
        })
        
        rep = rep.json()

        d = {
            "data": {}
        }

        count = 1
        leng = len(rep["data"]["data"])
        for i in rep["data"]["data"]:
            if count == 1:
                # 始发站
                d["start_time"] = i["start_time"]
                d["from"] = i["start_station_name"]
                d["to"] = i["end_station_name"]
                d["train_class"] = i["train_class_name"]
            elif count == leng:
                # 终到站
                d["arrive_time"] = i["arrive_time"]

            d["data"][i["station_no"]] = {
                "arrive_time": i["arrive_time"],
                "start_time": i["start_time"],
                "stopover_time": i["stopover_time"],
                "station_name": i["station_name"],
                "is_enabled": i["isEnabled"]
            }

            count = count + 1

        schedulers.set(tn["train_no"], d, expire=86400)
        return 0, d


    except:
        return -1, None
