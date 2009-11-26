'''
Created on 26/11/2009

@author: jose
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

import unittest, os
from biolib.seq.seqs import SeqWithQuality, Seq
from biolib.seq.seq_analysis import infer_introns_for_cdna
from biolib.utils.misc_utils import DATA_DIR

class IntronTest(unittest.TestCase):
    'It test that we can locate introns'
    @staticmethod
    def test_introns_for_cdna():
        'It tests that we can locate introns'
        seq1 =  'ATGATAATTATGAAAAATAAAATAAAATTTAATTATATAATTCATTTCATCTAATCGTACAA'
        seq1 += 'GCTAGATATTACTATATCAACAACTTTGTGTATAAAAAGGGCAAGAAATTAAGCATTATCGT'
        seq1 += 'GTGAGCCACTTTTTCTATATCTAGAGATAGAAGGTTTAAAATCATGTCTCTAATTGGAAAGC'
        seq1 += 'TTGTGAGTGAATTAGAGATCAATGCAGCTGCTGAGAAATTTTACGAAATATTCAAAGATCAA'
        seq1 += 'TGTTTTCAGGTTCCCAATATAACCCCCAGATGCATTCAACAAGTTGAAATTCATGGTACTAA'
        seq1 += 'TTGGGATGGCCATGGACATGGCTCTATCAAGTCTTGGTATTACACTATTGATGGCAAGGCAG'
        seq1 += 'AAGTTTTTAAGGAACGGGTCGAGTTTCACGATGATAAATTGTTGATAGTCTTGGATGGAGTG'
        seq1 += 'GGAGGAGATGTGTTCAAAAATTATAAAAGCTTTAAACCAGCTTACCAATTTGTACCTAAGGA'
        seq1 += 'TCGTAACCATTGCCAGGCAATTCTGAGTATAGAGTATGAGAAACTTCATCATGGGTCTCCTG'
        seq1 += 'ATCCTCATAAGTATATTGACCTCATGATTGGTATCACTAACGACATTGGATCTCACATTAAA'
        seq1 += 'TAAGTATTTAATGTCTGTCACATTCTCAAGTGTGGCTTGTTAATTTGTTGTGGGAAAGTTAT'
        seq1 += 'ATTTTATTTTGAAGTCATTTTCGTGTGGTTGATTATGTATCTTTGCTATTTTGCTTTTATAT'
        seq1 += 'TTCAATAAGTTATATGGTTTATATAATATTACAAAGTAAATAAAATCCAAGGATCATCCCTT'
        seq1 += 'GTTTATGTTTCGTTATTAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
        seq1 += 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
        seq1 += 'AAAAAAAAAAAAAAAAAAAGGCCCCCCCCCCCCCCCAAAAAAATTAAAAAACCCCCCCCCCC'
        seq1 += 'CGGGGGGGGCCC'
        seq1 = SeqWithQuality(name='seq1', seq=Seq(seq1))
        blast_db_path = os.path.join(DATA_DIR, 'blast')
        introns = infer_introns_for_cdna(seq1, genomic_db='arabidopsis_genes',
                                         blast_db_path=blast_db_path)
        print introns

        seq2  = 'AAACCAACTTTCTCCCCATTTTCTTCCTCAAACCTCCATCAATGGCTTCCTTCTCCAGAATC'
        seq2 += 'CTCTCCCCATTTTCACTATTTCTTCTGATTCTTGTCATCTCCACTCAAACCCACCTCTCCTT'
        seq2 += 'TTCAGCAAGGGATCTTCTCCTCAAGTCATCTGATATCCACGATCTTCTTCCCCTTTACGGTT'
        seq2 += 'TTCCAGTCGGTCTCTTACCCAGCAATGTCAAGTCCTACACTCTCTCAGACGATGGTAGCTTC'
        seq2 += 'GTAATCGAACTCGATAGCGCTTGCTATGTCCAGTTCGCTGATCTGGTCTATTACGGCAAGAC'
        seq2 += 'GATCAAGGGGAAATTGAGCTATGGGTCATTGAGCGATGTTTCTGGGATTCAAGTCAAGAAGT'
        seq2 += 'TGTTCGCCTGGCTTCCTATTACTGGAATGAGGGTTACTTCAGACTCTAAATCCATCGAGTTT'
        seq2 += 'CAGGTTGGGTTCTTGTCTGAGGCTTTGCCGTTCAGCATGTTTGAGTCCATTCCTACATGCAG'
        seq2 += 'AAAGAAAGCTTGCCTAGAAGGGAAAACAGAGGCAGTGTGAGGTGGAAATAATAGCTTTCCAA'
        seq2 += 'AACGCTTATCCTTTTCATTGGGTGAGAGAAGCATGTTGGTCTTTGCAAGAAGAATAATGTAA'
        seq2 += 'TCTTTGTTTTTATGTCATGAACCTACGGTGTCCATTTTTAATCTTTTTCTTACATGTTCATC'
        seq2 += 'TATATTTATATC-ATATCATAAATATTCTCACATGTTTACCTAATGTTTTCTTTCAATAATA'
        seq2 += 'TTATCTTTTTACGAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
        seq2 = SeqWithQuality(name='seq2', seq=Seq(seq2))

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()