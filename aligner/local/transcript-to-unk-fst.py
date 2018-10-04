#! /usr/bin/env python

import sys
import argparse
from math import log

parser = argparse.ArgumentParser("Converts transcripts to FSTs, with optional <unk> words between actual words")
parser.add_argument('--unk', default="<unk>")
parser.add_argument('words_txt')

args = parser.parse_args()

words = {}
for l in open(args.words_txt):
  ss = l.split()
  words[ss[0]] = int(ss[1])


for l in sys.stdin:
  ss = l.split()
  print(ss[0])
  for i, word in enumerate(ss[1:]):
    print("%d %d %d %d" % (i*2, i*2+1, words[word], words[word]))
    print("%d %d %d %d %f" % (i*2+1, i*2+2, words["<eps>"], words["<eps>"], -log(0.99)))
    print("%d %d %d %d %f" % (i*2+1, i*2+2, words["<unk>"], words["<unk>"], -log(0.01)))
  print(i*2+2)
  
