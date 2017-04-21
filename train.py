import os
from features import kwDocFeatures, buildFeaturesJudgmentsFile


def trainModel(trainingData, testData, modelOutput, whichModel=6):
    # java -jar RankLib-2.6.jar  -metric2t ERR@3 -ranker 6 -kcv -train osc_judgments_wfeatures_train.txt -test osc_judgments_wfeatures_test.txt -save model.txt
    cmd = "java -jar RankLib.jar -metric2t NDCG@10 -tree 20 -leaf 10 -ranker %s -train %s -test %s -save %s " % (whichModel, trainingData, testData, modelOutput)
    print("*********************************************************************")
    print("*********************************************************************")
    print("Running %s" % cmd)
    os.system(cmd)
    pass


def saveModel(es, scriptName, modelFname):
    """ Save the ranklib model in Elasticsearch """
    with open(modelFname) as modelFile:
        modelContent = modelFile.read()
        es.put_script(lang='ranklib', id=scriptName, body={"script": modelContent})


def saveJustLtrSearch(es, model, modelType, baseName='o19s_blog_search'):
    from searchJustLtr import justLtrTemplate
    templAsStr = justLtrTemplate(model)
    es.put_template(baseName + "_%s" % modelType, body=templAsStr)


def partitionJudgments(judgments, testProportion=0.1):
    testJudgments = {}
    trainJudgments = {}
    from random import random
    for qid, judgment in judgments.items():
        draw = random()
        if draw <= testProportion:
            testJudgments[qid] = judgment
        else:
            trainJudgments[qid] = judgment

    return (trainJudgments, testJudgments)




if __name__ == "__main__":
    from elasticsearch import Elasticsearch
    from judgments import judgmentsFromFile, judgmentsByQid, duplicateJudgmentsByWeight
    esUrl="http://ec2-54-234-184-186.compute-1.amazonaws.com:9616/supersecretsquirrel/"
    es = Elasticsearch(esUrl, timeout=1000)
    # Parse a judgments
    judgments = judgmentsByQid(judgmentsFromFile(filename='osc_judgments.txt'))
    judgments = duplicateJudgmentsByWeight(judgments)
    trainJudgments, testJudgments = partitionJudgments(judgments, testProportion=0.00)
    # Use proposed Elasticsearch queries (1.json.jinja ... N.json.jinja) to generate a training set
    # output as "osc_judgments_wfeatures.txt"
    kwDocFeatures(es, index='o19s', searchType='post', judgements=judgments)
    numFeatures = len(judgments[1][0].features)
    print("Training on %s features" % numFeatures)
    buildFeaturesJudgmentsFile(trainJudgments, filename='osc_judgments_wfeatures_train.txt')
    buildFeaturesJudgmentsFile(testJudgments, filename='osc_judgments_wfeatures_test.txt')
    # Train each ranklib model type
    for modelType in [0,6,9]:
        # 0, MART
        # 1, RankNet
        # 2, RankBoost
        # 3, AdaRank
        # 4, coord Ascent
        # 6, LambdaMART
        # 7, ListNET
        # 8, Random Forests
        # 9, Linear Regression
        print("*** Training %s " % modelType)
        trainModel(trainingData='osc_judgments_wfeatures_train.txt', testData='osc_judgments_wfeatures_test.txt', modelOutput='model.txt', whichModel=modelType)
        model = "test_%s" % modelType
        saveModel(es, model, modelFname='model.txt')
        saveJustLtrSearch(es, model=model, modelType=modelType)

