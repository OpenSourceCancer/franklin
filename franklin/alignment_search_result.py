'''This module holds the code that allows to analyze the alignment search
result analysis.

It can deal with blasts, iprscan or ssaha2 results.
This results can be parsed, filtered and analyzed.

This module revolves around a memory structure that represents a blast or
an iprscan result. The schema of this structure is:
result = {'query':the_query_sequence,
          'matches': [a_list_of_matches(hits in the blast terminology)]
         }
The sequence can have: name, description, annotations={'database':some db} and
len(sequence).
Every match is a dict.
match  = {'subject':the subject sequence
          'start'  :match start position in bp in query
          'end'    :match end position in bp in query
          'subject_start' : match start position in bp in subject
          'subject_end'    :match end position in bp in subject
          'scores' :a dict with the scores
          'match_parts': [a list of match_parts(hsps in the blast lingo)]
          'evidences'  : [a list of tuples for the iprscan]
         }
All the scores are holded in a dict
scores  = {'key1': value1, 'key2':value2}
For instance the keys could be expect, similarity and identity for the blast

match_part is a dict:
    match_part = {'query_start'    : the query start in the alignment in bp
                  'query_end'      : the query end in the alignment in bp
                  'query_strand'   : 1 or -1
                  'subject_start'  : the subject start in the alignment in bp
                  'subject_end'    : the subject end in the alignment in bp
                  'subject_strand' : 1 or -1
                  'scores'         :a dict with the scores
            }
Iprscan has several evidences generated by different programs and databases
for every match. Every evidence is similar to a match.
'''

# Copyright 2009 Jose Blanca, Peio Ziarsolo, COMAV-Univ. Politecnica Valencia
# This file is part of franklin.
# franklin is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

# franklin is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR  PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with franklin. If not, see <http://www.gnu.org/licenses/>.

import itertools, copy
from math import log10
from operator import itemgetter

from Bio.Blast import NCBIXML
from Bio.Seq import UnknownSeq
from franklin.seq.seqs import SeqWithQuality, SeqOnlyName


def _lines_for_every_tab_blast(fhand):
    'It returns the lines for every query in the tabular blast'
    ongoing_query = None
    match_parts = []
    for line in fhand:
        (query, subject, identity, alignment_length, mismatches, gap_opens,
         query_start, query_end, subject_start, subject_end, expect, score) = \
                                                           line.strip().split()
        query_start   = int(query_start) - 1
        query_end     = int(query_end) - 1
        subject_start = int(subject_start) - 1
        subject_end   = int(subject_end) - 1
        expect        = float(expect)
        score         = float(score)
        identity      = float(identity)
        match_part = {'subject_start': subject_start,
                      'subject_end'  : subject_end,
                      'query_start'  : query_start,
                      'query_end'    : query_end,
                      'scores'       : {'expect'    : expect,
                                        'identity'  : identity}}
        if ongoing_query is None:
            ongoing_query = query
            match_parts.append({'subject':subject, 'match_part':match_part})
        elif query == ongoing_query:
            match_parts.append({'subject':subject, 'match_part':match_part})
        else:
            yield ongoing_query, match_parts
            match_parts = [{'subject':subject, 'match_part':match_part}]
            ongoing_query = query
    if ongoing_query:
        yield ongoing_query, match_parts

def _group_match_parts_by_subject(match_parts):
    'It yields lists of match parts that share the subject'
    parts = []
    ongoing_subject = None
    for match_part in match_parts:
        subject = match_part['subject']
        if ongoing_subject is None:
            parts.append(match_part['match_part'])
            ongoing_subject = subject
        elif ongoing_subject == subject:
            parts.append(match_part['match_part'])
        else:
            yield ongoing_subject, parts
            parts = [match_part['match_part']]
            ongoing_subject = subject
    else:
        yield ongoing_subject, parts

def _tabular_blast_parser(fhand):
    'It parses the tabular output of a blast result and yields Alignment result'
    fhand.seek(0, 0)

    for query, match_parts in _lines_for_every_tab_blast(fhand):
        matches = []
        for subject, match_parts in _group_match_parts_by_subject(match_parts):
            #match start and end
            match_start, match_end = None, None
            match_subject_start, match_subject_end = None, None
            for match_part in match_parts:
                if (match_start is None or
                    match_part['query_start'] < match_start):
                    match_start = match_part['query_start']
                if match_end is None or match_part['query_end'] > match_end:
                    match_end = match_part['query_end']
                if (match_subject_start is None or
                    match_part['subject_start'] < match_subject_start):
                    match_subject_start = match_part['subject_start']
                if (match_subject_end is None or
                   match_part['subject_end'] > match_subject_end):
                    match_subject_end = match_part['subject_end']
            match = {'subject': SeqOnlyName(name=subject),
                     'start'  : match_start,
                     'end'    : match_end,
                     'subject_start': match_subject_start,
                     'subject_end'  : match_subject_end,
                     'scores' : {'expect':match_parts[0]['scores']['expect']},
                     'match_parts' : match_parts}
            matches.append(match)
        if matches:
            yield {'query'  : SeqOnlyName(name=query),
                   'matches': matches}

class TabularBlastParser(object):
    'It parses the tabular output of a blast result'
    def __init__(self, fhand):
        'The init requires a file to be parsed'
        self._gen = _tabular_blast_parser(fhand)

    def __iter__(self):
        'Part of the iterator protocol'
        return self

    def next(self):
        'It returns the next blast result'
        return self._gen.next()

class BlastParser(object):
    '''An iterator  blast parser that yields the blast results in a
    multiblast file'''
    def __init__(self, fhand, subj_def_as_accesion=None):
        'The init requires a file to be parser'
        fhand.seek(0, 0)
        sample = fhand.read(10)
        if sample and 'xml' not in sample:
            raise 'Not a xml file'
        fhand.seek(0, 0)
        self._blast_file = fhand
        blast_version, plus = self._get_blast_version()
        self._blast_file.seek(0, 0)

        if ((blast_version and plus) or
                                (blast_version and blast_version > '2.2.21')):
            self.use_query_def_as_accession = True
            self.use_subject_def_as_accession = True

        else:
            self.use_query_def_as_accession = True
            self.use_subject_def_as_accession = False

        if subj_def_as_accesion is not None:
            self.use_subject_def_as_accession = subj_def_as_accesion

        #we use the biopython parser
        #if there are no results we put None in our blast_parse results
        self._blast_parse = None
        if fhand.read(1) == '<':
            fhand.seek(0)
            self._blast_parse = NCBIXML.parse(fhand)

    def __iter__(self):
        'Part of the iterator protocol'
        return self

    def _create_result_structure(self, bio_result):
        'Given a BioPython blast result it returns our result structure'
        #the query name and definition
        definition = bio_result.query
        if self.use_query_def_as_accession:
            items = definition.split(' ', 1)
            name = items[0]
            if len(items) > 1:
                definition = items[1]
            else:
                definition = None
        else:
            name = bio_result.query_id
            definition = definition
        if definition is None:
            definition = "<unknown description>"
        #length of query sequence
        length = bio_result.query_letters
        #now we can create the query sequence
        query = SeqWithQuality(name=name, description=definition,
                               seq=UnknownSeq(length=length))

        #now we go for the hits (matches)
        matches = []
        for alignment in bio_result.alignments:
            #the subject sequence
            if self.use_subject_def_as_accession:
                items = alignment.hit_def.split(' ', 1)
                name = items[0]
                if len(items) > 1:
                    definition = items[1]
                else:
                    definition = None
            else:
                name = alignment.accession
                definition = alignment.hit_def

            if definition is None:
                definition = "<unknown description>"

            length = alignment.length
            subject = SeqWithQuality(name=name, description=definition,
                                        seq=UnknownSeq(length=length))

            #the hsps (match parts)
            match_parts = []
            match_start, match_end = None, None
            match_subject_start, match_subject_end = None, None
            for hsp in alignment.hsps:
                expect = hsp.expect
                subject_start = hsp.sbjct_start
                subject_end = hsp.sbjct_end
                query_start = hsp.query_start
                query_end = hsp.query_end
                hsp_length = len(hsp.query)
                #We have to check the subject strand
                if subject_start < subject_end:
                    subject_strand = 1
                else:
                    subject_strand = -1
                    subject_start, subject_end = (subject_end,
                                                  subject_start)
                #Also the query strand
                if query_start < query_end:
                    query_strand = 1
                else:
                    query_strand = -1
                    query_start, query_end = query_end, query_start

                try:
                    similarity = hsp.positives * 100.0 / float(hsp_length)
                except TypeError:
                    similarity = None
                try:
                    identity = hsp.identities * 100.0 / float(hsp_length)
                except TypeError:
                    identity = None
                match_parts.append({
                    'subject_start'  : subject_start,
                    'subject_end'    : subject_end,
                    'subject_strand' : subject_strand,
                    'query_start'    : query_start,
                    'query_end'      : query_end,
                    'query_strand'   : query_strand,
                    'scores'         : {'similarity': similarity,
                                        'expect'    : expect,
                                        'identity'  : identity}
                    })
                # It takes the first loc and the last loc of the hsp to
                # determine hit start and end
                if match_start is None or query_start < match_start:
                    match_start = query_start
                if match_end is None or query_end > match_end:
                    match_end = query_end
                if match_subject_start is None or subject_start < match_subject_start:
                    match_subject_start = subject_start
                if match_subject_end is None or subject_end > match_subject_end:
                    match_subject_end = subject_end
            matches.append({
                'subject': subject,
                'start'  : match_start,
                'end'    : match_end,
                'subject_start': match_subject_start,
                'subject_end'  : match_subject_end,
                'scores' : {'expect':match_parts[0]['scores']['expect']},
                'match_parts' : match_parts})
        result = {'query'  : query,
                  'matches': matches}
        return result
    def _get_blast_version(self):
        'It gets blast parser version'
        version = None
        plus    = False
        for line in self._blast_file:
            line = line.strip()
            if line.startswith('<BlastOutput_version>'):
                version = line.split('>')[1].split('<')[0].split()[1]
                break

        if version and '+' in version:
            plus = True
            version = version[:-1]
        return version, plus

    def next(self):
        'It returns the next blast result'
        if self._blast_parse is None:
            raise StopIteration
        else:
            bio_result = self._blast_parse.next()
            #now we have to change this biopython blast_result in our
            #structure
            our_result = self._create_result_structure(bio_result)
            return our_result

class ExonerateParser(object):
    '''Exonerate parser, it is a iterator that yields the result for each
    query separated'''

    def __init__(self, fhand):
        'The init requires a file to be parser'
        self._fhand = fhand
        self._exonerate_results = self._results_query_from_exonerate()
    def __iter__(self):
        'Part of the iterator protocol'
        return self

    def _results_query_from_exonerate(self):
        '''It takes the exonerate cigar output file and yields the result for
        each query. The result is a list of match_parts '''
        self._fhand.seek(0, 0)
        cigar_dict = {}
        for line in  self._fhand:
            if not line.startswith('cigar_like:'):
                continue
            items = line.split(':', 1)[1].strip().split()
            query_id = items[0]
            if query_id not in cigar_dict:
                cigar_dict[query_id] = []
            cigar_dict[query_id].append(items)
        for query_id, values in cigar_dict.items():
            yield values

    @staticmethod
    def _create_structure_result(query_result):
        '''It creates the result dictionary structure giving a list of
        match_parts of a query_id '''
        #TODO add to the match the match subject start and end
        struct_dict = {}
        query_name = query_result[0][0]
        query_length = int(query_result[0][9])

        query = SeqWithQuality(name=query_name,
                                      seq=UnknownSeq(length=query_length))
        struct_dict['query'] = query
        struct_dict['matches'] = []
        for match_part_ in query_result:
            (query_name, query_start, query_end, query_strand, subject_name,
            subject_start, subject_end, subject_strand, score, query_length,
            subject_length, similarity) = match_part_
            query_start = int(query_start)
            #they number the positions between symbols
            # A C G T
            #0 1 2 3 4
            #Hence the subsequence "CG" would have start=1, end=3, and length=2
            #but we would say start=1 and end=2
            query_end = int(query_end) - 1
            subject_start = int(subject_start)
            subject_end = int(subject_end) - 1
            query_strand = _strand_transform(query_strand)
            subject_strand = _strand_transform(subject_strand)
            score = int(score)
            similarity = float(similarity)
            # For each line , It creates a match part dict
            match_part = {}
            match_part['query_start'] = query_start
            match_part['query_end'] = query_end
            match_part['query_strand'] = query_strand
            match_part['subject_start'] = subject_start
            match_part['subject_end'] = subject_end
            match_part['subject_strand'] = subject_strand
            match_part['scores'] = {'score':score,
                                           'similarity':similarity}

            # Check if the match is already added to the struct. A match is
            # defined by a list of part matches between a query and a subject
            match_num = _match_num_if_exists_in_struc(subject_name, struct_dict)
            if match_num is not None:
                match = struct_dict['matches'][match_num]
                if match['start'] > query_start:
                    match['start'] = query_start
                if match['end'] < query_end:
                    match['end'] = query_end
                if match['scores']['score'] < score:
                    match['scores']['score'] = score
                match['match_parts'].append(match_part)
            else:
                match = {}
                match['subject'] = SeqWithQuality(name=subject_name,
                                     seq=UnknownSeq(length=int(subject_length)))
                match['start'] = query_start
                match['end'] = query_end
                match['scores'] = {'score':score}
                match['match_parts'] = []
                match['match_parts'].append(match_part)
                struct_dict['matches'].append(match)
        return struct_dict

    def next(self):
        '''It return the next exonerate hit'''
        query_result = self._exonerate_results.next()
        return self._create_structure_result(query_result)

def _strand_transform(strand):
    '''It transfrom the +/- strand simbols in our user case 1/-1 caracteres '''
    if strand == '-':
        return - 1
    elif strand == '+':
        return 1

def _match_num_if_exists_in_struc(subject_name, struct_dict):
    'It returns the match number of the list of matches that is about subject'
    for i, match in enumerate(struct_dict['matches']):
        if subject_name == match['subject'].name:
            return i
    return None

def get_alignment_parser(kind):
    '''It returns a parser depending of the aligner kind '''
    if 'blast_tab' == kind:
        parser = TabularBlastParser
    elif 'blast' in kind:
        parser = BlastParser
    else:
        parsers = {'exonerate':ExonerateParser}
        parser = parsers[kind]
    return parser

def get_match_score(match, score_key, query=None, subject=None):
    '''Given a match it returns its score.

    It tries to get the score from the match, if it's not there it goes for
    the first match_part.
    It can also be a derived score like the incompatibility. All derived scores
    begin with d_
    '''
    #the score can be in the match itself or in the first
    #match_part
    if score_key in match['scores']:
        score = match['scores'][score_key]
    else:
        #the score is taken from the best hsp (the first one)
        score = match['match_parts'][0]['scores'][score_key]
    return score

def get_match_scores(match, score_keys, query, subject):
    '''It returns the scores for one match.

    scores should be a list and it will return a list of scores.
    '''
    scores_res = []
    for score_key in score_keys:
        score = get_match_score(match, score_key, query, subject)
        scores_res.append(score)
    return scores_res

def alignment_results_scores(results, scores, filter_same_query_subject=True):
    '''It returns the list of scores for all results.

    For instance, for a blast a generator with all e-values can be generated.
    By default, the results with the same query and subject will be filtered
    out.
    The scores can be a single one or a list of them.
    '''
    #for each score we want a list to gather the results
    score_res = []
    for score in scores:
        score_res.append([])
    for result in results:
        query = result['query']
        for match in result['matches']:
            subject = match['subject']
            if (filter_same_query_subject and query is not None and subject is
                not None and query.name == subject.name):
                continue
            #all the scores for this match
            score_values = get_match_scores(match, scores, query, subject)
            #we append each score to the corresponding result list
            for index, value in enumerate(score_values):
                score_res[index].append(value)
    if len(score_res) == 1:
        return score_res[0]
    else:
        return score_res

'''
A graphical overview of a blast result can be done counting the hits
with a certain level of similarity. We can represent a distribution
with similarity in the x axe and the number of hits for each
similarity in the y axe. It would be something like.

 n |
 u |
 m |
   |       x
 h |      x x
 i |     x   x     x
 t |    x      x  x x
 s | xxx        xx   x
    ----------------------
         % similarity

Looking at this distribution we get an idea about the amount of
similarity found between the sequences used in the blast.

Another posible measure between a query and a subject is the
region that should be aligned, but it is not, the incompatible
region.

   query         -----------------
                   |||||
   subject   ----------------
                 ++     +++++ <-incompabible regions

For every query-subject pair we can calculate the similarity and the
incompatible region. We can also draw a distribution with both
measures. (a 3-d graph viewed from the top with different colors
for the different amounts of hits).

 % |
 s |
 i |       ..
 m |
 i |             ..
 l |           ..
 a |     x
 r |      xx         ..
 i |
 t | xx       xx
 y | xx       xx
   -----------------------
    % incompatibility

'''

def build_relations_from_aligment(fhand, query_name, subject_name):
    '''It returns a relations dict given an alignment in markx10 format

    The alignment must be only between two sequences query against subject
    '''

    #we parse the aligment
    in_seq_section = 0
    seq, seq_len, al_start = None, None, None
    for line in fhand:
        line = line.strip()
        if not line:
            continue
        if line[0] == '>' and line[1] != '>':
            if in_seq_section:
                seq = {'seq': seq,
                       'length': seq_len,
                       'al_start': al_start - 1,
                       'name': query_name}
                if in_seq_section == 1:
                    seq0 = seq
            in_seq_section += 1
            seq = ''
            continue
        if not in_seq_section:
            continue
        if '; sq_len:' in line:
            seq_len = int(line.split(':')[-1])
        if '; al_display_start:' in line:
            al_start = int(line.split(':')[-1])
        if line[0] not in (';', '#'):
            seq += line
    seq1 = {'seq': seq,
            'length': seq_len,
            'al_start': al_start - 1,
            'name': subject_name}

    #now we get the segments
    gap = '-'
    pos_seq0 = seq0['al_start']
    pos_seq1 = seq1['al_start']
    segment_start = None
    segments = []
    for ali_pos in range(len(seq1['seq'])):
        try:
            nucl0, nucl1 = seq0['seq'][ali_pos+1], seq1['seq'][ali_pos+1]
            if (nucl0 == gap or nucl1 == gap) and segment_start:
                do_segment = True
                segment_end = pos_seq0 - 1, pos_seq1 - 1
            else:
                do_segment = False
        except IndexError:
            do_segment = True
            segment_end = pos_seq0, pos_seq1
        if do_segment:
            segment= {seq0['name']: (segment_start[0], segment_end[0]),
                      seq1['name']: (segment_start[1], segment_end[1]),}
            segments.append(segment)
            segment_start = None
        if nucl0 != gap and nucl1 != gap and segment_start is None:
            segment_start = pos_seq0, pos_seq1
        if nucl0 != gap:
            pos_seq0 += 1
        if nucl1 != gap:
            pos_seq1 += 1

    relations = {}
    for seg in segments:
        for seq_name, limits in seg.items():
            if seq_name not in relations:
                relations[seq_name] = []
            relations[seq_name].append(limits)
    return relations

def _get_match_score(match, score_key, query=None, subject=None):
    '''Given a match it returns its score.

    It tries to get the score from the match, if it's not there it goes for
    the first match_part.
    '''
    #the score can be in the match itself or in the first
    #match_part
    if score_key in match['scores']:
        score = match['scores'][score_key]
    else:
        #the score is taken from the best hsp (the first one)
        score = match['match_parts'][0]['scores'][score_key]
    return score

def _score_above_threshold(score, min_score, max_score, log_tolerance,
                           log_best_score):
    'It checks if the given score is a good one'
    if log_tolerance is None:
        if min_score is not None and score >= min_score:
            match_ok = True
        elif max_score is not None and score <= max_score:
            match_ok = True
        else:
            match_ok = False
    else:
        if max_score is not None and score == 0.0:
            match_ok = True
        elif min_score is not None and score <= min_score:
            match_ok = False
        elif max_score is not None and score >= max_score:
            match_ok = False
        elif abs(log10(score) - log_best_score) < log_tolerance:
            match_ok = True
        else:
            match_ok = False
    return match_ok

def _create_scores_mapper_(score_key, score_tolerance=None,
                           max_score=None, min_score=None):
    'It creates a mapper that keeps only the best matches'

    if score_tolerance is not None:
        log_tolerance = log10(score_tolerance)
    else:
        log_tolerance = None
    def map_(alignment):
        '''It returns an alignment with the best matches'''
        if alignment is None:
            return None
        if log_tolerance is None:
            log_best_score = None
        else:
            #score of the best match
            try:
                best_match = alignment['matches'][0]
                best_score = _get_match_score(best_match, score_key)
                if best_score == 0.0:
                    log_best_score = 0.0
                else:
                    log_best_score = log10(best_score)
            except IndexError:
                log_best_score = None

        filtered_matches = []
        for match in alignment['matches']:
            filtered_match_parts = []
            for match_part in match['match_parts']:
                score = match_part['scores'][score_key]
                if _score_above_threshold(score, min_score, max_score,
                                          log_tolerance, log_best_score):
                    filtered_match_parts.append(match_part)
            match['match_parts']= filtered_match_parts
            if not len(match['match_parts']):
                continue
            #is this match ok?
            match_score = get_match_score(match, score_key)
            if _score_above_threshold(match_score, min_score, max_score,
                                      log_tolerance, log_best_score):
                filtered_matches.append(match)
        alignment['matches'] = filtered_matches
        return alignment
    return map_

def _create_best_scores_mapper(score_key, score_tolerance=None,
                              max_score=None, min_score=None):
    'It creates a mapper that keeps only the best matches'
    return _create_scores_mapper_(score_key, score_tolerance=score_tolerance,
                                 max_score=max_score, min_score=min_score)

def _create_scores_mapper(score_key, max_score=None, min_score=None):
    'It creates a mapper that keeps only the best matches'
    if max_score is None and min_score is None:
        raise ValueError('Either max_score or min_score should be given')
    return _create_scores_mapper_(score_key, max_score=max_score,
                                 min_score=min_score)

def _create_deepcopy_mapper():
    'It creates a mapper that does a deepcopy of the alignment'
    def map_(alignment):
        'It does the deepcopy'
        return copy.deepcopy(alignment)
    return map_

def _create_empty_filter():
    'It creates a filter that removes the false items'
    def filter_(alignment):
        'It filters the empty alignments'
        if alignment:
            return True
        else:
            return False
    return filter_

def _fix_match_start_end(match):
    'Given a match it fixes the start and end based on the match_parts'
    match_start, match_end = None, None
    match_subject_start, match_subject_end = None, None
    for match_part in match['match_parts']:
        if ('query_start' in match_part and
            (match_start is None or
             match_part['query_start'] < match_start)):
            match_start = match_part['query_start']
        if ('query_end' in match_part and
            (match_end is None or match_part['query_end'] > match_end)):
            match_end = match_part['query_end']
        if ('subject_start' in match_part and
            (match_subject_start is None or
             match_part['subject_start'] < match_subject_start)):
            match_subject_start = match_part['subject_start']
        if ('subject_end' in match_part and
            (match_subject_end is None or
             match_part['subject_end'] > match_subject_end)):
            match_subject_end = match_part['subject_end']
    if match_start is not None:
        match['start'] = match_start
    if match_end is not None:
        match['end'] = match_end
    if match_subject_start is not None:
        match['subject_start'] = match_subject_start
    if match_subject_end is not None:
        match['subject_end'] = match_subject_end

def _create_fix_matches_mapper():
    ''''It creates a function that removes alignments with no matches.

    It also removes matches with no match_parts
    '''
    def mapper_(alignment):
        'It removes the empty match_parts and the alignments with no matches'
        if alignment is None:
            return None
        new_matches = []
        for match in alignment['matches']:
            if len(match['match_parts']):
                _fix_match_start_end(match)
                new_matches.append(match)
        if not new_matches:
            return None
        else:
            alignment['matches'] = new_matches
        return alignment
    return mapper_

def _covered_segments(match_parts, in_query=True):
    '''Given a list of match_parts it returns the coverd segments.

       match_part 1  -------        ----->    -----------
       match_part 2       ------
       It returns the list of segments coverd by the match parts either in the
       query or in the subject.
    '''
    molecule = 'query' if in_query else 'subj'

    #we collect all start and ends
    START = 0
    END   = 1
    limits = [] #all hsp starts and ends
    for match_part in match_parts:
        if in_query:
            start = match_part['query_start']
            end   = match_part['query_end']
        else:
            start = match_part['subject_start']
            end   = match_part['subject_end']
        limit_1 = (START, start)
        limit_2 = (END, end)
        limits.append(limit_1)
        limits.append(limit_2)

    #now we sort the hsp limits according their location
    def cmp_query_location(hsp_limit1, hsp_limit2):
        'It compares the locations'
        return hsp_limit1[molecule] - hsp_limit2[molecule]
    #sort by secondary key: start before end
    limits.sort(key=itemgetter(0))
    #sort by location (primary key)
    limits.sort(key=itemgetter(1))

    #merge the ends and start that differ in only one base
    filtered_limits = []
    previous_limit = None
    for limit in limits:
        if previous_limit is None:
            previous_limit = limit
            continue
        if (previous_limit[0] == END and limit[0] == START and
            previous_limit[1] == limit[1] - 1):
            #These limits cancelled each other
            previous_limit = None
            continue
        filtered_limits.append(previous_limit)
        previous_limit = limit
    else:
        filtered_limits.append(limit)
    limits = filtered_limits

    #now we create the merged hsps
    starts = 0
    segments = []
    for limit in limits:
        if limit[0] == START:
            starts += 1
            if starts == 1:
                segment_start = limit[1]
        elif limit[0] == END:
            starts -= 1
            if starts == 0:
                segment = (segment_start, limit[1])
                segments.append(segment)
    return segments

def _match_length(match, length_from_query):
    '''It returns the match length.

    It does take into account only the length covered by match_parts.
    '''
    segments = _covered_segments(match['match_parts'], length_from_query)
    length = 0
    for segment in segments:
        match_part_len = segment[1] - segment[0] + 1
        length += match_part_len
    return length

def _create_min_length_mapper(length_in_query, min_num_residues=None,
                              min_percentage=None):
    '''It creates a mapper that removes short matches.

    The length can be given in percentage or in number of residues.
    The length can be from the query or the subject
    '''
    if not isinstance(length_in_query, bool):
        raise ValueError('length_in_query should be a boolean')
    if min_num_residues is None and min_percentage is None:
        raise ValueError('min_num_residues or min_percentage should be given')
    elif min_num_residues is not None and min_percentage is not None:
        msg =  'Both min_num_residues or min_percentage can not be given at the'
        msg += ' same time'
        raise ValueError(msg)
    def map_(alignment):
        '''It returns an alignment with the matches that span long enough'''
        if alignment is None:
            return None

        filtered_matches = []
        query = alignment.get('query', None)
        for match in alignment['matches']:
            match_length = _match_length(match, length_in_query)
            if min_num_residues is not None:
                if match_length >= min_num_residues:
                    match_ok = True
                else:
                    match_ok = False
            else:
                if length_in_query:
                    percentage = (match_length / float(len(query))) * 100.0
                else:
                    subject = match['subject']
                    percentage = (match_length / float(len(subject))) * 100.0
                if percentage >= min_percentage:
                    match_ok = True
                else:
                    match_ok = False
            if match_ok:
                filtered_matches.append(match)
        alignment['matches'] = filtered_matches
        return alignment
    return map_

MAPPER = 1
FILTER = 2

FILTER_COLLECTION = {'best_scores':{'funct_factory': _create_best_scores_mapper,
                                    'kind': MAPPER},
                     'score_threshold':{'funct_factory': _create_scores_mapper,
                                    'kind': MAPPER},
                     'min_length':{'funct_factory': _create_min_length_mapper,
                                    'kind': MAPPER},
                     'deepcopy':{'funct_factory': _create_deepcopy_mapper,
                                 'kind': MAPPER},
                     'fix_matches':{'funct_factory': _create_fix_matches_mapper,
                                    'kind': MAPPER},
                     'filter_empty':{'funct_factory': _create_empty_filter,
                                     'kind': FILTER},
                    }

def filter_alignments(alignments, config):
    '''It filters and maps the given alignments.

    The filters and maps to use will be decided based on the configuration.
    '''
    config = copy.deepcopy(config)
    config.insert(0, {'kind': 'deepcopy'})
    config.append({'kind': 'fix_matches'})
    config.append({'kind': 'filter_empty'})

    #create the pipeline
    for conf in config:
        funct_fact = FILTER_COLLECTION[conf['kind']]['funct_factory']
        kind     = FILTER_COLLECTION[conf['kind']]['kind']
        del conf['kind']
        function = funct_fact(**conf)
        if kind == MAPPER:
            alignments = itertools.imap(function, alignments)
        else:
            alignments = itertools.ifilter(function, alignments)
    return alignments
