from esUrlParse import parseUrl
from judgments import Judgment
from elasticsearch import Elasticsearch

def getPotentialResults(esUrl, keywords, boostwords):
    (esUrl, index, searchType) = parseUrl(esUrl)
    es = Elasticsearch(esUrl)
    baseQuery = {
        "query": {
            "bool": {
                "filter": [
                    {
                        "bool": {"should": [
                            {"range": {
                                "post_date": {
                                    "gte": "now-2y/d"
                                }
                            }}]}

                    }
                ],
                "should": [
                    {"match": {
                        "title": ""
                    }},
                    {"match": {
                        "_all": ""
                    }}
                ]
            }
        },
        "size": 2
    }

    baseQuery["query"]["bool"]["should"][0]["match"]["title"] = keywords
    baseQuery["query"]["bool"]["should"][1]["match"]["_all"] = boostwords
    results = es.search(index=index, doc_type=searchType, body=baseQuery)
    return results['hits']['hits']


def gradeResults(results, keywords, qid):
    titleField = 'title'
    overviewField = 'excerpt'
    ratings = []
    print("Rating %s results" % len(results))
    for result in results:
        grade = None
        if 'fields' not in result:
            if '_source' in result:
                result['fields'] = result['_source']
        if 'fields' in result:
            if result['fields']['url'].startswith('http://opensourceconnections.com/blog/'):
                print("")
                print("")
                print("## %s " % result['fields'][titleField])
                print("")
                print("   %s " % result['fields'][overviewField])
                print("   %s " % result['fields']['post_date'])
                print("   %s " % result['fields']['categories'])
                while grade not in ["0", "1", "2", "3", "4"]:
                    grade = input("Rate this shit (0-4) ")
                judgment = Judgment(int(grade), qid=qid, keywords=keywords, docId=result['_id'])
                ratings.append(judgment)

    for rating in ratings:
        print(rating.toRanklibFormat())




if __name__ == "__main__":
    from sys import argv

    keywords = "-"
    qid = 1
    while len(keywords) > 0:
        keywords = input("Enter the Keywords ")
        boostwords = input("What words can help me find that? ")

        results = getPotentialResults(argv[1], keywords, boostwords)
        gradeResults(results, keywords, qid)

        qid += 1


