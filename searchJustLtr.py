from features import formatFeature
import json

baseQuery = {
  "query": {
        "ltr": {
                "model": {
                    "stored": "" # Model name
                },
                "features": []# features]
        }
  }
}

def featureQueries(keywords, model):
    try:
        ftrId = 1
        while True:
            parsedJson = formatFeature(ftrId, "{{query_string}}")
            baseQuery['query']['ltr']['features'].append(parsedJson['query'])
            ftrId += 1
    except IOError:
        pass
    baseQuery['query']['ltr']['model']['stored'] = model
    print("%s" % json.dumps(baseQuery))
    return baseQuery


if __name__ == "__main__":
    from sys import argv
    from elasticsearch import Elasticsearch
    esUrl="http://localhost:9200"
    model = "test_6"
    if len(argv) > 2:
        model = argv[2]
    es = Elasticsearch(timeout=1000)
    search = featureQueries(argv[1], model)
    es.put_template('o19s_blog_search', body=json.dumps(baseQuery['query']))
    results = es.search(index='o19s', doc_type='post', body=search)
    for result in results['hits']['hits']:
             print("%s, %s" % (result['_id'], result['_source']['title']))

