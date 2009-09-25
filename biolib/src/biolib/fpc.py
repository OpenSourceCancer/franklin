'''An fpc physical map representation with gff export capabilities.

This module has been coded looking at the bioperl equivalent module
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

class FPCMap(object):
    '''It parses and hold the information from an FPC map'''

    def __init__(self, fpc_file):
        '''It parses and fpc file'''
        self._fhand = fpc_file
        self.name = None
        self.version = None
        self._parse_fpc()

    def _parse_fpc(self):
        'It parses the fpc file'
        #the header
        version_re = re.compile('^((\d+\.\d+)).*')
        clone_lpos_re = re.compile('Map "ctg(\d+)" Ends Left ([-\d]+)')
        clone_rpos_re = re.compile('Map "ctg\d+" Ends Right ([-\d]+)')
        clone_match_re = re.compile('([a-zA-Z]+)_match_to_\w+\s+"(.+)"')
        clone_positive_re = re.compile('Positive_(\w+)\s+"(.+)"')
        for line in self._fhand:
            line = line.strip()
            if not line:
                break
            line = line.lstrip('/ ')
            #project name
            if 'project' in line and 'fpc' in line:
                self.name = line.split()[-1]
            version_match = version_re.match(line)
            if version_match:
                self.version = line.split()[0]

        #clone data
        clones = {}
        contigs = {}
        markers = {}
        for line in self._fhand:
            if line.startswith('Markerdata'):
                break
            line = line.strip()
            if not line:
                continue
            type_, name = line.split(':')
            clone = {}
            clone['type'] = type_.strip()
            clone['name'] = name.strip().strip('"')
            #clone attributes
            fpc_remark = ''
            remark = ''
            for line in self._fhand:
                line = line.strip()
                if not line:
                    break
                lpos_match = clone_lpos_re.match(line)
                if lpos_match:
                    contig_number = lpos_match.group(1)
                    contig_start = lpos_match.group(2)
                    if 'range' not in clone:
                        clone['range'] = {}
                    clone['contig_number'] = contig_number
                    clone['range']['start'] = contig_start
                    continue
                rpos_match = clone_rpos_re.match(line)
                if rpos_match:
                    contig_end = rpos_match.group(1)
                    if 'range' not in clone:
                        clone['range'] = {}
                    clone['range']['end'] = contig_end
                    continue
                match_match = clone_match_re.match(line)
                if match_match:
                    match_type = 'match_' + match_match.group(1).lower()
                    matched_object = match_match.group(2)
                    if match_type not in clone:
                        clone[match_type] = []
                    clone[match_type].append(matched_object)
                    continue
                positive_match = clone_positive_re.match(line)
                if positive_match:
                    if 'markers' not in clone:
                        clone['markers'] = []
                    marker_type = positive_match.group(1)
                    marker = positive_match.group(2)
                    clone['markers'].append(marker)
                    if marker not in markers:
                        markers[marker] = {}
                        markers[marker]['contigs'] = {}
                        markers[marker]['clones'] = []
                    markers[marker]['type'] = marker_type
                    markers[marker]['contigs'][clone['contig_number']] = True
                    markers[marker]['clones'].append(clone['name'])
                elif line.startswith('Gel_number'):
                    gel_number = line.split()[1]
                    clone['gel'] = gel_number
                elif line.startswith('Remark'):
                    remark += line.split(' ', 1)[1].strip('"')
                    remark += '\n'
                    if 'Chr' in remark:
                        raise NotImplemented('Fixme')
                elif line.startswith('Fp_number'):
                    fp_number = line.split()[1]
                    clone['fp_number'] = fp_number
                elif line.startswith('Shotgun'):
                    seq_type, seq_status = line.split()[1:]
                    clone['sequence_type'] = seq_type
                    clone['sequence_status'] = seq_status
                elif line.startswith('fpc_remark'):
                    fpc_remark += line.split(' ', 1)[1].strip('"')
                    fpc_remark += '\n'
            clone['remark'] = remark
            clone['fpc_remark'] = fpc_remark
            clones[clone['name']] = clone
            if 'contig_number' in clone:
                contig_number = clone['contig_number']
                if contig_number not in contigs:
                    contigs[contig_number] = {}
                    contigs[contig_number]['clones'] = []
                    contigs[contig_number]['range'] = {}
                    contigs[contig_number]['range']['start'] = None
                    contigs[contig_number]['range']['end'] = None
                #this clone is in the contig
                contigs[contig_number]['clones'].append(clone['name'])
                #is the contig larger due to this clone?
                start = clone['range']['start']
                end = clone['range']['end']
                if (contigs[contig_number]['range']['start'] is None or
                    contigs[contig_number]['range']['start'] > start):
                    contigs[contig_number]['range']['start'] = start
                if (contigs[contig_number]['range']['end'] is None or
                    contigs[contig_number]['range']['end'] < end):
                    contigs[contig_number]['range']['end'] = end
            #the markers in the contig
            if 'markers' in clone:
                if 'markers' not in contigs[contig_number]:
                    contigs[contig_number]['markers'] = {}
                for marker in clone['markers']:
                    contigs[contig_number]['markers'][marker] = True

        #marker data
        re_group = re.compile('(\d+|\w)(.*)')
        re_anchor = re.compile('Anchor_pos\s+([\d.]+)\s+(F|P)?')
        for line in self._fhand:
            if line.startswith('Contigdata'):
                break
            line = line.strip()
            if not line:
                continue
            type_, name = line.split(':')
            name = name.strip().strip('"')
            type_ = type_.split('_', 1)[-1]
            marker = {}
            marker['type'] = type_
            marker['group'] = 0
            marker['global'] = 0
            marker['anchor'] = 0
            remark = ''
            for line in self._fhand:
                line = line.strip()
                if not line:
                    break
                if line.startswith('Global_position'):
                    raise NotImplemented('Fixme')
                elif line.startswith('Anchor_bin'):
                    group = line.split()[1].strip('"')
                    match = re_group.match(group)
                    marker['group'] = match.group(1)
                    marker['subgroup'] = match.group(2)
                elif line.startswith('Anchor_pos'):
                    match = re_group.match(line)
                    marker['global'] = match.group(1)
                    marker['anchor'] = 1
                    if match.group(2) == 'F':
                        marker['framework'] = 1
                    else:
                        marker['framework'] = 0
                elif line.startswith('anchor'):
                    marker['anchor'] = 1
                elif line.startswith('Remark'):
                    remark += line.split(' ', 1)[1].strip('"')
                    remark += '\n'
            markers[name] = marker

        #contig data
        re_contig_def = re.compile('^Ctg(\d+)')
        re_contig_remark = re.compile('#\w*(.*)\w*$/')
        re_chr_remark = re.compile('Chr_remark\s+"(-|\+|Chr(\d+))\s+(.+)"$')
        for line in self._fhand:
            line = line.strip()
            if not line:
                continue
            if line.startswith('Ctg'):
                match = re_contig_def.match(line)
                contig = None
                name = match.group(1)
                if name in contigs:
                    contig = contigs[name]
                else:
                    contig = {}
                    contigs[name] = contig
                contig['group'] = 0
                contig['anchor'] = 0
                contig['position'] = 0
                match = re_contig_remark.search(line)
                if match:
                    contig['group'] = match.group(1)
                    contig['anchor'] = 1
            elif line.startswith('Chr_remark'):
                match = re_chr_remark.match(line)
                if match is None:
                    continue
                contig['anchor'] = 1
                if match.group(3):
                    contig['chr_remark'] = match.group(3)
                if match.group(2):
                    contig['group'] = match.group(2)
                else:
                    contig['group'] = '?'
            elif line.startswith('User_remark'):
                remark = line.split()[1].strip('"')
                contig['usr_remark'] = remark
            elif line.startswith('Trace_remark'):
                remark = line.split()[1].strip('"')
                contig['trace_remark'] = remark

        print contigs