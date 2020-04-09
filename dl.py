import requests
from bs4 import BeautifulSoup
import re
from pathlib import Path
import urllib.parse
import os
import fnmatch
from multiprocessing import Pool
import subprocess

headers = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:59.0) Gecko/20100101 Firefox/59.0'
}

proxies = {
    "http": "http://192.168.200.1:7890",
    "https": "http://192.168.200.1:7890",
}

jar = requests.cookies.RequestsCookieJar()
jar.set('bjxC', '1', domain='orgasmsoundlibrary.com', path='/')
# jar.set('_csrf', r'f8f6ac2af121c12d4d1f9b1754e7a41b50ac28933037ee853397abb16bd6e134a%3A2%3A%7Bi%3A0%3Bs%3A5%3A%22_csrf%22%3Bi%3A1%3Bs%3A32%3A%22Lov1PbV0L7xATUsP734gYy5-8lA-pe5i%22%3B%7D', domain='orgasmsoundlibrary.com', path='/')
# jar.set('gross_cookie', 'blech', domain='orgasmsoundlibrary.com', path='/elsewhere')

host = "https://orgasmsoundlibrary.com/"
basePath = Path("./data")
indexFilePath = basePath.joinpath("data").joinpath("bijoux.json")

# dlTimeout = (30, 30)

# proxies = {}

session = requests.session()
session.headers = headers
session.timeout = (30, 30)
session.proxies = proxies

session.cookies = jar

orgExamp = {
    "id": "1825",
    "tipo": "Circles",
    "id_color": "147",
    "id_preset": "147",
    "count_visit": "25669",
    "count_share": "72",
    "count_like": "100",
    "title": "LARITA",
    "audio": "upload/recoded/1825/9ZuVNADr2uw-ta2pCpiUzLk0WH3s9xeY.mp3",
    "duration": "45.73866666666667",
    "filetype": "mp3",
    "wave": "upload/recoded/1825/wave_id_1825.png",
    "wave_gris": "upload/recoded/1825/wave_id_1825_gris.png",
    "art": "upload/recoded/1825/art_id_1825.png",
    "thumb_art": "upload/recoded/1825/thumb_art_id_1825.png",
    "download": "upload/recoded/1825/libreriadeorgasmos_id_1825.jpg",
    "rrss_img": "upload/recoded/1825/libreriadeorgasmos_rrss_id_1825.jpg",
    "tags": [
        "Couple", "Liberating", "Penetration", "Neck", "Ears", "Hot", "Erotic",
        "Bed", "Ecstasy", "Heat", "Casual", "Enjoyment", "Passionate", "Loving",
        "Erotic"]
}


def getAudioFilePath(org):
    audioFilePath = basePath
    if org.get("audio"):
        audioFilePath = basePath.joinpath(org.get("audio"))
        return audioFilePath
    else:
        return None


def dl(org):
    audioFilePath = basePath
    if org.get("audio"):
        audioFilePath = basePath.joinpath(org.get("audio"))
    else:
        print(org)

    if audioFilePath.is_file():
        print("Skip {} for {} exists.".format("org", audioFilePath))
        return

    os.makedirs(os.path.dirname(audioFilePath), exist_ok=True)
    dlUrl = host + org.get("audio")
    ret = session.get(dlUrl)
    with open(audioFilePath, 'wb') as f:
        f.write(ret.content)
        print("{} {}".format(org.get("id"), audioFilePath))
    pass


def dlP(org):
    try:
        dl(org)
    except Exception:
        raise


def updateIndex():
    indexUrl = host + "data/bijoux.json"
    ret = session.get(indexUrl)
    with open(indexFilePath, 'wb+') as f:
        f.write(ret.content)
        print(indexFilePath)
    pass


def downloadAll(orgasmos):
    pool = Pool(5)
    print("Has {} orgasmos".format(len(orgasmos)))
    pool.map(dlP, orgasmos)
    pool.close()
    pool.join()


def norm(org):
    audioFilePath = basePath
    if org.get("audio"):
        audioFilePath = basePath.joinpath(org.get("audio"))
    else:
        print(org)

    if not audioFilePath.is_file():
        print("Skip {} for {} not exists.".format(org.get("id"), audioFilePath))
        return

    normedPath = basePath.joinpath("mixed/norm").joinpath(audioFilePath.stem + ".m4a")
    cmd = "ffmpeg.exe -y -i {} -af loudnorm -ac 1 {}".format(audioFilePath, normedPath)
    os.system(cmd)
    return


def ffmpegConcat(orgs):
    import ffmpeg
    import random
    import json
    from datetime import datetime
    max_nb_layers = 20
    hard_limit = 30000
    dur_limit = 600
    tags_not = {
        "Couple", "Electric", 'Threesome', 'Public transport', 'Male stranger'
    }
    tags_must = {"Alone"}
    tags_may = {"Powerful", "Finger"}

    contactList = []
    amixList = []
    length = 0

    selected = dict()
    selectedOrgs = []
    for _ in range(hard_limit):
        id = random.randint(0, len(orgs) - 1)
        # id = random.randint(0, 5)
        org = orgs[id]
        tags = set(org.get("tags"))
        if tags_not & tags:
            # print(tags_not & tags)
            continue
        if tags_must - tags:
            # print(tags_must - tags)
            continue
        if not tags_may & tags:
            # print(tags_may & tags)
            continue

        stream = selected.get(id, None)
        if not stream:
            stream = ffmpeg.input(str(getAudioFilePath(org)))
            stream = ffmpeg.filter(stream, 'loudnorm')
        
        streams = ffmpeg.filter_multi_output(stream, 'asplit')
        selected[id] = streams.stream(0)
        stream = streams.stream(1)
        contactList.append(stream)

        audioLength = float(org.get("duration", "30"))
        length += audioLength
        if length >= dur_limit:
            contactStream = ffmpeg.concat(*contactList, v=0, a=1)
            amixList.append(contactStream)
            contactList = []
            length = 0

        selectedOrgs.append(org)
        if len(amixList) >= max_nb_layers:
            break
    else:
        if contactList:
            contactStream = ffmpeg.concat(*contactList, v=0, a=1)
            amixList.append(contactStream)

    fullStream = ffmpeg.filter(
        amixList, 'amix', inputs=len(amixList), duration='longest'
    )
    fullStream = ffmpeg.filter(fullStream, 'atrim', duration=dur_limit)

    outputPath = basePath.joinpath("mixed").joinpath(
        "mix-{:d}.m4a".format(int(datetime.now().timestamp())))
    metadata = {
        'length': dur_limit,
        'nb': len(selectedOrgs),
        'nb_dist': len(selected),
        'mix_layers': len(amixList),
        'tags_not': list(tags_not),
        'tags_must': list(tags_must),
        'tags_may': list(tags_may),
        'tags': list(getTags(selectedOrgs))
    }
    metadataJson = json.dumps(metadata, ensure_ascii=False, sort_keys=False)
    outputParam = {
        'metadata': 'comment="{}"'.format(metadataJson),
        'acodec': 'aac'
    }

    fullStream = fullStream.output(str(outputPath), **outputParam)
    cmd = ffmpeg.compile(fullStream)
    print(cmd)
    ffmpeg.view(fullStream, filename=str(outputPath)+".png")
    ffmpeg.run(fullStream, overwrite_output=True)
    printTags(selectedOrgs)
    pass


def test(orgasmos):
    import ffmpeg
    from datetime import datetime
    stream = ffmpeg.input("data\\upload\\orgasmos\\1-x-ti\\pqaY1OJ9eWOzWgVZDn-L1TAnkcdnJrUR.mp3")
    stream = ffmpeg.filter(stream, 'loudnorm')
    concatList = []
    selected = {
        1: stream
    }
    for _ in range(5):
        id = 1
        stream = selected.get(id)
        streams = ffmpeg.filter_multi_output(stream, 'asplit')
        selected[id] = streams.stream(0)
        stream = streams.stream(1)
        concatList.append(stream)

    fullStream = ffmpeg.concat(*concatList, v=0, a=1)
    outputFilename = "mix-test-{:d}.m4a".format(int(datetime.now().timestamp()))
    outputPath = basePath.joinpath("mixed").joinpath(outputFilename)
    fullStream = fullStream.output(str(outputPath))
    cmd = ffmpeg.compile(fullStream)
    print(cmd)
    ffmpeg.view(fullStream, filename=str(outputPath)+".png")
    # ffmpeg.run(fullStream)
    pass


def getTags(orgasmos):
    tags = set()
    for org in orgasmos:
        tags.update(org.get("tags"))
    return tags


def printTags(orgasmos):
    print(getTags(orgasmos))


def main():
    import json
    index = {}
    try:
        with open(indexFilePath, 'r', encoding="UTF-8") as f:
            index = json.load(f)
    except Exception as e:
        return

    orgasmos = index.get("Orgasmos")
    # printTags(orgasmos)
    ffmpegConcat(orgasmos)
    # test(orgasmos)


if __name__ == "__main__":
    main()
