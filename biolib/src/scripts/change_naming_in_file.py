#!/usr/bin/env python
'''
This script changes the names of sequences in a file. It takes the name from a
naming schema database.
If the database does not exists, it creates it.
If the project does not exist it creates it.

Created on 21/12/2009

@author: peio

from optparse import OptionParser
'''
from optparse import OptionParser
import sys, sqlalchemy, os
from biolib.db.naming import (create_naming_database, project_in_database,
                              add_project_to_naming_database, DbNamingSchema,
                              change_names_in_files)

def parse_options():
    'It parses the command line arguments'
    parser = OptionParser()
    parser.add_option('-s', '--infile', dest='infile',
                    help='input sequence file')
    parser.add_option('-o', '--outseqfile', dest='outfile',
                      help='output file')
    parser.add_option('-f', '--fileformat', dest="format",
                      help='input file format', default='fasta')
    parser.add_option('-d', '--database', dest='database',
                    help='path to the naming schema database')
    parser.add_option('-p', '--project', dest='project',
                      help='Project name')
    parser.add_option('-t', '--tag', dest="tag",
                      help='Type of seq to change. EST, CONTIG, ...')
    return parser


def set_parameters():
    'Set parameters'
    # Set parameters
    parser  = parse_options()
    options = parser.parse_args()[0]

    if options.infile is None:
        parser.error('Input file is mandatory')
    else:
        infhand = open(options.infile)
    if options.outfile is None:
        outfhand = sys.stdout
    else:
        outfhand = open(options.outfile, 'w')
    format = options.format

    if options.database is None:
        parser.error('Database is mandatory')
    else:
        database = options.database

    if options.project is None:
        parser.error('Project is mandatory')
    else:
        items = options.project.split(',')
        try:
            description = items[2]
        except IndexError:
            description = None
        project = {'name':items[0], 'code':items[1],
                   'description':description}

    if options.tag is None:
        tag = 'EST'
    else:
        tag = options.tag
    return infhand, outfhand, format, database,  project, tag

def main():
    'The main part of the script'
    infhand, outfhand, format, database, project, tag = set_parameters()

    # check if the database exits
    engine   = sqlalchemy.create_engine( 'sqlite:///%s'  % database)
    if not os.path.exists(database):
        create_naming_database(engine)
    # check if the project exists
    project_name = project['name']
    if not project_in_database(engine, project_name):
        add_project_to_naming_database(engine, name=project_name,
                                       code=project['code'],
                                       description=project['description'])
    # create a naming schema
    naming = DbNamingSchema(engine, project_name)
    print naming.get_uniquename(kind='EST', name='hoa')
    # change name to seqs in file
    change_names_in_files(infhand, outfhand, naming, format, tag)

if __name__ == '__main__':
    main()