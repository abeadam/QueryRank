from __future__ import division
import sys
import re
import os.path
from math import log
import math
import pickle
import operator
import pdb
from collections import Counter

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

def get_average(features):
  totals = Counter()
  docCount = 0.0
  for query in features:
    for doc in features[query]:
      #url
      url = ''
      for i in doc:
        if i.isalnum():
          url = url+i
        else:
        # two white spaces will be removed by split
          url = url + ' '
      url = url.split()
      # title
      if(features[query][doc].has_key('title')):
        title = features[query][doc]['title']
      else:
        title = ""
      title = title.split()
      # body
      body_count = 0
      if(features[query][doc].has_key('body_hits')):
        body = features[query][doc]['body_hits']
        for b in body:
          body_count += len(body[b])
      else:
        body = {}
      # header
      headerList = []
      if(features[query][doc].has_key('header')):
        for h in features[query][doc]:
          headerList.append(h)
      else:
        header = ''
      header = ' '.join(headerList)
      header = header.split()
      #anchor
      anchor_count = 0
      if(features[query][doc].has_key('anchors')):
        anchor = features[query][doc]['anchors']
        for a in anchor:
          anchor_count += anchor[a]
      else:
        anchor = {}
      totals['url'] = totals['url'] + len(url)
      totals['title'] = totals['title']+len(title)
      totals['header'] = totals['header']+len(header)
      totals['body'] = totals['body']+body_count
      totals['anchor'] = totals['anchor'] + anchor_count
      docCount += 1
  totals['url'] = totals['url']/docCount
  totals['title'] = totals['title']/docCount
  totals['header'] = totals['header']/docCount
  totals['body'] = totals['body']/docCount
  totals['anchor'] = totals['anchor']/docCount
  return totals

# doc -> term -> field -> doc frequency
def get_ftf_dft(query,features,averages,Bu,Bt,Bb,Bh,Ba):
  docs = {}
  queryList = query.replace('\n','').split()
  for doc in features[query]:
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
      # count the term in those fields
      for term in queryList:
        url_vector.append(url.count(term))
        title_vector.append(title.count(term))
        header_vector.append(header.count(term))
        if(body.has_key(term)):
          body_vector.append(len(body[term]))
        else:
          body_vector.append(0)
        anchor_count = 0
        for a in anchor:
          link = a.split()
          anchor_count = anchor_count+anchor[a]*link.count(term)
        anchor_vector.append(anchor_count)
      # apply sublinear scaling and normalization
      temp_url = []
      temp_title = []
      temp_header = []
      temp_body = []
      temp_anchor = []
      for i in range(0,len(queryList)):
        if(url_vector[i] > 0):
          len_df = len(url)
          avg_len = averages['url']
          fdf = url_vector[i] / (1 + Bu*((len_df/avg_len)-1))
          temp_url.append(fdf)
        else:
          temp_url.append(0)
        if(title_vector[i] > 0):
          len_df = len(title)
          avg_len = averages['title']
          fdf = title_vector[i] / (1 + Bu*((len_df/avg_len)-1))
          temp_title.append(fdf)
        else:
          temp_title.append(0)
        if(header_vector[i]>0):
          len_df = len(header)
          avg_len = averages['header']
          fdf = header_vector[i] / (1 + Bu*((len_df/avg_len)-1))
          temp_header.append(fdf)
        else:
          temp_header.append(0)
        if(body_vector[i] > 0):
          len_df = len(body)
          avg_len = averages['body']
          fdf = body_vector[i] / (1 + Bu*((len_df/avg_len)-1))
          temp_body.append(fdf)
        else:
          temp_body.append(0)
        if(anchor_vector[i]>0):
          len_df = len(anchor)
          avg_len = averages['anchor']
          fdf = anchor_vector[i] / (1 + Bu*((len_df/avg_len)-1))
          temp_anchor.append(fdf)
        else:
          temp_anchor.append(0)
      info['url'] = temp_url
      info['title'] = temp_title
      info['header'] = temp_header
      info['body'] = temp_body
      info['anchor'] = temp_anchor
      docs[doc] = info
  return docs

# this is going to return the overall weight for the fields
def get_overall_weight(ftf,Wu,Wt,Wb,Wh,Wa,queryLength):
    docs = {}
    for doc in ftf:
        termList =[]
        for i in range(0,queryLength):
          url = ftf[doc]['url'][i] * Wu
          title = ftf[doc]['title'][i] * Wt
          body = ftf[doc]['body'][i] * Wb
          header = ftf[doc]['header'][i] * Wh
          anchor = ftf[doc]['anchor'][i] * Wa
          termList.append(url+title+body+header+anchor)
        docs[doc] = termList
    return docs

#this is going to apply one of the 3 functions that we have
def apply_func(lamp,f,pagerank):
    if(f==1):
      return log(lamp+pagerank)
    elif(f==2):
      return pagerank/(lamp+pagerank)
    elif(f==3):
      return 1/(lamp+(math.exp(lamp+pagerank)))


# this will get the final overall score for the document
# note the F parameter controlls which function is choosen
def get_overall_score(w_dt,K,lam,lamp,f,idf,query,features):
    docs = {}
    queryList = query.replace('\n','').split()
    for doc in w_dt:
        sum = 0
        for i in range(0,len(queryList)):
            term = w_dt[doc][i]
            word = queryList[i]
            sum = sum + (term/(term+K))*idf[word]
        pagerank = features[query][doc]['pagerank']
        sum = sum+lam*apply_func(lamp,f,pagerank)
        docs[doc] = sum
    return docs


#inparams
#  queries: map containing list of results for each query
#  features: map containing features for each query,url pair
#return value
#  rankedQueries: map containing ranked results for each query
def baseline(queries, features,Bu,Bt,Bb,Bh,Ba,Wu,Wt,Wb,Wh,Wa,K,lam,lamp,f):
    # get the averages
    averages = get_average(features)
    rankedQueries = {}
    idf = get_idf_count()
    for query in queries.keys():

      #This will return ftf_dft
      ftf = get_ftf_dft(query,features,averages,Bu,Bt,Bb,Bh,Ba)
      # this will get W_d,t
      W_dt = get_overall_weight(ftf,Wu,Wt,Wb,Wh,Wa, len(query.replace('\n','').split()))
      # this will give us the final score
      ranks = get_overall_score(W_dt,K,lam,lamp,f,idf,query,features)

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
def main(featureFile,Bu,Bt,Bb,Bh,Ba,Wu,Wt,Wb,Wh,Wa,K,lam,lamp,f):
    #output file name
    outputFile = "ranked.txt" #Please don't change this!

    #populate map with features from file
    (queries, features) = extractFeatures(featureFile)

    #calling baseline ranking system, replace with yours
    rankedQueries = baseline(queries, features,Bu,Bt,Bb,Bh,Ba,Wu,Wt,Wb,Wh,Wa,K,lam,lamp,f)

    #print ranked results to file
    printRankedResults(rankedQueries)

if __name__=='__main__':
    if (len(sys.argv) < 2):
      print "Insufficient number of arguments"
    if (len(sys.argv) > 5):
      Bu = sys.argv[2]
      Bt = sys.argv[3]
      Bb = sys.argv[4]
      Bh = sys.argv[5]
      Ba = sys.argv[6]
      Wu = sys.argv[7]
      Wt = sys.argv[8]
      Wb = sys.argv[9]
      Wh = sys.argv[10]
      Wa = sys.argv[11]
      K = sys.argv[12]
      lam = sys.argv[13]
      lamp = sys.argv[14]
      f = sys.argv[15]
    else:
      Wu = 1
      Wt = 4
      Wb = 1
      Wh = 3
      Wa = 2
      Bu = 0.75
      Bt = 0.75
      Bb = 0.75
      Bh = 0.75
      Ba = 0.75
      K = 0.5
      lam = 0.5
      lamp = 1
      f = 1
    main(sys.argv[1],Bu,Bt,Bb,Bh,Ba,Wu,Wt,Wb,Wh,Wa,K,lam,lamp,f)
