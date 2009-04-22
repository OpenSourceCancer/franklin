'''
Created on 2009 mar 9

@author: peio

Script who reads a caf file and takes the information for each
contig. It creates a file for each contig to  easyly use them
'''

from re import match
from biolib.contig import Contig, locate_sequence
from biolib.Seqs import SeqWithQuality
from Bio.Seq import Seq

class CafParser(object):
    ''' This class is used to parse caf files.'''
    def __init__(self, fname):

        '''The initialitation.
        keyword arguments:
            fname : caf file name
        '''
        self._fname     = fname
        self._qual_index = {}
        self._seq_index = {}
        self._dna_index = {}
        self._type_index = {}
        self._caf_file2caf_index()

    def _caf_file2caf_index(self):
        '''It takes a caf file and after reading it it returns an index with 
           section positions. We define section as the paragraph of text where
            each caf data type is represented . example:
                    DNA: name
                    aaaaaaaaaaaaaaa
                    ttttttttttt
                    cccccccccc
         It stores as well if the secuence is a contig or a read
         '''
        
        fhandler = open(self._fname,'rt')
        rawline  = "Filled"
        sec_in = False

        while len(rawline) != 0:
            
            prior_tell = fhandler.tell()
            rawline    = fhandler.readline()
            line       = rawline.strip()
            
            #if match("\w*\s*:\s*\w*", line):
            mode = rawline.split(':', 1)[0].strip().lower()
            if mode in ('dna', 'basequality', 'sequence'):
                #pylint: disable-msg=W0612
                mode_, name = line.split(":")
                name = name.strip()
                if mode == "sequence":
                    sec_in = True
                else:
                    sec_in = False
                
                if mode == 'dna':
                    self._dna_index[name] = prior_tell
                elif mode == 'basequality':
                    self._qual_index[name] = prior_tell
                elif mode == 'sequence':
                    self._seq_index[name] = prior_tell    

            if sec_in:
                if line == "Is_read":
                    self._type_index[name] = "Is_read"
                elif line == "Is_contig": 
                    self._type_index[name] = "Is_contig"
                    
    def contigs(self):
        '''It returns a generator that yields the contigs.'''
        
        for seq_rec_name in self._seq_index:
            if self._type_index[seq_rec_name] == 'Is_contig':
                yield self.contig(seq_rec_name)
    
    def reads(self):
        '''It returns a generator with the reads'''
        
        for seq_rec_name in self._seq_index:
            if self._type_index[seq_rec_name] == 'Is_read':
                yield  self.read(seq_rec_name)

    def _return_section(self, position):
        ''' It returns a section giving a position in the file. It will take
        the text until it finds the next statement ( DNA: , Sequence: or
        BaseQuality '''
        content = []
        fhandler = open(self._fname, 'r')
        fhandler.seek(position)
        
        line = fhandler.readline()# To pass the header
        line = fhandler.readline()
        while True:
            line = line.strip()
#            if (len(line) == 0) or (match("\w*\s*:\s*\w*", line)):
            if (len(line) == 0) or \
            (match("^[DNA|Sequence|BaseQuality|BasePosition]\s*:", line)):
                break
            content.append(line)
            line = fhandler.readline()
        return content

    def _get_dna(self, sec_rec_name):
        ''' It returns the dna secuence in a string.It needs the sec_rec name
        '''
        dna_pos     = self._dna_index[sec_rec_name]
        dna_section = self._return_section(dna_pos)
        dna = ''
        for line in dna_section:
            dna += line.strip()
        return dna
  
    def _get_base_quality(self, sec_rec_name):
        ''' It returns the base quality list. It needs the sec_rec name.'''
        try:
            base_quality_pos = self._qual_index[sec_rec_name]
        except KeyError:
            raise ValueError('No quality for the given read')
        base_quality_section = self._return_section(base_quality_pos)
        
        base_quality = []
        for line in base_quality_section:
            line          = line.strip()
            base_quality += line.split(' ')
        return base_quality

    @staticmethod
    def _get_align_to_scf(line):
        ''' It reads Alig_to_SCF line and returns a tupla with the info
         structured. Tupla order: scf_start, scf_end, read_start, read_end '''
        item       = line.split(" ")
        return (int(item[1]), int(item[2]), int(item[3]), int(item[4]))

    @staticmethod
    def _get_assembled_from(line):
        ''' It reads Assembled_from line and returns 2 elements: The first is
        the read name, and the second one is a tupla with 4 coordinates:
        The order of the tupla is: (contig_start, contig_end, read_start,
         read_end)'''
        item         = line.split(" ")
        return item[1], (int(item[2]), int(item[3]), int(item[4]), int(item[5]))

    def _get_seq_rec(self, sec_rec_name):
        ''' It return a dictionary with the content of the secuence section.

        It stores the key and the value, but there are  2 exceptions:
        1) reads key's value is a dict with the reads. Where the key is 
        the read name and the value are a list of tuples where each tupla
        contains:
            (contig_start, contig_end, read_start,read_end)

        2) scf_alignments key's value is a dict with the alignemnts.
         Where the key is the SCF file name and the value is a list of
         tuples where each tupla contains:
            (scf_start, scf_end, read_start, read_end)
        '''
       
        # variable type in this section. All of them are in array to easy use
        # of them
        seq_type = ('Is_read', 'Is_contig', 'Is_group', 'Is_assembly')
        state    = ('Padded', 'Unpadded')
        sec_info = {}
        reads    = {}
        scf_alignment = []
        
        sequence_pos     = self._seq_index[sec_rec_name]
        sequence_section = self._return_section(sequence_pos)
        
        for line in sequence_section:
            line = line.strip()
            if line in state:
                sec_info['state'] = line
            elif line in seq_type:
                sec_info['type'] = line
            elif line.startswith('Align_to_SCF'):
                scf_alignment.append(self._get_align_to_scf(line))
            elif line.startswith('Assembled_from'):
                read_name, coords = self._get_assembled_from(line)
                if read_name not in reads.keys():
                    reads[read_name] = []
                reads[read_name].append(coords)
            else:
                items = line.split(' ')
                sec_info[items[0]] = " ".join(items[1:])
        
        sec_info['name'] = sec_rec_name
        if reads:
            sec_info['reads'] = reads
        else:
            scf_file_name     = sec_info['SCF_File']
            scf_alignments = {}
            scf_alignments[scf_file_name] = scf_alignment
            sec_info['scf_alignments'] = scf_alignments
        
        return sec_info
    def _get_seq_rec_full(self, seq_rec_name):
        ''' It returns the complete info of a sec_record. It uses the index 
         to access the file so we do no t need to read the whole file.
         We need the name of the sec record '''
        
        seq_rec_info = self._get_seq_rec(seq_rec_name) 
        # First we take dna secuence
        seq_rec_info['DNA'] = self._get_dna(seq_rec_name)
        # If BaseQuality is in the sec record
        if seq_rec_name in self._qual_index:
            seq_rec_info['BaseQuality'] = self._get_base_quality(seq_rec_name)
        
        return seq_rec_info
    
    def read(self, name):
        '''Given a read name it returns a SeqWithQuality object'''
        
        if self._type_index[name] == 'Is_read':
            
            seq_info = self._get_seq_rec(name)
            dna      = self._get_dna(name)
            quality  = self._get_base_quality(name)
     
            seq_rec  = SeqWithQuality(seq=Seq(dna), name=name, qual=quality )
            seq_rec.annotations =  seq_info
            return seq_rec
        else:
            raise RuntimeError (name + 'does not corresponds to a read')
    @staticmethod  
    def _correct_minus(reads):
        ''' It corrects the problem of the minus(-)  coordenates. This function
        returns a int that is de maximun minus numer.example:
                   -2101234567890
            contig    aaaaaaaa
            read1   cccccc
            read2      eeeeee
            In this case the maximun minus number is 2 and we use it to 
            move the other seqs
            ''' 
        correction = 0
        for read in reads:
            if reads[read][0][0] > reads[read][0][1]:
                contig_start = reads[read][0][1]
            else:
                contig_start = reads[read][0][0]
            read_start   = reads[read][0][2]
            diff         = contig_start - read_start
            if diff < correction:
                correction = diff
        return abs(correction)
    
    @staticmethod
    def _read_mask(read_lenght, annot_dict):
        ''' It returns the mask of the read. It gets the information using
         the annotations dictionary'''
        read = range(1, read_lenght)
        for key in annot_dict:
            if key.lower() == 'clippping' or key.lower() == 'seq_vec':
                start = annot_dict[key].split(" ")[1]
                end   = annot_dict[key].split(" ")[2]
                for i in range(int(start), int(end)):
                    if i in read:
                        read.remove(i)
        mask_start = read[0]
        mask_end   = read[-1]
        return [mask_start, mask_end]
         
    def contig(self, name):
        '''Given a name it returns a Contig'''
        contig_info = self._get_seq_rec(name)
        dna         = self._get_dna(name)
        try:
            qual = self._get_base_quality(name)
        except ValueError:
            qual = None
        if contig_info['type'] == 'Is_contig':
            reads      = contig_info['reads']
            correction = self._correct_minus(reads)
            if len(dna) == 0:
                contig    = Contig()
            else:
                consensus = SeqWithQuality(seq=Seq(dna), name=name, qual=qual)
                consensus = locate_sequence(sequence = consensus, \
                                             location = correction)
                contig    = Contig(consensus=consensus)
                
            for read in reads:
                read_sections = reads[read]
                if len(read_sections) > 1:
                    #We it's unpadded there is more than one list of coordentes 
                    raise RuntimeError('This is an unppadded sec record and \
                     we do not support them. Use caf tools to convert it to \
                     padded')
                else:
                    if read_sections[0][0] > read_sections[0][1]:
                        contig_start = int(read_sections[0][1]) + correction
                        forward = False
                    else:
                        contig_start = int(read_sections[0][0]) + correction
                        forward = True
                    read_start    = int(read_sections[0][2]) 
                    contig_start -= read_start

                #Data to fill the contig
                seq_rec    = self.read(read)
                mask       = self._read_mask(len(seq_rec.seq), seq_rec.annotations)
                
                if forward:
                    strand  = 1
                else:
                    strand = -1
                contig.append_to_location(sequence=seq_rec, \
                                          start=contig_start,\
                                          strand=strand, forward=forward, \
                                          mask=mask)
        return contig 
                 
