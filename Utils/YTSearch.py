import re

import requests
import urllib.parse
import json

from . import Proxy

BASE_URL = "https://youtube.com"

class YoutubeSearch:
    def __init__(self, search_terms: str, max_results=None, proxy=False):
        self.search_terms = "music allintitle:" + search_terms
        self.max_results = max_results
        self.use_proxy = proxy
        self.videos = self._search()

    def _search(self):
        self.videos = ""
        encoded_search = urllib.parse.quote_plus(self.search_terms)
        url = f"{BASE_URL}/results?search_query={encoded_search}"
        
        if self.use_proxy == True:
            proxy = Proxy.get_random_proxy()
            print("Searching for youtube videos... with proxy:", proxy)
            response = requests.get(url, proxies=proxy).text
        else:
            print("Searching for youtube videos...")
            response = requests.get(url).text
        
        while "ytInitialData" not in response:
            response = requests.get(url).text
        results = self._parse_html(response)
        if self.max_results is not None and len(results) > self.max_results:
            return results[: self.max_results]
        return results

    def _parse_html(self, response):
        results = []
        start = (
            response.index("ytInitialData")
            + len("ytInitialData")
            + 3
        )
        end = response.index("};", start) + 1
        json_str = response[start:end]
        data = json.loads(json_str)

        for contents in data["contents"]["twoColumnSearchResultsRenderer"]["primaryContents"]["sectionListRenderer"]["contents"]:
            for video in contents["itemSectionRenderer"]["contents"]:
                res = {}
                if "videoRenderer" in video.keys():
                    video_data = video.get("videoRenderer", {})
                    res["id"] = video_data.get("videoId", None)
                    res["thumbnails"] = [thumb.get("url", None) for thumb in video_data.get("thumbnail", {}).get("thumbnails", [{}]) ]
                    res["title"] = video_data.get("title", {}).get("runs", [[{}]])[0].get("text", None)
                    res["long_desc"] = video_data.get("descriptionSnippet", {}).get("runs", [{}])[0].get("text", None)
                    res["author"] = video_data.get("longBylineText", {}).get("runs", [[{}]])[0].get("text", None)
                    res["channel"] = video_data.get("longBylineText", {}).get("runs", [[{}]])[0].get("text", None)
                    res["duration"] = video_data.get("lengthText", {}).get("simpleText", 0)
                    
                    views_string : str = video_data.get("viewCountText", {}).get("simpleText", 0)
                    if not re.findall(r'\d+', views_string):
                        continue
                    else:
                        res["views"] = int(re.findall(r'\d+', str(views_string).replace(".",""))[0])
                    
                    res["publish_time"] = video_data.get("publishedTimeText", {}).get("simpleText", 0)
                    res["url_suffix"] = video_data.get("navigationEndpoint", {}).get("commandMetadata", {}).get("webCommandMetadata", {}).get("url", None)
                    
                    results.append(res)

            if results:
                return results
        return results

    def get_results(self):
        for index, result in enumerate(self.videos):
            duration = result['duration']
            duration_in_seconds = duration.split(":")
            duration_in_seconds = (int(duration_in_seconds[0]) * 60) + int(duration_in_seconds[1])
            
            self.videos[index]['duration_in_seconds'] = duration_in_seconds
        
        return self.videos

# def test_search():
#     test_string = "Captain Qubz - High Dosage"
#     search = YoutubeSearch(test_string)
    
#     sorted_search = sorted(search.get_results(), key=lambda x: x['views'], reverse=True)

#     for result in sorted_search:
#         print(result["title"], " | ", result["author"], " | ", result["views"], " | ", result["duration"])

# test_search()