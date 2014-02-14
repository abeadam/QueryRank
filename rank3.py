from __future__ import division
import sys
import re
import os.path
from math import log
import pickle
import operator
import pdb
from collections import Counter
import numpy

#inparams
#  featureFile: input file containing queries and url features
#return value
#  queries: map containing list of results for each query
#  features: map containing features for each (query, url, <feature>) pair
def extractFeatures(featureFile):
    f = open(featureFile, 'r')
    queries = {}
    features = {}

    for line in f:
      key = line.split(':', 1)[0].strip()
      value = line.split(':', 1)[-1].strip()
      if(key == 'query'):
        query = value
        queries[query] = []
        features[query] = {}
      elif(key == 'url'):
        url = value
        queries[query].append(url)
        features[query][url] = {}
      elif(key == 'title'):
        features[query][url][key] = value
      elif(key == 'header'):
        curHeader = features[query][url].setdefault(key, [])
        curHeader.append(value)
        features[query][url][key] = curHeader
      elif(key == 'body_hits'):
        if key not in features[query][url]:
          features[query][url][key] = {}
        temp = value.split(' ', 1)
        features[query][url][key][temp[0].strip()] \
                    = [int(i) for i in temp[1].strip().split()]
      elif(key == 'body_length' or key == 'pagerank'):
        features[query][url][key] = int(value)
      elif(key == 'anchor_text'):
        anchor_text = value
        if 'anchors' not in features[query][url]:
          features[query][url]['anchors'] = {}
      elif(key == 'stanford_anchor_count'):
        features[query][url]['anchors'][anchor_text] = int(value)

    f.close()
    return (queries, features)

# this is going to return the scaled term frequecy for , url, title, body, header and anchors felds,
def sublinear_term_frequency(query,features):
  docs = {}
  queryList = query.split()
  for doc in features[query] :
    normalization_factor = features[query][doc]['body_length'] + 500
    info = {}
    #url
    url = ''
    for i in doc:
      if i.isalnum():
        url = url+i
      else:
      # two white spaces will be removed by split
        url = url + ' '
    url = url.split()
    url_vector = []
    # title
    if(features[query][doc].has_key('title')):
      title = features[query][doc]['title']
    else:
      title = ""
    title = title.split()
    title_vector = []
    # body
    if(features[query][doc].has_key('body_hits')):
      body = features[query][doc]['body_hits']
    else:
      body = {}
    body_vector = []
    # header
    if(features[query][doc].has_key('header')):
      header = features[query][doc]['header']
    else:
      header = ''
    header = ' '.join(header)
    header = header.split()
    header_vector = []
    #anchor
    if(features[query][doc].has_key('anchors')):
      anchor = features[query][doc]['anchors']
    else:
      anchor = {}
    anchor_vector = []

    for q in queryList:
      url_vector.append(url.count(q))
      title_vector.append(title.count(q))
      header_vector.append(header.count(q))
      if(body.has_key(q)):
        body_vector.append(len(body[q]))
      else:
        body_vector.append(0)
      anchor_count = 0
      for a in anchor:
        link = a.split()
        if(link.count(q) > 0):
          anchor_count = anchor_count+anchor[a]
      anchor_vector.append(anchor_count)
    # apply sublinear scaling and normalization
    temp_url = []
    temp_title = []
    temp_header = []
    temp_body = []
    temp_anchor = []
    for i in range(0,len(queryList)):
      if(url_vector[i] > 0):
        temp_url.append((1+log(url_vector[i]))/normalization_factor)
      else:
        temp_url.append(0)
      if(title_vector[i] > 0):
        temp_title.append((1+log(title_vector[i]))/normalization_factor)
      else:
        temp_title.append(0)
      if(header_vector[i]>0):
        temp_header.append((1+log(header_vector[i]))/normalization_factor)
      else:
        temp_header.append(0)
      if(body_vector[i] > 0):
        temp_body.append((1+log(body_vector[i]))/normalization_factor)
      else:
        temp_body.append(0)
      if(anchor_vector[i]>0):
        temp_anchor.append((1+log(anchor_vector[i]))/normalization_factor)
      else:
        temp_anchor.append(0)
    info['url'] = temp_url
    info['title'] = temp_title
    info['header'] = temp_header
    info['body'] = temp_body
    info['anchor'] = temp_anchor
    docs[doc] = info
  return docs

# this is going to return the idf, it will attempt to read data from PA1 if  idfInfo is not present
def get_idf_count():
  if(os.path.exists('idfInfo')):
    file = open('idfInfo','rb')
    idf = pickle.load(file)
    file.close()
    return idf
  location_of_words = 'AllQueryTerms'
  location_of_corpus = '/afs/ir.stanford.edu/class/cs276/2013/PA1/data'
      # checking to make sure the files we need exist
  if(os.path.isfile(location_of_words) == False):
    print >> sys.stderr , 'Couldn\'t find AllQueryTerms in same location as rank1.py'
  if(os.path.exists(location_of_corpus) == False):
    print >> sys.stderr , 'Couldn\'t find corpus at /afs/ir.stanford.edu/class/cs276/2013/PA1/data'

  # open query words file and fill a list with them
  file = open(location_of_words,'r')
  query_words = ' '.join(file.readlines()).replace('\n','').split()
  file.close()
  df = Counter()
  N = 0
  for dir in sorted(os.listdir(location_of_corpus)):
    dir_name = os.path.join(location_of_corpus, dir)
    print >> sys.stderr , dir_name
    for f in sorted(os.listdir(dir_name)):
      N += 1.0
      file_id = os.path.join(dir_name, f)
      corpus_file = open(file_id,'r')
      corpus_words = ' '.join(corpus_file.readlines()).replace('\n','').split()
      for word in query_words:
        if(corpus_words.count(word)>0):
          df[word] = df[word]+1
      corpus_file.close()
  idf = {}
  for w in query_words:
  # here we are smoothing when we get the idf
    idf[w]= log((N+1)/(df[i]+1))
  file = open('idfInfo','wb')
  pickle.dump(idf,file)
  file.close()

def query_normalized(query):
  idf = get_idf_count()
  query_words = query.replace('\n','').split()
  words = []
  for w in query_words:
    words.append(idf[w])
  return words

def get_parts_of_list(big,s):
    start = 0
    toReturn = []
    while(start+s <= len(big)):
      toReturn.append(big[start:s+start])
      start += 1
    return toReturn


def bigList_contains_small(big,small):
    for s in small:
        if big.count(s) < 1:
           return False
    return True

def contains(big, small):
    if (len(small) > len(big)):
       return False
    smallest = len(small)
    maxl = len(big)
    while(smallest <= maxl):
      possible_breaks = list(get_parts_of_list(big, smallest))
      for b in possible_breaks:
          if bigList_contains_small(b,small):
             return smallest-len(small)
      smallest +=1
    return False

def get_body_factor(queryList,body,bodyLength):
    newbody = {}
    queryList = (set(queryList))
    for q in queryList:
        if body.has_key(q) == False or  (body.has_key(q) and len(body[q])>0):
           return False
        else:
           newbody[q] = body[q]
    body = newbody

    #current map
    current = {}
    for q in queryList:
        current[q] = body[q][0]
        body[q].remove(body[q][0])
    maxNum = max(current.iteritems(), key=operator.itemgetter(1))[0]
    minNum = min(current.iteritems(), key=operator.itemgetter(1))[0]
    smallest = current[maxNum] - current[minNum]
    go = True
    while go:
      temp = {}
      go = False
      for q in body:
        if(len(body[q]) > 0):
          go = True
          temp[q] = body[q][0]
      if (go):
        minNum = min(current.iteritems(), key=operator.itemgetter(1))[0]
        if(len(body[minNum])==0):
          return smallest
        current[minNum] = body[minNum][0]
        body[minNum].remove(body[minNum][0])
        maxNum = max(current.iteritems(), key=operator.itemgetter(1))[0]
        smallest = current[maxNum] - current[minNum]
      else:
        return smallest

# this is going to return a dictionry that has the information that we need
def window_size_measurements(query,features,doc,B,u,t,b,h,a):
    queryList = query.replace('\n','').split()
    #url
    url = ''
    for i in doc:
      if i.isalnum():
        url = url+i
      else:
      # two white spaces will be removed by split
        url = url + ' '
    url = url.split()
    url_factor = contains(url,queryList)
    # title
    if(features[query][doc].has_key('title')):
      title = features[query][doc]['title']
    else:
      title = ""
    title = title.split()
    if(len(title) >0):
      title_factor = contains(title, queryList)
    else:
      title_factor = False
    # body
    if(features[query][doc].has_key('body_hits')):
      body = features[query][doc]['body_hits']
    else:
      body = {}
    body_factor = get_body_factor(queryList, body , features[query][doc]['body_length'])
    # header
    headerList = []
    if(features[query][doc].has_key('header')):
      for hv in features[query][doc]:
        headerList.append(hv)
    else:
      header = ''
    header = ' '.join(headerList)
    header = header.split()
    if(len(header) > 0):
      header_factor = contains(headerList,query)
    else:
      header_factor = False
    #anchor
    anchorList = []
    if(features[query][doc].has_key('anchors')):
      for av in features[query][doc]['anchors']:
        anchorList.append(av)
    else:
      anchor = {}
    anchor = ' '.join(anchorList)
    anchor =  anchor.split()
    if(len(anchor) > 0):
      anchor_factor = contains(anchor,queryList)
    else:
      anchor_factor = False
    total = 0
    if(url_factor):
      total += (B*(1/(1+url_factor))*u)/5
    if(title_factor):
      total += (B*(1/(1+title_factor))*t)/5
    if(body_factor):
      total += (B*(1/(1+body_factor))*b)/5
    if(header_factor):
      total += (B*(1/(1+header_factor))*h)/5
    if(anchor_factor):
      total += (B*(1/(1+anchor_factor))*a)/5
    return total
#inparams
#  queries: map containing list of results for each query
#  features: map containing features for each query,url pair
#return value
#  rankedQueries: map containing ranked results for each query
def baseline(queries, features,uv,tv,bv,hv,av,B):
    #constants for weights
    rankedQueries = {}
    get_idf_count()
    for query in queries.keys():
      results = queries[query]
      # first term frequency scaled and normalized
      term_frequency = sublinear_term_frequency(query,features)
      # second querREWWcument frequency and normalization
      qv = query_normalized(query)

      #add the count of the terms
      total_term_frequency = {}
      for doc in features[query]:
        info = term_frequency[doc]
        url =  [x * int(uv) for x in info['url']]
        title =  [x * int(tv) for x in info['title']]
        body = [x * int(bv) for x in info['body']]
        header = [x * int(hv) for x in info['header']]
        anchor = [x * int(av) for x in info['anchor']]
        weighted = [sum(s) for s in zip(url, title, body, header, anchor)]
        total_term_frequency[doc] = weighted
      #multiply term frequency by the weighted query
      ranks = {}
      for doc in features[query]:
        windowNum = window_size_measurements(query,features,doc,B,uv,tv,bv,hv,av)
        ranks[doc] = numpy.dot(total_term_frequency[doc],qv)
        ranks[doc] + windowNum
      ranks = sorted(ranks.iteritems(), key=operator.itemgetter(1),reverse = True)
      rankedQueries[query] = ranks

    return rankedQueries


#inparams
#  queries: contains ranked list of results for each query
#  outputFile: output file name
def printRankedResults(queries):
    for query in queries:
      print("query: " + query)
      for res in queries[query]:
	print("  url: " + res[0])

#inparams
#  featureFile: file containing query and url features
def main(featureFile,u,t,b,h,a,B):
    #output file name
    outputFile = "ranked.txt" #Please don't change this!

    #populate map with features from file
    (queries, features) = extractFeatures(featureFile)

    #calling baseline ranking system, replace with yours
    rankedQueries = baseline(queries, features,u,t,b,h,a,B)

    #print ranked results to file
    printRankedResults(rankedQueries)

if __name__=='__main__':
    if (len(sys.argv) < 2):
      print "Insufficient number of arguments"
    if (len(sys.argv) > 5):
      u = sys.argv[2]
      t = sys.argv[3]
      b = sys.argv[4]
      h = sys.argv[5]
      a = sys.argv[6]
      B = sys.argv[7]
    else:
      u = 1
      t = 2
      b = 1
      h = 2
      a = 5
      B = 0
    main(sys.argv[1],u,t,b,h,a,B)
