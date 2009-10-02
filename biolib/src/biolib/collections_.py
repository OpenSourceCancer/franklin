'''
Created on 04/09/2009

@author: jose
'''

# Copyright 2009 Jose Blanca, Peio Ziarsolo, COMAV-Univ. Politecnica Valencia
# This file is part of biolib.
# project is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

# biolib is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR  PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with biolib. If not, see <http://www.gnu.org/licenses/>.

import pysparse
import tempfile

class SparseVector(object):
    'A sparse vector collection to hold nearly empty vectors.'
    def __init__(self, nelements, size_hint=None, store_non_int=False):
        '''It initializes the vector.

        We require the number of elements that the vector should hold.
        size_hint is the number of estimated elements that the vector should
        hold at the end. If given expensive memory reallocation will be saved.
        '''
        self._size = nelements
        if size_hint:
            self._spv = pysparse.spmatrix.ll_mat(nelements, 1, size_hint)
        else:
            self._spv = pysparse.spmatrix.ll_mat(nelements, 1)
        if store_non_int:
            self._cargo = []
            self._cargo.append(None)   #we dont' use the 0 as cargo index
        else:
            self._cargo = None
        self._position = 0

    def __setitem__(self, index, value):
        'It sets one item in the vector'
        cargo = self._cargo
        if cargo is None:
            self._spv[index, 0] = value
        else:
            #was an item already stored in that position?
            cargo_index = self._spv[index, 0]
            if cargo_index:
                self._cargo[cargo_index] = value
            else:
                self._cargo.append(value)
                cargo_index = len(self._cargo) - 1
                self._spv[index, 0] = cargo_index

    def __getitem__(self, index):
        'It returns one element'
        cargo = self._cargo
        if cargo is None:
            return self._spv[index, 0]
        else:
            return cargo[int(self._spv[index, 0])]
    def __iter__(self):
        'The iterable protocol'
        self._position = 0
        return self

    def next(self):
        'It returns the next item'
        position = self._position
        if position < self._size:
            value = self[self._position]
            self._position += 1
            return value
        else:
            raise StopIteration

    def __len__(self):
        'It returns the number of elements'
        return self._size

    def __str__(self):
        'It prints the vector'
        toprint = '['
        for item in self:
            toprint += str(item)
            toprint += ', '
        toprint += ']'
        return toprint

    def non_empty_items(self):
        'It return a iterator with non empty items'
        keys = self._spv.keys()[0]
        last_item = len(keys) - 1
        for index, key in enumerate(keys):
            if self._cargo:
                yield key, self._cargo[int(self._spv[key, 0])]
            else:
                yield key, self._spv[key, 0]
            if index == last_item:
                raise StopIteration

    def non_empty_values(self):
        'It return a iterator with non empty items'
        for item in self.non_empty_items():
            yield item[1]

class FileCachedList(object):
    '''A list cached in a file.

    The main aim is to store really big lists in files with an iterator
    interface.
    '''
    def __init__(self, type_):
        '''It creates a FileCachedList.

        It requires the type of objects that will be stored.
        '''
        self._type = type_
        #the file to store the data
        self._wfhand = tempfile.NamedTemporaryFile()
        #the file to read the data
        self._rfhand = None

    def append(self, item):
        'It writes one element at the file end'
        self._wfhand.write('%s\n' % str(item))

    def extend(self, items):
        'It adds a bunch of items from a list or from a FileCachedList'
        if 'items' in dir(items):
            items = items.items()
        for item in items:
            self.append(item)

    def items(self):
        'It yields all items'
        self._wfhand.flush()
        rfhand = open(self._wfhand.name)
        for line in rfhand:
            if len(line) == 0:
                raise StopIteration
            yield self._type(line.strip())

class RequiredPosition(object):
    'This class'

    def __init__(self, fhand):
        '''It initializes the class '''
        self._fhand = fhand
        self._fhand.seek(0)

    def __getitem__(self, index):
        print "hola", index, "hola" #,  index2
#        for line in self._fhand:
#            if not line:
#                continue
#            line = line.strip()
#            (cromosome, position) = line.split()
#            (asked_crom, asked_pos) = index
#            print index



def item_context_iter(items, window=None):
    '''Given an iter with Locatable items it returns an item, context iter,

    The items in the iter should have a location property (numerical) and a
    reference porperty. An item located based on its reference and its location.
    The iter should be sorted by references and locations.
    This generator will yield every item and its surrounding items (context).
    If window is not given all items from every reference will be included in
    the context.
    '''
    context = []
    if window is not None:
        width = window / 2.0
    else:
        width = None
    current_item = None #the item that we're yielding now
    items_buffer = []    #the items to be returned
    context_buffer = []
    right_edge_item = None
    last_item_in_iter = False
    while True:
        #if we have consumed the right item in the last iteration we ask for
        #other one
        if right_edge_item is None:
            try:
                right_edge_item = items.next()
            except StopIteration:
                #we have to empty the buffers before finishing
                last_item_in_iter = True
        #the case or the empty iter
        if not right_edge_item and not items_buffer:
            raise StopIteration
        #if the right item is in the same reference as the current one we add it
        #to the buffers
        if (right_edge_item is not None
            and (current_item is None or
                 right_edge_item.reference == current_item.reference)):
            #a buffer with the items to the right of the current one
            items_buffer.append(right_edge_item)
            #a buffer with the items to be added to the context
            context_buffer.append(right_edge_item)
            #we have consumed this right item
            right_edge_item = None
        #do we have to yield an item? we have to fill up the context buffer
        #first.
        #if there is no width but we're at the last item of the reference
        if (last_item_in_iter or
            #if we're at a new reference
            (items_buffer[-1].reference != items_buffer[0].reference) or
            #if we're yet to close to the start we don't return anything
            (width is not None and items_buffer[-1].location > width)):
            current_item = items_buffer.pop(0)

        if not current_item:
            continue
        current_location = current_item.location
        current_reference = current_item.reference
        #which items do we have to add to the context in the right side?
        while True:
            #if there are still items that might be added to the reference
            #and the item to be added has the same reference as the current
            if (context_buffer and
                              context_buffer[0].reference == current_reference):
                if((width is None) or
                   (width is not None and
                        context_buffer[0].location - current_location < width)):
                    #and the item is close enough to the current item
                    context.append(context_buffer.pop(0))
                else:
                    break
            else:
                break
        #purge the items from the context that are not close to the current item
        while True:
            if not context:
                break
            if ((width is not None and
                 current_location - context[0].location  > width) or
                 current_reference != context[0].reference):
                context.pop(0)
            else:
                break
        yield current_item, context
        #if we have consumed the buffers for this reference we have to go to the
        #next reference
        current_item = None
        if not items_buffer:
            current_item = None
            #if there's no more item and nothing in the buffers we're done
            if last_item_in_iter:
                raise StopIteration