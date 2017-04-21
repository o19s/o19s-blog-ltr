from features import kwDocFeatures, buildFeaturesJudgmentsFile
from judgments import duplicateJudgmentsByWeight


def trainModel(trainingData, testData, modelOutput, whichModel=6, features=[]):
    # java -jar RankLib-2.6.jar  -ranker 6 -kcv -train osc_judgments_wfeatures_train.txt -test osc_judgments_wfeatures_test.txt -save model.txt
    if len(features) == 0:
        return (0,0)
    with open("features.txt", "w+") as f:
        f.write("\n".join(features))
        f.close()
    cmd = "java -jar RankLib.jar -metric2t ERR@5 -tree 20 -leaf 10 -ranker %s -train %s -test %s -feature features.txt -save %s " \
            % (whichModel, trainingData, testData, modelOutput)
    print("*********************************************************************")
    print("*********************************************************************")
    print("Running %s" % cmd)
    import subprocess
    import re
    result = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT).decode("utf-8")
    print(result)
    m = re.search('ERR.*on training data:\s([0-9\.]+)', result)
    trainErr = float(m.group(1))
    m = re.search('ERR.*on test data:\s([0-9\.]+)', result)
    testErr = float(m.group(1))
    print("Test  ERR@3: %s" % testErr)
    print("Train ERR@3: %s" % trainErr)
    return (trainErr, testErr)



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


def everySubset(l):
    from itertools import combinations
    for i in range(len(l)):
        for c in combinations(l, i):
            yield c
    yield tuple(l)




if __name__ == "__main__":
    from elasticsearch import Elasticsearch
    from judgments import judgmentsFromFile, judgmentsByQid
    esUrl="http://localhost:9200"
    es = Elasticsearch(timeout=1000)
    # Parse a judgments
    judgments = judgmentsByQid(judgmentsFromFile(filename='osc_judgments.txt'))
    judgments = duplicateJudgmentsByWeight(judgments)
    kwDocFeatures(es, index='o19s', searchType='post', judgements=judgments)

    results = {}

    numTrials = 10
    for i in range(numTrials):
        trainJudgments, testJudgments = partitionJudgments(judgments, testProportion=0.2)
        # Use proposed Elasticsearch queries (1.json.jinja ... N.json.jinja) to generate a training set
        # output as "osc_judgments_wfeatures.txt"
        numFeatures = len(judgments[1][0].features)
        print("Training on %s features" % numFeatures)
        buildFeaturesJudgmentsFile(trainJudgments, filename='osc_judgments_wfeatures_train.txt')
        buildFeaturesJudgmentsFile(testJudgments, filename='osc_judgments_wfeatures_test.txt')


        availableFeatures = [str(i) for i in range(1,numFeatures+1)]
        # For every feature combination


        for currFeatures in everySubset(availableFeatures):
            # Train each ranklib model type
            for modelType in [6]:
                # 0, MART
                # 1, RankNet
                # 2, RankBoost
                # 3, AdaRank
                # 4, coord Ascent
                # 6, LambdaMART
                # 7, ListNET
                # 8, Random Forests
                # 9, Linear Regression
                (trainErr, testErr) = trainModel(trainingData='osc_judgments_wfeatures_train.txt', testData='osc_judgments_wfeatures_test.txt', modelOutput='model.txt', whichModel=modelType, features=currFeatures)
                print("*** Training %s w/ %s. TestERR %s TrainERR %s" % (modelType, currFeatures, testErr, trainErr))
                model = "test_%s" % modelType

                if currFeatures not in results:
                    results[currFeatures] = [testErr, trainErr]
                else:
                    results[currFeatures][0] += testErr
                    results[currFeatures][1] += trainErr
                print("*** ACCUMULA %s w/ %s. TestERR %s TrainERR %s" % (modelType, currFeatures, results[currFeatures][0], results[currFeatures][1]))

                #saveModel(es, model, modelFname='model.txt')
                #saveJustLtrSearch(es, model=model, modelType=modelType)

    testErrResults = sorted(results.items(), key=lambda x: (x[1][0] * 100 + x[1][1]), reverse=True)

    bestFeatures = {}

    print("Best Results %s")
    for result in testErrResults:
        features = result[0]
        testErr = result[1][0]
        trainErr = result[1][1]
        for feature in features:
            if feature not in bestFeatures:
                bestFeatures[feature] = testErr
            else:
                bestFeatures[feature] += testErr
        print("%s -> testERR %s trainERR %s" % (features, (testErr / numTrials), (trainErr / numTrials)))

    featureBySumErr = sorted(bestFeatures.items(), key=lambda x: (x[1]), reverse=True)
    for feature, totErr in featureBySumErr:
        print("%s -> %s" % (feature[0], totErr))
