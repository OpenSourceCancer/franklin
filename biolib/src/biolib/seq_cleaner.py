'''
Functions to clean sequences.

All functions here have the same interface. You pass a SeqWithQuality to the
fucntion and it returns another SeqWithQuality.
Depending on the algorith used it mask or it trim the bad seq/quality section.

As bad we undertand low quality section, low complexity section, poliA section,
...
'''

# Copyright 2009 Jose Blanca, Peio Ziarsolo, COMAV-Univ. Politecnica Valencia
# This file is part of biolib.
# biolib is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

# biolib is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR  PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with biolib. If not, see <http://www.gnu.org/licenses/>.

import re
from biolib.biolib_cmd_utils import create_runner
from biolib.biolib_utils import parse_fasta, get_content_from_fasta
from biolib.seqs import  SeqWithQuality

def strip_seq_by_quality(seq, quality_treshold, min_quality_bases=None,
                       min_seq_length=None, quality_window_width=None):
    '''It trims from the sequence  bad quality extremes.

    This function uses our algorithm based in the average of the neighbours
    qualities. It calculates the average quality of each position taking into
    account the qualities of the neighbours.
    Arguments:
        .- quality_threshold. Minimun quality needed to pass the check. For
        phred qualities a number of 20 is a good threshold
        .- quality_window_width: The number of nucleotide qualities of each side
         to calculate the average.
        .- min_quality_bases: How many nucleotides we need to define the start
        of a good quality zone. example:
                0 0 0 1 1 0 1 1 1
                      + +   > > >
                I the min_quality_bases is 2, the start end of the bad quality
                zone start with +. if it is 3, it starts with >
        .- min_seq_length: Minimun seq length of the new sequence to mark as
        valid. Otherwise we dismiss the sequence
    '''
    quality = seq.qual
    seq_len = len(quality)
    # Define defaults
    (min_quality_bases, min_seq_length, quality_window_width) = \
    _trim_seq_by_quality_defaults(seq_len, min_quality_bases, min_seq_length,
                                  quality_window_width)
    #calculate the sliding window qual
    qual_average_array = _calculate_sliding_window_qual(quality,
                                                        quality_window_width)
    # Now we convert the quality average array in a boolean string. 1 if the
    # quality is good, and 0 if it is bad. Depending on the treshold
    boolean_quality_treshold = _quality_to_boolean(quality_treshold,
                                                   qual_average_array)

    start, end = _trim_bad_qual_extremes(boolean_quality_treshold,
                                         min_quality_bases)
    new_seq = seq[start:end]
    if len(new_seq.qual) < min_seq_length:
        return None
    else:
        return new_seq
def _trim_bad_qual_extremes(bool_seq, min_quality_bases):
    '''It returns start and and of the new sequence. Givig the 0/1 string.'''
    start = re.search('0*(1{%d})' % min_quality_bases, bool_seq).start(1)

    #First I reverse de quality string
    bool_seq = bool_seq[::-1]
    end = re.match('0*(1{%d})' % min_quality_bases , bool_seq).start(1)
    end = len(bool_seq) - end
    return start, end
def _calculate_sliding_window_qual(quality, quality_window_width):
    '''It takes into account the neighbour qualities to calculate the new
    quality. The window size is variable '''
    average_quality = []
    #pylint: disable-msg=W0612
    for i, single_qual in enumerate(quality):
        if quality_window_width > i:
            qual_slice = quality[0: i + quality_window_width +1]
        else:
            qual_slice = quality[i -quality_window_width:
                                 i + quality_window_width +1]
        average = sum(qual_slice) / float(len(qual_slice))
        average_quality.append(average)
    return average_quality

def _quality_to_boolean(quality_treshold, qual_average_array):
    '''It converts the average_quality array in a boolean string.  1 if the
    quality is good, and 0 if it is bad. Depending on the treshold'''
    boolean_qual = []
    for quality in qual_average_array:
        if quality > quality_treshold:
            boolean_qual.append('1')
        else:
            boolean_qual.append('0')
    return ''.join(boolean_qual)

def _trim_seq_by_quality_defaults(seq_len, min_quality_bases, min_seq_length,
                                  quality_window_width):
    '''We define defaults for the  trim_seq_by_quality function.

    Using comments of Giles Weaver <giles.weaver@googlemail.com> to the
    biopython list.

     '''
    if min_quality_bases is None:
        if seq_len < 70:
            min_quality_bases = 6
        elif seq_len < 300:
            min_quality_bases = 15
        else:
            min_quality_bases = 25

    if quality_window_width is None:
        if seq_len < 70:
            quality_window_width = 2
        elif seq_len < 300:
            quality_window_width = 3
        else:
            quality_window_width = 4

    if min_seq_length is None:
        fiftypercent = seq_len / 2
        if fiftypercent > 100:
            min_seq_length = 100
        else:
            min_seq_length = fiftypercent
    return (min_quality_bases, min_seq_length, quality_window_width)

def mask_low_complexity(sequence):
    '''It adds a mask to the sequence where low clomplexity is found

    It uses mdust from the seqclean package
    '''

    mask_low_complex_by_seq = create_runner(kind='mdust')
    fhand = mask_low_complex_by_seq(sequence)[0]
    return  parse_fasta(fhand)

def mask_polya(sequence):
    '''It adds a mask to the sequence where poly A are found

    It uses trimpoly from seqclean package
    '''
    parameters = {'min_score':'10', 'end':'x', 'incremental_dist':'20',
                  'fixed_dist':None}
    mask_polya_by_seq = create_runner(kind='trimpoly', parameters=parameters)
    fhand = mask_polya_by_seq(sequence)[0]
    masked_sequence = _sequence_from_trimpoly(fhand, sequence, trim=False)

    return SeqWithQuality(seq=masked_sequence)

def strip_seq_by_quality_trimpoly(sequence):
    '''It strip the sequence where low quality is found

    It uses trimpoly from seqclean package.
    This program does not work well with short sequences, and it only can
    look at the last 30 nucleotides max
    '''
    if len(sequence) < 80:
        msg = 'Sequence must be at least of 70 nucleotides to be used by this'
        raise ValueError(msg)
    parameters = {'only_n_trim':None, 'ntrim_above_percent': '3'}
    mask_polya_by_seq = create_runner(kind='trimpoly', parameters=parameters)
    fhand = mask_polya_by_seq(SeqWithQuality(seq=sequence))[0]
    masked_sequence = _sequence_from_trimpoly(fhand, sequence, trim=True)

    return SeqWithQuality(seq=masked_sequence)

def _sequence_from_trimpoly(fhand_trimpoly_out, sequence, trim):
    '''It return new sequence giving tha trimpoly output and the old sequence
     trim option is used to trim os mask the low quality sequence '''

    trimp_data = fhand_trimpoly_out.readline().split()
    end3 = int(trimp_data[2]) - 1
    end5 = int(trimp_data[3])
    new_sequence = ''
    str_seq = sequence.seq
    if not trim:
        new_sequence  += str_seq[:end3].lower()
    new_sequence += str_seq[end3:end5]
    if not trim:
        new_sequence += str_seq[end5:].lower()
    new_seqrec = SeqWithQuality(name=sequence.name,
                                description=sequence.description,
                                annotations=sequence.annotations,
                                seq=new_sequence,
                                qual=sequence.qual)
    return new_seqrec

def strip_seq_by_quality_lucy(sequence):
    '''It trims from the sequence  bad quality sections.

    It uses lucy external program
    '''
    if sequence.name is None:
        raise ValueError('lucy requires that the sequence has a name')
    elif len(sequence) < 130:
        raise ValueError('lucy requires a minimun sequence length of 130')
    #we run lucy
    run_lucy_for_seq = create_runner(kind='lucy')
    #pylint: disable-msg=W0612
    seq_out_fhand, qual_out_fhand = run_lucy_for_seq(sequence)
    #from the output we know where to strip the seq
    name, description, seq = get_content_from_fasta(seq_out_fhand)
    #lucy can consider that the seq is low qual and return an empty file
    if description is None:
        return None
    start, end = description.split()[-2:]
    #we count from zero
    start, end = int(start) - 1, int(end)
    striped_seq = sequence[start:end]
    return striped_seq





