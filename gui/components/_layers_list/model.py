import weakref
from collections.abc import Iterable, Sequence

from vispy.util.event import EmitterGroup, Event
from ...layers import Layer

from ...util.naming import inc_name_count
from .view import QtLayersPanel


class ItemEvent(Event):
    def __init__(self, type, item, **kwargs):
        super().__init__(type, **kwargs)
        self._item = item

    @property
    def item(self):
        return self._item


def _check_layer(obj, error=False):
    result = isinstance(obj, Layer)
    if error and not result:
        raise TypeError(f'expected {obj} to be Layer; '
                        f'got {type(obj)}') from None
    return result


class LayersList:
    """List-like layer collection with built-in reordering and callback hooks.

    Parameters
    ----------
    viewer : Viewer, optional
        Parent viewer.

    Attributes
    ----------
    viewer : Viewer
        Parent viewer.
    events : vispy.util.event.EmitterGroup
        Event hooks:
            * add_item(item): whenever an item is added
            * remove_item(item): whenever an item is removed
            * reorder(): whenever the list is reordered
    """
    __slots__ = ('__weakref__', '_list', '_qt', '_viewer', 'events')

    def __init__(self, viewer=None):
        self._list = []
        self._viewer = None
        self.events = EmitterGroup(source=self,
                                   auto_connect=True,
                                   add_item=ItemEvent,
                                   remove_item=ItemEvent,
                                   reorder=Event)

        self.events.add_item.connect(self._add)
        self.events.remove_item.connect(self._remove)
        self.events.reorder.connect(self._reorder)

        # property setting - happens last
        self.viewer = viewer
        self._qt = QtLayersPanel(self)

    def __str__(self): return str(self._list)

    def __repr__(self): return repr(self._list)

    def __iter__(self): return iter(self._list)

    def __len__(self): return len(self._list)

    def __contains__(self, item):
        try:
            self[item]
        except KeyError:
            return False
        else:
            return True

    def __getitem__(self, query):
        """Get item in list.

        Parameters
        ----------
        query : str, int, or slice
            Querying index, slice or layer name.
        
        Returns
        -------
        layer : Layer
            Matching layer.
        
        Throws
        ------
        KeyError
            When the query returns no results.
        """
        # TODO: handle slicing ourselves
        try:
            if isinstance(query, str):
                match = self._name_match(query)
                if match:
                    return match[1]
            else:
                return self._list[query]
        except IndexError:
            pass

        raise KeyError(query)

    @property
    def viewer(self):
        """Viewer: Parent viewer.
        """
        if self._viewer is None:
            return self._viewer

        return self._viewer()

    @viewer.setter
    def viewer(self, viewer):
        prev = self.viewer
        if viewer == prev:
            return

        if prev is not None:
            self.events.add_item.disconnect(prev.dims._on_layers_change)
            self.events.remove_item.disconnect(prev.dims._on_layers_change)
            self.events.add_item.disconnect(prev._update_layer_selection)
            self.events.remove_item.disconnect(prev._update_layer_selection)
            self.events.reorder.disconnect(prev._update_layer_selection)

        for layer in self:
            layer.viewer = viewer

        if viewer is not None:
            self.events.add_item.connect(viewer.dims._on_layers_change)
            self.events.remove_item.connect(viewer.dims._on_layers_change)
            self.events.add_item.connect(viewer._update_layer_selection)
            self.events.remove_item.connect(viewer._update_layer_selection)
            self.events.reorder.connect(viewer._update_layer_selection)
            viewer = weakref.ref(viewer)

        self._viewer = viewer

    def _name_match(self, name, start=None, stop=None, ignore=None):
        """Check if a name matches a layer within the interval.

        Parameters
        ----------
        name : str
            Name of the layer.
        start : int, optional
            Start of the interval.
        stop : int, optional
            End of the interval.
        ignore : Layer, optional
            Layer to ignore if the names match.

        Returns
        -------
        match : int, Layer tuple or None
            Matching index, layer pair, if found.
        """
        if start is None:
            start = 0
            
        for i, layer in enumerate(self._list[start:stop]):
            if ignore:
                if layer is ignore:
                    continue
            if layer.name == name:
                return i + start, layer

    def _coerce_name(self, name, layer=None):
        """Coerce a name into a unique equivalent.

        Parameters
        ----------
        name : str
            Original name.
        layer : Layer, optional
            Layer for which name is generated.

        Returns
        -------
        new_name : str
            Coerced, unique name.
        """
        while self._name_match(name, ignore=layer):
            name = inc_name_count(name)
        return name

    def _to_index(self, obj):
        """Ensures that an object is a proper integer index.

        Parameters
        ----------
        obj : str, int, or Layer
            Object to be converted.

        Returns
        -------
        index : int
            Index of the object if it is not already an int.
        """
        if _check_layer(obj) or isinstance(obj, str):
            return self.index(obj)
        
        if not isinstance(obj, int):
            raise TypeError(f'expected {obj} to be str, int, or Layer; '
                            f'got {type(obj)}') from None
        return obj

    def _reordered_list(self, ordering):
        """Generates the reordered list given an ordering.

        Parameters
        ----------
        ordering : iterable of int
            Ordering of the indices to use.

        Yields
        ------
        layer : Layer
            Next layer in the ordered list.

        Raises
        ------
        ValueError
            When the improper indices are used.
        """
        expected = list(range(len(self)))

        for o in ordering:
            if not isinstance(o, int):
                raise TypeError(f'expected {o} to be int; '
                                f'got {type(o)}') from None
            try:
                expected.remove(o)
            except ValueError:
                raise ValueError(f'duplicate index: {o}') from None
            yield self._list[o]

        if expected:
            raise ValueError(f'indices {tuple(expected)} not provided')

    def append(self, layer):
        """Appends a layer to the list.

        Parameters
        ----------
        layer : Layer
            Layer to append.
        """
        _check_layer(layer, error=True)

        self._list.append(layer)
        self.events.add_item(item=layer, index=len(self) - 1)

    def insert(self, id, layer):
        """Inserts a layer before another layer.

        Parameters
        ----------
        id : str, int, or Lyaer
            Layer, its name, or its index to insert before.
        layer : Layer
            Layer to insert.
        """
        _check_layer(layer, error=True)
        index = self._to_index(id)

        self._list.insert(index, layer)
        self.events.add_item(item=layer, index=index - 1)

    def pop(self, id=-1):
        """Removes and returns a layer given its identifier.

        Parameters
        ----------
        id : str or int, optional
            Name or index of layer to remove.

        Returns
        -------
        layer : Layer
            Removed layer.
        """
        index = self._to_index(id)
        layer = self._list.pop(index)
        self.events.remove_item(item=layer)
        return layer

    def remove(self, id):
        """Removes a layer from the list given its identifier.

        Parameters
        ----------
        id : Layer, str, or int
            Layer or its name to remove.
        """
        self.pop(id)

    def __delitem__(self, id):
        """Removes an item given its identifier.

        Parameters
        ----------
        id : str or int
            Index of the item to remove.
        """
        self.remove(id)

    def swap(self, a, b):
        """Swaps the ordering of two elements in the list.

        Parameters
        ----------
        a : str, Layer, or int
            Layer to swap or its index.
        b : str, Layer, or int
            Layer to swap or its index.
        """
        i = self._to_index(a)
        j = self._to_index(b)

        self._list[i], self._list[j] = self._list[j], self._list[i]
        self.events.reorder()

    def reorder(self, *ordering):
        """Reorders the list given an iterable of its elements
        or their indices.

        Parameters
        ----------
        ordering : iterable of str, Layer, or int
            Ordering of the layers. Can also be used as *args.

        Notes
        -----
        LayerList.reorder(i, j, k, ...)
        LayerList.reorder([i, j, k, ...])
        """
        if not isinstance(ordering[0], (int, str, Layer)):
            ordering = ordering[0]
            if not isinstance(ordering, Sequence):
                raise TypeError(f'expected {ordering} to be Sequence; '
                                f'got {type(ordering)}') from None

        self._list[:] = self._reordered_list(self._to_index(o)
                                             for o in ordering)
        self.events.reorder()

    def index(self, query, start=None, stop=None):
        """Finds the index of an layer in the list.

        Parameters
        ----------
        query : Layer or str
            Querying layer or its name.
        start : int, optional
            Start of slice index to look.
        stop : int, optional
            Stop of slice index to look.

        Returns
        -------
        index : int
            Index of the layer.

        Raises
        ------
        ValueError
            When the query does not find a match.
        """
        if isinstance(query, str):
            match = self._name_match(query, start, stop)
            if not match:
                raise ValueError(query)
            return match[0]

        args = (query,)
        if stop is not None and start is None:
            start = 0

        if start is not None:
            args += (start,)

        if stop is not None:
            args += (stop,)

        return self._list.index(*args)

    def _add(self, event):
        """Callback when an item is added to set its order and viewer.
        """
        layer = event.item
        layer._order = -len(self)
        layer.viewer = self.viewer
        layer.events.select.connect(self.viewer._update_layer_selection)
        layer.events.deselect.connect(self.viewer._update_layer_selection)

    def _remove(self, event):
        """Callback when an item is removed to remove its viewer
        and reset its order.
        """
        layer = event.item
        layer.viewer = None
        layer._order = 0
        layer.events.select.disconnect(self.viewer._update_layer_selection)
        layer.events.deselect.disconnect(self.viewer._update_layer_selection)

    def _reorder(self, event):
        """Callback when the list is reordered to propagate those changes
        to the node draw order.
        """
        for i in range(len(self)):
            self[i]._order = -i
        canvas = self.viewer._canvas
        canvas._draw_order.clear()
        canvas.update()

    def _move_layers(self, index, insert):
        """Reorder list by moving the item at index and insterting it
        at the insert index. If additional items are selected these will
        get inserted at the insert index too. This allows for rearranging
        the list based on dragging and dropping a selection of items, where
        index is the index of the primary item being dragged, and insert is
        the index of the drop location, and the selection indicates if
        multiple items are being dragged.

        Parameters
        ----------
        index : int
            Index of primary item to be moved
        insert : int
            Index that item(s) will be inserted at
        """
        total = len(self)
        indices = list(range(total))
        if self[index].selected:
            selected = [i for i in range(total) if self[i].selected]
        else:
            selected = [index]
        for i in selected:
            indices.remove(i)
        offset = sum([i < insert for i in selected])
        for insert_idx, elem_idx in enumerate(selected, start=insert - offset):
            indices.insert(insert_idx, elem_idx)
        self.reorder(indices)

    def unselect_all(self):
        for layer in self:
            if layer.selected:
                layer.selected = False

    def remove_selected(self):
        """Removes selected items from list.
        """
        to_delete = []
        for i in range(len(self)):
            if self[i].selected:
                to_delete.append(i)
        to_delete.reverse()
        for i in to_delete:
            self.pop(i)
