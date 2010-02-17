'''
Created on 16/02/2010

@author: jose
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
from __future__ import division

import pysam
import os


from Bio.SeqFeature import FeatureLocation

from franklin.seq.seqs import SeqFeature, SeqWithQuality
from franklin.utils.seqio_utils import get_seq_name
from franklin.utils.cmd_utils import call, create_runner
from copy import copy

DELETION_ALLELE = '-'

SNP = 0
INSERTION = 1
DELETION = 2
INVARIANT = 3
INDEL = 4
COMPLEX = 5

COMMON_ENZYMES = ['ecori', 'smai', 'bamhi', 'alui', 'bglii',
                  'sali', 'bgli', 'clai', 'bsteii', 'taqi',
                  'psti', 'pvuii', 'hindiii', 'ecorv', 'xbai',
                  'haeiii', 'xhoi', 'kpni', 'scai', 'banii',
                  'hinfi', 'drai', 'apai', 'asp718']

def _get_allele_from_read(aligned_read, index):
    'It returns allele, quality, is_reverse'
    allele = aligned_read.seq[index].lower()
    qual   = aligned_read.qual[index]
    return allele, qual, bool(aligned_read.is_reverse)

def _add_allele(alleles, allele, kind, read_name, read_group, is_reverse, qual,
                mapping_quality):
    'It adds one allele to the alleles dict'
    key = (allele, kind)
    if key not in alleles:
        alleles[key] = {'read_names':[], 'read_groups':[], 'orientations':[],
                       'qualities':[], 'mapping_qualities':[]}
    allele_info = alleles[key]
    allele_info['read_names'].append(read_name)
    allele_info['read_groups'].append(read_group)
    allele_info['orientations'].append(not(is_reverse))
    allele_info['qualities'].append(qual)
    allele_info['mapping_qualities'].append(qual)

def _snvs_in_bam(bam, reference):
    'It yields the snv information for every snv in the given reference'

    current_deletions = {}
    reference_id = get_seq_name(reference)
    reference_seq = reference.seq
    for column in bam.pileup(reference=reference_id):
        alleles = {}
        ref_pos = column.pos
        ref_id =  bam.getrname(column.tid)
        ref_allele = reference_seq[ref_pos].lower()
        for pileup_read in column.pileups:
            aligned_read = pileup_read.alignment

            read_group = aligned_read.opt('RG')
            read_name = aligned_read.qname
            read_mapping_qual = aligned_read.mapq

            read_pos = pileup_read.qpos

            allele = None
            qual = None
            is_reverse = None
            kind = None
            start = None
            end = None
            #which is the allele for this read in this position?
            if read_name in current_deletions:
                current_deletion = current_deletions[read_name]
                if current_deletion[1]:
                    allele = DELETION_ALLELE * current_deletion[0]
                    qual = None
                    is_reverse = bool(aligned_read.is_reverse)
                    kind = 'deletion'
                    current_deletion[1] = False #we have returned it already
                #we count how many positions should be skip until this read
                #has now deletion again
                current_deletion[0] -= 1
                if current_deletion[0] == 0:
                    del current_deletions[read_name]
            else:
                allele, qual, is_reverse = _get_allele_from_read(aligned_read,
                                                                 read_pos)
                if allele != ref_allele:
                    kind = SNP
                else:
                    kind = INVARIANT

            #is there a deletion in the next column?
            indel_length = pileup_read.indel
            if indel_length < 0:
                #deletion length, return this at the first oportunity
                current_deletions[read_name] = [-indel_length, True]

            if allele is not None:
                _add_allele(alleles, allele, kind, read_name, read_group,
                            is_reverse, qual, read_mapping_qual)

            #is there an insertion after this column
            if indel_length > 0:
                start  = read_pos + 1
                end    = start + indel_length

                allele, qual, is_reverse = _get_allele_from_read(aligned_read,
                                                              slice(start, end))
                kind = INSERTION
                _add_allele(alleles, allele, kind, read_name, read_group,
                            is_reverse, qual, read_mapping_qual)

        if len(alleles) > 1:
            yield {'ref_name':ref_id,
                   'ref_position':ref_pos,
                   'alleles':alleles}


def create_snv_annotator(bam_fhand):
    'It creates an annotator capable of annotating the snvs in a SeqRecord'

    #the bam should have an index, does the index exists?
    index_fpath = os.path.join(bam_fhand.name, '.bai')
    if not os.path.exists(index_fpath):
        call(['samtools', 'index', bam_fhand.name], raise_on_error=True)

    bam = pysam.Samfile(bam_fhand.name, 'rb')

    def annotate_snps(sequence):
        'It annotates the snvs found in the sequence'
        for snv in _snvs_in_bam(bam, reference=sequence):
            location = snv['ref_position']
            type_ = 'snv'
            qualifiers = {'alleles':snv['alleles']}
            feat = SeqFeature(location=FeatureLocation(location, location),
                              type=type_,
                              qualifiers=qualifiers)
            sequence.features.append(feat)
    return annotate_snps


def calculate_snv_kind(feature):
    'It returns the snv kind for the given feature'
    snv_kind = INVARIANT
    alleles = feature.qualifiers['alleles']
    for allele in alleles.keys():
        allele_kind = allele[1]
        snv_kind = _calculate_kind(allele_kind, snv_kind)
    return snv_kind

def _calculate_kind(kind1, kind2):
    'It calculates the result of the union of two kinds'
    if kind1 == kind2:
        return kind1
    else:
        if kind1 is INVARIANT:
            return kind2
        elif kind2 is INVARIANT:
            return kind1
        elif kind1 in [SNP, COMPLEX] or kind2 in [SNP, COMPLEX]:
            return COMPLEX
        else:
            return INDEL

def _cmp_by_read_num(allele1, allele2):
    'cmp by the number of reads for each allele'
    return len(allele2['read_names']) - len(allele1['read_names'])

def sorted_alleles(feature):
    'It returns the alleles sorted by number of reads'
    #from dict to list
    alleles = feature.qualifiers['alleles']
    alleles_list = []
    for allele, allele_info in alleles.items():
        allele_info = copy(allele_info)
        allele_info['seq'] = allele[0]
        allele_info['kind'] = allele[1]
        alleles_list.append(allele_info)
    return sorted(alleles_list, _cmp_by_read_num)

def calculate_maf_frequency(feature):
    'It returns the most frequent allele frequency'
    alleles = feature.qualifiers['alleles']
    major_number_reads = None
    total_number_reads = 0
    for allele_info in alleles.values():
        number_reads = len(allele_info['read_names'])
        if major_number_reads is None or major_number_reads < number_reads:
            major_number_reads = number_reads
        total_number_reads += number_reads
    return major_number_reads / total_number_reads

def calculate_snv_variability(sequence):
    'It returns the number of snv for every 100 pb'
    n_snvs = sum(1 for snv in sequence.get_features(kind='snv'))
    return n_snvs / len(sequence)

def calculate_cap_enzymes(feature, sequence, all_enzymes=False):
    '''Given an snv feature and a sequence it returns the list of restriction
    enzymes that distinguish between their alleles.'''

    if 'cap_enzymes' in feature.qualifiers:
        return feature.qualifiers['cap_enzymes']

    #which alleles do we have?
    alleles = set()
    for allele in feature.qualifiers['alleles'].keys():
        alleles.add(repr((allele[0], allele[1])))
    #for every pair of different alleles we have to look for differences in
    #their restriction maps
    enzymes = set()
    alleles = list(alleles)
    reference = sequence
    location = int(str(feature.location.start))
    for i_index in range(len(alleles)):
        for j_index in range(i_index, len(alleles)):
            if i_index == j_index:
                continue
            allelei = eval(alleles[i_index])
            allelei = {'allele':allelei[0], 'kind':allelei[1]}
            allelej = eval(alleles[j_index])
            allelej = {'allele':allelej[0], 'kind':allelej[1]}
            i_j_enzymes = _cap_enzymes_between_alleles(allelei, allelej,
                                                       reference, location,
                                                       all_enzymes)
            enzymes = enzymes.union(i_j_enzymes)

    enzymes = list(enzymes)
    feature.qualifiers['cap_enzymes'] = enzymes
    return enzymes

def _cap_enzymes_between_alleles(allele1, allele2, reference, location,
                                 all_enzymes=False):
    '''It looks in the enzymes that differenciate the given alleles.

    It returns a set.
    '''
    kind1 = allele1['kind']
    kind2 = allele2['kind']
    allele1 = allele1['allele']
    allele2 = allele2['allele']

    #we have to build the two sequences
    ref = reference
    loc = location
    def create_sequence(name, allele, kind):
        'The returns the sequence for the given allele'
        sseq = ref.seq
        if kind == INVARIANT:
            seq = sseq
        elif kind == SNP:
            seq = sseq[0:loc] + allele + sseq[loc + 1:]
        elif kind == DELETION:
            seq = sseq[0:loc + 1] + sseq[loc + len(allele) + 1:]
        elif kind == INSERTION:
            seq = sseq[0:loc] + allele + sseq[loc:]
        seq = SeqWithQuality(name=name, seq=seq)
        return seq
    seq1 = create_sequence('seq1', allele1, kind1)
    seq2 = create_sequence('seq2', allele2, kind2)

    parameters = {}
    if not all_enzymes:
        parameters['enzymes'] = ",".join(COMMON_ENZYMES)

    remap_runner = create_runner(tool='remap', parameters=parameters)

    result1_fhand = remap_runner(seq1)['remap']
    result2_fhand = remap_runner(seq2)['remap']
    enzymes1 = _parse_remap_output(result1_fhand)
    enzymes2 = _parse_remap_output(result2_fhand)
    enzymes = set(enzymes1).symmetric_difference(set(enzymes2))

    return enzymes

def _parse_remap_output(remap_output):
    ''' It takes the remap output and it returns a set list with the enzymes
     that cut there'''
    section = ''
    enzymes = []
    for line in open(remap_output.name):
        line = line.strip()
        if line.isspace() or len(line) < 2:
            continue
        if section == 'cut':
            if line.startswith('#'):
                section = ''
            else:
                enzymes.append(line.split()[0])

        if line.startswith('# Enzymes that cut'):
            section = 'cut'
            continue
    return enzymes
