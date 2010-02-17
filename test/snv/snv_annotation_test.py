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
import unittest, os
from Bio.Seq import UnknownSeq
from Bio.SeqFeature import FeatureLocation

from franklin.utils.misc_utils import DATA_DIR
from franklin.snv.snv_annotation import create_snv_annotator
from franklin.utils.seqio_utils import seqs_in_file
from franklin.seq.seqs import SeqWithQuality, SeqFeature
from franklin.snv.snv_annotation import (SNP, INSERTION, DELETION, INVARIANT,
                                         INDEL, COMPLEX,
                                         calculate_snv_kind,
                                         sorted_alleles,
                                         calculate_maf_frequency,
                                         calculate_snv_variability,
                                         calculate_cap_enzymes)

class TestSnvAnnotation(unittest.TestCase):
    'It tests the annotation of SeqRecords with snvs'

    @staticmethod
    def test_snv_annotation():
        'It tests the annotation of SeqRecords with snvs'
        bam_fhand = open(os.path.join(DATA_DIR, 'samtools', 'seqs.bam'))
        seq_fhand = open(os.path.join(DATA_DIR, 'samtools', 'reference.fasta'))

        annotator = create_snv_annotator(bam_fhand=bam_fhand)

        for seq in seqs_in_file(seq_fhand):
            annotator(seq)

    @staticmethod
    def test_snv_kind():
        'It tests that we can infer the snv kind given a seqrecord with an snv'
        seq = SeqWithQuality(UnknownSeq(100))
        alleles = {('A', INVARIANT): {'read_names':['r1']}}
        feat = SeqFeature(location=FeatureLocation(3, 3), type='snv',
                          qualifiers={'alleles':alleles})
        seq.features.append(feat)

        assert calculate_snv_kind(feat) == INVARIANT

    @staticmethod
    def test_sort_alleles():
        'It tests that we can get the alleles'
        alleles = {('A', INVARIANT): {'read_names':['r1']},
                   ('A', DELETION): {'read_names':['r2', 'r3']}}
        feat = SeqFeature(location=FeatureLocation(3, 3), type='snv',
                          qualifiers={'alleles':alleles})
        alleles = sorted_alleles(feat)
        assert alleles[0]['kind'] == DELETION

    @staticmethod
    def test_maf_alleles():
        'It tests that we can calculate the major allele frequency'
        alleles = {('A', INVARIANT): {'read_names':['r1']},
                   ('A', DELETION): {'read_names':['r2', 'r3']}}
        feat = SeqFeature(location=FeatureLocation(3, 3), type='snv',
                          qualifiers={'alleles':alleles})
        maf = calculate_maf_frequency(feat)
        assert maf == 2/3

    @staticmethod
    def test_snv_variability():
        'It tests that we can calculate the snv variability in a sequence'
        seq = SeqWithQuality(UnknownSeq(100))
        feat1 = SeqFeature(location=FeatureLocation(3, 3), type='snv',
                          qualifiers={'alleles':{}})
        feat2 = SeqFeature(location=FeatureLocation(30, 30), type='snv',
                          qualifiers={'alleles':{}})
        seq.features.extend([feat1, feat2])
        maf = calculate_snv_variability(seq)
        assert maf == 2/100


    @staticmethod
    def test_snv_cap():
        'It tests that we can get the enzymes that are a cap'
        reference = SeqWithQuality(seq='Actgacttactgtca', name='ref')
        alleles = {('C', SNP): None,
                   ('T', INVARIANT): None}

        feat1 = SeqFeature(location=FeatureLocation(7, 7), type='snv',
                           qualifiers={'alleles':alleles})
        enzymes = calculate_cap_enzymes(feat1, reference, True)
        assert set(['HinfI', 'TscAI']) == set(enzymes)


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()