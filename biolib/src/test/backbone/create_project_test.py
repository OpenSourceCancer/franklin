'''
Created on 26/01/2010

@author: jose
'''
import unittest, os.path

from biolib.utils.misc_utils import NamedTemporaryDir
from biolib.backbone.create_project import create_project
from biolib.backbone.analysis import do_analysis, BACKBONE_DIRECTORIES
from configobj import ConfigObj

READS_454 = '''@FKU4KFK07H6D2L
GGTTCAAGGTTTGAGAAAGGATGGGAAGAAGCCAAATGCCTACATTGCTGATACCACTACGGCAAATGCTCAAGTTCGGACGCTTGCTGAGACGGTGAGACTGGATGCAAGAACTAAGTTATTGAAT
+
CCFFFFFCC;;;FFF99;HHIHECCHHIIIFHHEEEHHHHHHIIIFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFGGGGFFGGBCCGFFFGG
@FKU4KFK07IJEB9
AATTCCCTTTCCGGTGATCGCCTCTCCTAGCAATGATGCAGCAAAGCCGATCATAGCAACACGGCCGACGAAGAGTTCATTCTGCTTGGTAAAACCAATGCCACCAGAAGTCCCAAAAATTCCATCTTCAACCTTCTGCTTCGGCTTCTCAACCTTCTTGGGCGGGGCTTTAGTTCTGGATTTGAACACAGCAAGAGGGTGAAACCA
+
FFFFFFFFFFFFFFFFFFIIIIIIIIIIIIIIIIIIIIIIIIIIIFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFGGGGFFFFGGGGGGFFFFFFGAA@5557>55577G
@FKU4KFK07IMD9G
ACCCTTCTAGCAGTAGGAATGACTTGACCACCTCCTCTGTGGATGGCATCAGCGTGAAGCACCACATCACAAACTTCAAAACAGATGCCT
+
B>>>GGFFFFFFFFFGGGGHHHHHHHHHIIIIIIIIIIIIIIIIIFFFFFFFFFFFFFFFFFFFFFFFFFFFFFGCB;;;;BGFFFFFFF
@FKU4KFK07IE66H
ATGAACCGCAAAAGCTTGTATGCTGTATTGCCTTGATTTGGTTTCCAAGATTCTTCCCACATATTTAGGAGAGAGTGTAGCTGGAAACCGAGACTTTGGCTGGAGAAGCA
+
FFFFFFFFG7777CGFFFFHHHHHHIHHHHHHHHHHHHHHH==?CCFFFFFFFGGCCCGFFFFFFFFFFFFFFFFFFFFFFFFFGGGFFFFFFFFFFFFFGGGFFFFFFF
'''
READS_ILL= '''@HWI-EAS59:3:1:5:1186#0/1
TGATACCACTGCTTANTCTGCGTTGNTACCA
+
BBBBCBAAABA=BB<%<C@?BBA@9%<B;A@
@HWI-EAS59:3:1:5:169#0/1
GTTGATACCACTGCTNACTCTGCG
+
BBA@ABBBBBBBAA9%;BBBBCAA
@HWI-EAS59:3:1:5:1467#0/1
AAGCAGTGGTATCAANGCAGAGTTCNGCTTC
+
B?@CBCBCBAACBB:%>BBBAC@B<%9>BBB
@HWI-EAS59:3:1:5:651#0/1
CATACCCAATTGCTTNAGATGGAT
+
AAAABBA@@B?7=@<%=<ABBA:A
@HWI-EAS59:3:1:5:1609#0/1
AGAGCATTGCTTTGANTTTAAAAACNCGGTT
+
?BA@B>CCCBCBB:<%>BCA@;A?<%?BBAB
@HWI-EAS59:3:1:5:247#0/1
GATGGATCCCAAGTTNTTGAGGAACNAGAGG
+
BBA?;BBBBBA3AB=%=BBB@A=A=%<><@?
'''



class TestBackbone(unittest.TestCase):
    'It tests the backbone'

    @staticmethod
    def test_create_project():
        'We can create a project'
        test_dir = NamedTemporaryDir()
        settings_path = create_project(directory=test_dir.name,
                                       name='backbone')

        assert settings_path == os.path.join(test_dir.name,
                                'backbone', BACKBONE_DIRECTORIES['config_file'])
        settings = ConfigObj(settings_path)
        assert settings['General_settings']['project_name'] == 'backbone'
        project_path = os.path.join(test_dir.name, 'backbone')
        assert settings['General_settings']['project_path'] == project_path
        test_dir.close()

    @staticmethod
    def test_cleaning_analysis():
        'We can clean the reads'
        test_dir = NamedTemporaryDir()
        project_name = 'backbone'
        settings_path = create_project(directory=test_dir.name,
                                       name=project_name)
        project_dir = os.path.join(test_dir.name, project_name)
        #setup the original reads
        reads_dir = os.path.join(project_dir, 'reads')
        original_reads_dir = os.path.join(reads_dir, 'original')
        os.mkdir(reads_dir)
        os.mkdir(original_reads_dir)

        #print original_reads_dir
        fpath_454 = os.path.join(original_reads_dir, 'pt_454.sfastq')
        fpath_ill = os.path.join(original_reads_dir, 'pt_illumina.sfastq')
        open(fpath_454, 'w').write(READS_454)
        open(fpath_ill, 'w').write(READS_ILL)

        #use only the 454 and sanger reads
        analsysis_config = {
            'inputs_filter':lambda input: input['platform'] in ('454',
                                                                'illumina')}
        do_analysis(project_settings=settings_path,
                    kind='clean_reads',
                    analysis_config=analsysis_config)
        cleaned_dir = os.path.join(project_dir, 'reads', 'cleaned')
        assert os.path.exists(cleaned_dir)
        cleaned_454 = os.path.join(cleaned_dir, os.path.basename(fpath_454))
        assert os.path.exists(cleaned_454)

        do_analysis(project_settings=settings_path,
                    kind='prepare_mira_assembly',
                    analysis_config=analsysis_config)
        assembly_input = os.path.join(project_dir, 'assembly', 'input')
        assert os.path.exists(assembly_input)
        mira_in_454 = os.path.join(assembly_input, 'backbone_in.454.fasta')
        mira_in_qul = os.path.join(assembly_input, 'backbone_in.454.fasta.qual')
        assert os.path.exists(mira_in_454)
        assert os.path.exists(mira_in_qul)


        do_analysis(project_settings=settings_path,
                    kind='mira_assembly',
                    analysis_config=analsysis_config)
        assembly_dir = os.path.join(project_dir)

        do_analysis(project_settings=settings_path,
                    kind='select_last_assembly',
                    analysis_config=analsysis_config)
#        print test_dir.name
#        raw_input()
        test_dir.close()

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
