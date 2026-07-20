from serpapi import GoogleSearch

params = {
  "engine": "google",
  "q": "Coffee",
  "api_key": "c7e40acb57c13a31d8958c06a6514f0034d61ff1e42d67cbc825503fc988ee68"
}

search = GoogleSearch(params)
results = search.get_dict()
organic_results = results["organic_results"]
print(organic_results)