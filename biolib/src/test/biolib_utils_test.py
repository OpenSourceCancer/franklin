'''
Created on 2009 mai 22

@author: peio
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
import StringIO
from biolib.biolib_utils import (xml_itemize, _get_xml_tail, _get_xml_header,
                                 NamedTemporaryDir, seqs_in_file,
                                 guess_seq_file_format, temp_fasta_file,
                                 FileIndex, split_long_sequences)
from biolib.seqs import SeqWithQuality

class XMLTest(unittest.TestCase):
    '''It tests the xml utils'''

    @staticmethod
    def test_xml_itemize():
        '''It tests xml itemize '''
        string = '<h><t><c></c><c></c></t></h>'
        xml = StringIO.StringIO(string)
        cont = 0
        for result in  xml_itemize(xml, 'c'):
            assert result == '<h><t><c></c></t></h>'
            cont += 1
        assert cont == 2
    def test_no_good_xml_start_end(self):
        '''Tests if the raise an error with a bad xml file. from begining to
        end '''
        xml = StringIO.StringIO('<header><conten></content></header>')
        self.failUnlessRaises(ValueError, _get_xml_header, xml, 'content')
    def test_no_good_xml_end_start(self):
        '''Tests if the raise an error with a bad xml file. From end to start'''
        xml = StringIO.StringIO('<header><content><content></header>')
        self.failUnlessRaises(ValueError, _get_xml_tail , xml, 'content')

class NamedTemporariDirTest(unittest.TestCase):
    'It test temporay named dir'
    @staticmethod
    def test_simple_named_temporary_dir():
        'It test temporay named dir'
        temp_dir = NamedTemporaryDir()
        dir_name = temp_dir.name
        assert os.path.exists(dir_name) == True
        temp_dir.close()
        assert os.path.exists(dir_name) == False

        temp_dir = NamedTemporaryDir()
        dir_name = temp_dir.name
        fhand = open(os.path.join(dir_name, 'peio'), 'w')
        assert os.path.exists(fhand.name) == True
        assert os.path.exists(dir_name)   == True
        del(temp_dir)
        assert os.path.exists(dir_name) == False

class GuessFormatSeqFileTest(unittest.TestCase):
    'It tests that we can guess the format of a sequence file'
    @staticmethod
    def test_guess_format():
        'It test that we can guess the format for the sequence files'
        fhand = StringIO.StringIO('>fasta\nACTAG\n')
        assert guess_seq_file_format(fhand) == 'fasta'

        fhand = StringIO.StringIO('LOCUS AX0809\n')
        assert guess_seq_file_format(fhand) == 'genbank'

class SeqsInFileTests(unittest.TestCase):
    'It test that we can get seqrecords out of a seq file.'
    @staticmethod
    def test_seqs_in_file():
        'It test that we get seqs without quality from a sequence file'
        fcontent = '>hola\nACGATCTAGTCATCA\n>caracola\nATCGTAGCTGATGT'
        fhand = StringIO.StringIO(fcontent)
        expected = [('hola', 'ACGATCTAGTCATCA'), ('caracola', 'ATCGTAGCTGATGT')]
        for index, seq in enumerate(seqs_in_file(fhand)):
            assert seq.name == expected[index][0]
            assert str(seq.seq) == expected[index][1]

    def test_seqquals_in_file(self):
        'It test that we get seqs with quality from two sequence files'
        fcontent = '>hola\nACGA\n>caracola\nATCG'
        fhand = StringIO.StringIO(fcontent)
        fcontent_qual = '>hola\n1 2 3 4\n>caracola\n5 6 7 8'
        fhand_qual = StringIO.StringIO(fcontent_qual)
        expected = [('hola', 'ACGA', [1, 2, 3, 4]),
                    ('caracola', 'ATCG', [5, 6, 7, 8])]
        for index, seq in enumerate(seqs_in_file(fhand, fhand_qual)):
            assert seq.name == expected[index][0]
            assert str(seq.seq) == expected[index][1]
            assert seq.qual == expected[index][2]

        #when the seq and qual names do not match we get an error
        fcontent = '>hola\nACGA\n>caracola\nATCG'
        fhand = StringIO.StringIO(fcontent)
        fcontent_qual = '>caracola\n1 2 3 4\n>hola\n5 6 7 8'
        fhand_qual = StringIO.StringIO(fcontent_qual)
        try:
            for seq in seqs_in_file(fhand, fhand_qual):
               #pylint: disable-msg=W0104
                seq.name
            self.fail()
            #pylint: disable-msg=W0704
        except RuntimeError:
            pass

class TestFastaFileUtils(unittest.TestCase):
    'here we test our utils related to fast format'

    @staticmethod
    def test_temp_fasta_file_one_seq():
        'It test temp_fasta_file'
        seqrec1 = SeqWithQuality(seq='ATGATAGATAGATGF', name='seq1')
        fhand = temp_fasta_file(seqrec1)
        content = open(fhand.name).read()
        assert content == ">seq1\nATGATAGATAGATGF\n"

    @staticmethod
    def test_temp_fasta_file_seq_iter():
        'It test temp_fasta_file'
        seqrec1 = SeqWithQuality(seq='ATGATAGATAGATGF', name='seq1')
        seqrec2 = SeqWithQuality(seq='ATGATAGATAGA', name='seq2')
        seq_iter = iter([seqrec1, seqrec2])
        fhand = temp_fasta_file(seq_iter)
        content = open(fhand.name).read()
        assert content == ">seq1\nATGATAGATAGATGF\n>seq2\nATGATAGATAGA\n"

class TestFileIndexer(unittest.TestCase):
    'It test the FileIndex class'

    @staticmethod
    def test_basic_file_index():
        'It test the file index class basic functionality'
        fhand = StringIO.StringIO('>key1\nhola\n>key2\ncaracola\n')
        index = FileIndex(fhand, item_start_patterns=['>'],
                          key_patterns=['>([^ \t\n]+)'])
        assert index['key1'] == '>key1\nhola\n'
        assert index['key2'] == '>key2\ncaracola\n'

    @staticmethod
    def test_with_item_types():
        'It test the file index class basic functionality'
        content = '>\n%key1%\ntype1\nhola\n>\n%key2%\ncaracola\ntype2\n'
        fhand = StringIO.StringIO(content)
        index = FileIndex(fhand, item_start_patterns=['>'],
                          key_patterns=['%([^%]+)%'],
                          type_patterns={'type1':['type1'], 'type2':['type2']})
        assert index['type1']['key1'] == '>\n%key1%\ntype1\nhola\n'
        assert index['type2']['key2'] == '>\n%key2%\ncaracola\ntype2\n'


class SplitLongSequencestest(unittest.TestCase):
    'It tests sequence spliting functions'
    @staticmethod
    def test_split_long_sequences():
        '''It test the function that splits sequences of an iterator with long
        sequences into  smaller sequences'''
        seq = 'atatatatatg'
        qual = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
        seq_rec = SeqWithQuality(seq=seq, qual=qual)
        seq_iter = iter([seq_rec])
        splited_seq_iter = split_long_sequences(seq_iter, 5)
        seq1 = splited_seq_iter.next()
        seq2 = splited_seq_iter.next()
        assert len(seq1) == 6
        assert len(seq2) == 5

        seq_iter = iter([seq_rec])
        splited_seq_iter = split_long_sequences(seq_iter, 3)
        seq1 = splited_seq_iter.next()
        seq2 = splited_seq_iter.next()
        seq3 = splited_seq_iter.next()
        assert len(seq1) == 4
        assert len(seq2) == 4
        assert len(seq3) == 3


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
