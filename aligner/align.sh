#!/bin/bash

set -e
set -o pipefail
set -u

cleanup=true
KALDI_ROOT=/home/tanel/tools/kaldi-trunk

stage=0


acmodel=tdnn_7d_online

export PATH=$PWD/utils/:$KALDI_ROOT/tools/openfst/bin:$PWD:$PATH
[ ! -f $KALDI_ROOT/tools/config/common_path.sh ] && echo >&2 "The standard file $KALDI_ROOT/tools/config/common_path.sh is not present -> Exit!" && exit 1
. $KALDI_ROOT/tools/config/common_path.sh


if [ ! -L steps ]; then
  ln -s ${KALDI_ROOT}/egs/wsj/s5/steps
fi

if [ ! -L utils ]; then
  ln -s ${KALDI_ROOT}/egs/wsj/s5/utils
fi


. utils/parse_options.sh

echo "$0 $@"



if [ $# != 3 ]; then
   echo "usage: steps/align.sh <wav> <txt> <praat_output>"
   exit 1;
fi

srcwav=$1
srctxt=$2
result=$3

echo "Preparing acoustic model"

if [ ! -d build/${acmodel} ]; then
  mkdir -p build/model
  cp -r model/${acmodel} build/model
  perl -i -npe 's#=.*'${acmodel}'/#=build/model/'${acmodel}/'#' build/model/${acmodel}/conf/*.conf
  if [ ! -e build/model/${acmodel}/cmvn_opts ]; then \
    echo "--norm-means=false --norm-vars=false" > build/model/${acmodel}/cmvn_opts;
  fi 
fi

echo "Preparing G2P translator"

if [ ! -d local/et-g2p/build ]; then
  (cd local/et-g2p; ant dist)
fi

uuid=`uuidgen`
dir=build/align/${uuid}

echo "Preparing data"

mkdir -p $dir/data
echo "dummy sox $srcwav -c 1 -2 -t wav - rate -v 16k |" > $dir/data/wav.scp

cat ${srctxt} | uconv -x any-nfc | perl -npe 's/[\r\n]/ /g; s/[,.!?:]//g;' | perl -npe 's/^/dummy /' > $dir/data/text
echo "dummy dummy" > $dir/data/spk2utt
echo "dummy dummy" > $dir/data/utt2spk

echo "Generating language model"

# Make lexicon
mkdir -p $dir/dict
cp -r model/dict/* $dir/dict
cat model/filler.dict | egrep -v "^<.?s>"   > $dir/dict/lexicon.txt
cat $dir/data/text | perl -npe 's/\S+ //; s/\s+/\n/g;' | grep -v "^\s*$" | sort | uniq | ./local/et-g2p/run.sh |  perl -npe 's/\(\d\)(\s)/\1/' | \
  perl -npe 's/\b(\w+) \1\b/\1\1 /g; s/(\s)jj\b/\1j/g; s/(\s)tttt\b/\1tt/g;' >> $dir/dict/lexicon.txt
  
#utils/prepare_lang.sh --phone-symbol-table build/model/${acmodel}/phones.txt --sil-prob 0.01 --unk-fst model/unk_fst.txt $dir/dict '<unk>' $dir/dict/tmp $dir/lang
utils/prepare_lang.sh --phone-symbol-table build/model/${acmodel}/phones.txt --sil-prob 0.01 $dir/dict '<unk>' $dir/dict/tmp $dir/lang

echo "Generating features"

# make mfcc
./steps/make_mfcc.sh --nj 1 --mfcc-config build/model/${acmodel}/conf/mfcc.conf \
  $dir/data
./steps/compute_cmvn_stats.sh $dir/data

echo "Generating i-vectors"

./steps/online/nnet2/extract_ivectors_online.sh --nj 1 \
  $dir/data build/model/${acmodel}/ivector_extractor $dir/ivectors

mkdir $dir/ali
cat $dir/data/text | local/transcript-to-unk-fst.py $dir/lang/words.txt | \
  fstcopy ark:- ark,scp:$dir/ali/graphs.ark,$dir/ali/graphs.scp


# align, produce lattices
./steps/nnet3/align_lats.sh --nj 1 --online-ivector-dir $dir/ivectors \
  --scale-opts '--transition-scale=1.0 --self-loop-scale=1.0' \
  --acoustic_scale 1.0 \
  --graphs-scp $dir/ali/graphs.scp \
  $dir/data $dir/lang build/model/${acmodel} $dir/ali

lattice-1best ark:"gunzip -c $dir/ali/lat.1.gz |" ark:- | \
  lattice-align-words $dir/lang/phones/word_boundary.int build/model/${acmodel}/final.mdl ark:- ark:$dir/ali/lat.ark

frame_shift=0.0$(cat build/model/tdnn_7d_online/frame_subsampling_factor)

#make word CTM
nbest-to-ctm --print-silence=true --frame-shift=${frame_shift} ark:$dir/ali/lat.ark - | \
  ./utils/int2sym.pl -f 5 $dir/lang/words.txt | perl -npe 's/<eps>/<sil>/g' > $dir/ali/words.ctm
  
#make phone CTM
lattice-to-phone-lattice build/model/${acmodel}/final.mdl ark:$dir/ali/lat.ark ark:- | \
  nbest-to-ctm --print-silence=true --frame-shift=${frame_shift} ark:- - | \
  ./utils/int2sym.pl -f 5 <(perl -npe 's/_[BIES]//; s/ou/õ/g; s/ae/ä/g; s/oe/ö/g; s/ue/ü/g;' $dir/lang/phones.txt ) > $dir/ali/phones.ctm

python3 local/make_textgrid.py $dir/ali/words.ctm $dir/ali/phones.ctm $dir/ali/result.TextGrid

cp $dir/ali/result.TextGrid $result

if $cleanup; then
  rm -rf $dir
fi

